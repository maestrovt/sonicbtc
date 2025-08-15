from decimal import Decimal
from ecdsa import SigningKey, SECP256k1
from subprocess import run
from typing import List, Tuple
from note import Note
import hashlib
import hmac
import json
import threading
import queue
import time
from collections import deque
from constants import OVERTONES
from data import (
    MidiTask,
    BlockScanned,
    UTXOReceived,
    BalanceUpdated,
    UTXOSpent,
    SENTINEL
)
from sonify import _pitch_from_balance
from utilities import log
from player import send_note_via_mido, metronome


# Provided by administrator
WALLET_NAME = "wallet_171"
EXTENDED_PRIVATE_KEY = "tprv8ZgxMBicQKsPdyeZaFF6JRjdJ24oy7dC9FvYrtaqTrhhRbs9vXMCMwsFn95Gg7rhkHwX5piq66LN69iJfxBWFtL5tQAdm4atSq5eBHP7nZT"

_LAST_BALANCE_PITCH: int | None = None

# Decode a base58 string into an array of bytes
def base58_decode(base58_string: str) -> bytes:
    base58_alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = 0
    for char in base58_string:
        num *= 58
        num += base58_alphabet.index(char)

    num_bytes = (num.bit_length() + 7) // 8
    combined = num.to_bytes(num_bytes, byteorder="big")
    # combined = num.to_bytes(78, byteorder="big")
    checksum = combined[-4:]
    if hashlib.sha256(hashlib.sha256(combined[:-4]).digest()).digest()[:4] != checksum:
        raise ValueError("Invalid checksum")
    return combined[:-4]
    # Convert Base58 string to a big integer

    # Convert the integer to bytes

    # Chop off the 32 checksum bits and return
    # BONUS POINTS: Verify the checksum!


# Deserialize the extended key bytes and return a JSON object
# https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#serialization-format
# 4 byte: version bytes (mainnet: 0x0488B21E public, 0x0488ADE4 private; testnet: 0x043587CF public, 0x04358394 private)
# 1 byte: depth: 0x00 for master nodes, 0x01 for level-1 derived keys, ....
# 4 bytes: the fingerprint of the parent's key (0x00000000 if master key)
# 4 bytes: child number. This is ser32(i) for i in xi = xpar/i, with xi the key being serialized. (0x00000000 if master key)
# 32 bytes: the chain code
# 33 bytes: the public key or private key data (serP(K) for public keys, 0x00 || ser256(k) for private keys)
def deserialize_key(b: bytes) -> object:
    version = b[:4]
    depth = b[4]
    parent_fingerprint = b[5:9]
    child_number = b[9:13]
    chaincode = b[13:45]
    key_data = b[46:78]
    return {
        "version": version,
        "depth": depth,
        "parent_fingerprint": parent_fingerprint,
        "child_number": child_number,
        "chaincode": chaincode,
        "key": key_data
    }


# Derive the secp256k1 compressed public key from a given private key
# BONUS POINTS: Implement ECDSA yourself and multiply you key by the generator point!
def get_pub_from_priv(priv: bytes) -> bytes:
    sk = SigningKey.from_string(priv, curve=SECP256k1)
    vk = sk.verifying_key
    return b"\x02" + vk.to_string()[:32] if vk.to_string()[-1] % 2 == 0 else b"\x03" + vk.to_string()[:32]


# Perform a BIP32 parent private key -> child private key operation
# Return a JSON object with "key" and "chaincode" properties as bytes
# https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#user-content-Private_parent_key_rarr_private_child_key
def derive_priv_child(key: bytes, chaincode: bytes, index: int, hardened: bool) -> object:
    """Derive a child private key from a parent private key."""
    n = SECP256k1.order  # Order of the secp256k1 curve

    # Step 1: Determine hardened or non-hardened derivation
    if hardened:
        index += 0x80000000  # Set the hardened bit
        data = b"\x00" + key + index.to_bytes(4, "big")  # 0x00 || ser256(k_par) || ser32(i)
    else:
        pubkey = get_pub_from_priv(key)  # Compute the compressed public key
        data = pubkey + index.to_bytes(4, "big")  # serP(point(k_par)) || ser32(i)

    # Step 2: Compute HMAC-SHA512(c_par, data)
    I = hmac.new(chaincode, data, hashlib.sha512).digest()
    I_L, I_R = I[:32], I[32:]  # Split I into I_L (key derivation) and I_R (new chain code)

    # Step 3: Compute the child private key
    I_L_int = int.from_bytes(I_L, "big")
    if I_L_int >= n:
        raise ValueError("I_L is greater than or equal to the curve order; invalid derivation")

    child_key = (I_L_int + int.from_bytes(key, "big")) % n
    if child_key == 0:
        raise ValueError("Derived key is zero; invalid derivation")

    # Step 4: Return the child private key and chain code
    return {
        "key": child_key.to_bytes(32, "big"),  # 32-byte child private key
        "chaincode": I_R  # 32-byte child chain code
    }


# Given an extended private key and a BIP32 derivation path,
# compute the first 2000 child private keys.
# Return an array of keys encoded as bytes.
# The derivation path is formatted as an array of (index: int, hardened: bool) tuples.
def get_wallet_privs(key: bytes, chaincode: bytes, path: List[Tuple[int, bool]]) -> List[bytes]:
    privs = []
    current_key = key
    current_chaincode = chaincode
    
    for index, hardened in path:
        derived = derive_priv_child(current_key, current_chaincode, index, hardened)
        current_key = derived["key"]
        current_chaincode = derived["chaincode"]
    
    for i in range(2000):
        derived = derive_priv_child(current_key, current_chaincode, i, False)
        privs.append(derived["key"])
    
    return privs


# Derive the p2wpkh witness program (aka scriptPubKey) for a given compressed public key.
# Return a bytes array to be compared with the JSON output of Bitcoin Core RPC getblock
# so we can find our received transactions in blocks.
# These are segwit version 0 pay-to-public-key-hash witness programs.
# https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#user-content-P2WPKH
def get_p2wpkh_program(pubkey: bytes) -> bytes:
    """Derive the P2WPKH witness program (scriptPubKey) for a given compressed public key."""
    hashed_pubkey = hashlib.new('ripemd160', hashlib.sha256(pubkey).digest()).digest()
    return b"\x00" + len(hashed_pubkey).to_bytes(1, 'big') + hashed_pubkey


# Assuming Bitcoin Core is running and connected to signet using default datadir,
# execute an RPC and return its value or error message.
# https://github.com/bitcoin/bitcoin/blob/master/doc/bitcoin-conf.md#configuration-file-path
# Examples: bcli("getblockcount")
#           bcli("getblockhash 100")
def bcli(cmd: str):
    res = run(
            ["bitcoin-cli", "-signet"] + cmd.split(" "),
            capture_output=True,
            encoding="utf-8")
    if res.returncode == 0:
        return res.stdout.strip()
    else:
        raise Exception(res.stderr.strip())


# Recover the wallet state from the blockchain:
# - Parse tprv and path from descriptor and derive 2000 key pairs and witness programs
# - Request blocks 0-310 from Bitcoin Core via RPC and scan all transactions
# - Return a state object with all the derived keys and total wallet balance
def recover_wallet_state(tprv: str, on_event=None) -> dict:
    emit = on_event or (lambda _e: None)
    decoded = base58_decode(tprv)
    key_data = deserialize_key(decoded)
    master_private_key = key_data["key"]
    master_chain_code = key_data["chaincode"]
    path = [(84, True), (1, True), (0, True), (0, False)]

    # Generate all the keypairs and witness programs to search for
    privs = get_wallet_privs(master_private_key, master_chain_code, path)
    pubs = [get_pub_from_priv(priv) for priv in privs]
    programs = [get_p2wpkh_program(pub) for pub in pubs]

    # Prepare a wallet state data structure
    state = {
        "utxo": {},
        "balance": 0,
        "privs": privs,
        "pubs": pubs,
        "programs": programs
    }

    # Scan blocks 0-300
    height = 150
    for h in range(height + 1):
        emit(BlockScanned(height=h))  # <--- stream progress
        block_hash = bcli(f"getblockhash {h}")
        # log(f"Scanning block {h}")
        
        block = json.loads(bcli(f"getblock {block_hash} 2"), parse_float=Decimal)
        txs = block["tx"]

        # Scan every tx in every block
        for tx in txs:
            # Check every tx input (witness) for our own compressed public keys.
            # These are coins we have spent.
            for inp in tx["vin"]:
                if "txinwitness" in inp:
                    witness = inp["txinwitness"]
                    if len(witness) >= 2:
                        pubkey = witness[1]
                        for pub in pubs:
                            if pubkey == pub.hex():
                                outpoint = f"{inp['txid']}:{inp['vout']}"
                                # log(f"Found matching pubkey {pubkey} and outpoint {outpoint}")
                                if outpoint in state["utxo"]:
                                    # Remove this coin from our wallet state utxo pool
                                    # so we don't double spend it later
                                    spent_value = state["utxo"][outpoint]["value"]
                                    emit(UTXOSpent(outpoint=outpoint, value=spent_value))
                                    # log(f"utxo found with value {spent_value}")
                                    state["balance"] -= state["utxo"][outpoint]["value"]
                                    del state["utxo"][outpoint]
                                    emit(BalanceUpdated(balance=state["balance"]))
                                    # log(f"Updated balance: {state['balance']}")

            # Check every tx output for our own witness programs.
            # These are coins we have received.
            for out in tx["vout"]:
                    # Add to our total balance
                script_pub_key = out["scriptPubKey"]
                if "hex" in script_pub_key:
                    program = bytes.fromhex(script_pub_key["hex"])
                    if program in programs:
                        # log(f"Found matching witness program {script_pub_key["hex"]}, output {out['n']}, value {Decimal(out["value"])} BTC")
                        outpoint = f"{tx['txid']}:{out['n']}"
                        program_index = programs.index(program)
                        # Keep track of this UTXO by its outpoint in case we spend it later
                        state["utxo"][outpoint] = {
                            "value": Decimal(out["value"]),
                            "program_index": program_index # Store the program index
                        }
                        val = Decimal(out["value"])
                        state["balance"] += val
                        emit(UTXOReceived(outpoint=outpoint, value=val, program_index=program_index))
                        emit(BalanceUpdated(balance=state["balance"]))
                        # log(f"Updated balance: {state['balance']}")


    return state


def recover_and_feed_streaming(xprv: str, out_q: "queue.Queue[object]") -> None:
    try:
        def on_event(ev):  # called *within* recover_wallet_state loops
            out_q.put(ev)
        recover_wallet_state(xprv, on_event=on_event)
    finally:
        out_q.put(SENTINEL)


def event_to_tasks(ev) -> list[MidiTask]:
    global _LAST_BALANCE_PITCH
    # --- simple, musical defaults you can tweak freely ---
    if isinstance(ev, BlockScanned):
        # Encode block height as an overtone over four octaves starting at C0
        # Move to next overtone every 20 blocks
        # Only sound every 5 blocks
        if ev.height % 5 == 0:
            pitch = 24
            for i in range(0, ev.height // 20):
                pitch += OVERTONES[i]
            log(f"Block height: {ev.height}, Pitch: {pitch}")
            return [MidiTask(pitch, velocity=50, duration_ms=140, channel=1, controller=10, controller_value=40)]
        return []
    if isinstance(ev, UTXOReceived):
        # Larger values → higher velocity; program_index nudges pitch
        sats = int(ev.value * Decimal(100_000_000))
        vel = 60 + min(67, sats // 1_000_000)          # cap at ~127
        pitch = 60 + (ev.program_index % 24)           # map script variant
        log(f"UTXO Received: {ev.value} BTC, Program index: {ev.program_index}, Pitch: {pitch}")
        return [MidiTask(pitch=pitch, velocity=vel, duration_ms=140, channel=2, controller=10, controller_value=64)]
    if isinstance(ev, UTXOSpent):
        # A softer “down” motif for spends
        pitch = 36 + (hash(ev.outpoint) % 12)          # deterministic but varied
        log(f"UTXO Spent Outpoint: {ev.outpoint}, Pitch: {pitch}")
        return [MidiTask(pitch=pitch, velocity=50, duration_ms=100, channel=0, controller=10, controller_value=100)]
    if isinstance(ev, BalanceUpdated):
        new_pitch = _pitch_from_balance(ev.balance)
        log(f"Wallet balance upated to: {ev.balance} BTC, calculated pitch: {new_pitch}")
        if _LAST_BALANCE_PITCH is not None and new_pitch == _LAST_BALANCE_PITCH:
            return []  # ignore small/no-op changes that map to the same note

        _LAST_BALANCE_PITCH = new_pitch
        
        return [MidiTask(pitch=new_pitch, velocity=64, duration_ms=120, channel=3, controller=10, controller_value=80)]
    return []  # unknown events → silent

def metronome_scheduler(
    tick_seconds: float,
    inbox: "queue.Queue[object]",
    send_note_fn,
    max_notes_per_tick: int = 1,
    stop_when_empty: bool = True,
) -> None:
    pending = deque()
    producer_done = False
    next_deadline = time.monotonic()

    while True:
        # Pull all currently available events and expand them to tasks
        while True:
            try:
                item = inbox.get_nowait()
            except queue.Empty:
                break
            if item is SENTINEL:
                producer_done = True
            else:
                pending.extend(event_to_tasks(item))

        # Play up to K tasks this tick
        for _ in range(min(max_notes_per_tick, len(pending))):
            send_note_fn(pending.popleft())

        # Exit when producer is done and every task is drained
        if stop_when_empty and producer_done and not pending and inbox.empty():
            break

        # Drift-resistant sleep
        next_deadline += tick_seconds
        remain = next_deadline - time.monotonic()
        if remain > 0:
            time.sleep(remain)
        else:
            next_deadline = time.monotonic()


if __name__ == "__main__":
    # Use the same period you pass to your click-track metronome, e.g. 0.2s (≈120 BPM, 8th-note grid)
    TICK_SECONDS = 0.2

    inbox: "queue.Queue[object]" = queue.Queue(maxsize=1024)  # backpressure if recovery discovers a lot

    # 1) Producer: recover and enqueue tasks
    t_producer = threading.Thread(
        target=recover_and_feed_streaming,
        args=(EXTENDED_PRIVATE_KEY, inbox),
        daemon=True,  # producer can be daemon — we gate shutdown via the consumer
        name="recover-producer",
    )

    # 2) Optional: keep your existing audible click running independently
    t_click = threading.Thread(
        target=metronome,
        args=(TICK_SECONDS, 5, 1),   # your existing signature (period, count, velocity)
        daemon=True,                   # don't block program exit
        name="click-track",
    )

    # 3) Consumer: plays queued notes on the grid, then exits when drained
    t_player = threading.Thread(
        target=metronome_scheduler,
        args=(TICK_SECONDS, inbox, send_note_via_mido),
        kwargs={"max_notes_per_tick": 1, "stop_when_empty": True},
        daemon=False,                  # ensure we wait for clean drain
        name="player",
    )

    t_producer.start()
    # t_click.start()
    t_player.start()

    # Wait until everything queued has been played
    t_player.join()
    # (No need to join the daemon threads; program exits now.)

    

