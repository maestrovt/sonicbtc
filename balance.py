from decimal import Decimal
from ecdsa import SigningKey, SECP256k1
from subprocess import run
from typing import List, Tuple
import hashlib
import hmac
import json

# Provided by administrator
WALLET_NAME = "wallet_171"
EXTENDED_PRIVATE_KEY = "tprv8ZgxMBicQKsPdyeZaFF6JRjdJ24oy7dC9FvYrtaqTrhhRbs9vXMCMwsFn95Gg7rhkHwX5piq66LN69iJfxBWFtL5tQAdm4atSq5eBHP7nZT"

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
def recover_wallet_state(tprv: str):
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
    height = 300
    for h in range(height + 1):
        block_hash = bcli(f"getblockhash {h}")
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
                                if outpoint in state["utxo"]:
                                    state["balance"] -= state["utxo"][outpoint]["value"]
                                    del state["utxo"][outpoint]

                    # Remove this coin from our wallet state utxo pool
                    # so we don't double spend it later

            # Check every tx output for our own witness programs.
            # These are coins we have received.
            for out in tx["vout"]:
                    # Add to our total balance
                script_pub_key = out["scriptPubKey"]
                if "hex" in script_pub_key:
                    program = bytes.fromhex(script_pub_key["hex"])
                    if program in programs:
                        outpoint = f"{tx['txid']}:{out['n']}"
                        program_index = programs.index(program)
                        state["utxo"][outpoint] = {
                            "value": Decimal(out["value"]),
                            "program_index": program_index # Store the program index
                        }

                        state["balance"] += Decimal(out["value"])

                    # Keep track of this UTXO by its outpoint in case we spend it later

    return state


if __name__ == "__main__":
    print(f"{WALLET_NAME} {recover_wallet_state(EXTENDED_PRIVATE_KEY)['balance']}")
