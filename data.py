from dataclasses import dataclass
from decimal import Decimal

# --- streaming events produced by recover_wallet_state ---

@dataclass
class BlockScanned:
    height: int

@dataclass
class UTXOSpent:
    outpoint: str
    value: Decimal

@dataclass
class UTXOReceived:
    outpoint: str
    value: Decimal
    program_index: int  # which witness program matched

@dataclass
class BalanceUpdated:
    balance: Decimal

SENTINEL = object()  # tells consumer “producer is finished”
# --- metronome-consumer's unit of work ---

@dataclass
class MidiTask:
    pitch: int
    velocity: int = 96
    duration_ms: int = 120
    channel: int = 0
    controller: int = 10
    controller_value: int = 64
