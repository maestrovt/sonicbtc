from decimal import Decimal
from constants import OVERTONES, TODI_SPANS, TODI_THAAT, BASE_BALANCE_PITCH
from utilities import log
def _pitch_from_balance(balance: Decimal) -> int:
    """
    Map ev.balance (Decimal, < 15 BTC) to a MIDI pitch:
      - Start at BASE_PITCH.
      - Add the first N values of OVERTONES where N = floor(balance in BTC).
      - For the fractional part, walk the TODI_SPANS cumulatively and
        add the corresponding TODI_THAAT step at each interval until
        cumulative >= fractional (like your 0.54 → take 1,2,3,1).
    """
    # Normalize and split
    if not isinstance(balance, Decimal):
        balance = Decimal(balance)

    if balance < 0:
        balance = Decimal(0)

    # Integer BTC (N) and fractional part f in [0, 1)
    N = int(balance)  # floor
    # N = int(balance) + (1 if balance % 1 != 0 else 0) # ceiling
    if N >= len(OVERTONES):  # safety although you said <15
        N = len(OVERTONES) - 1

    f = balance - Decimal(N)

    # Start at base pitch
    pitch = BASE_BALANCE_PITCH

    # A) Add the first N OVERTONES
    if N > 0:
        pitch += sum(OVERTONES[:N])

    # B) Walk TODI_SPANS for the fractional part (ceil-like)
    # Accumulate spans until we reach or exceed f
    cum = 0.0
    for i, span in enumerate(TODI_SPANS):
        if cum < float(f):
            pitch += TODI_THAAT[i]  # add the ith semitone step
            cum += span
        else:
            break
    log(f"Balance: {balance}, N: {N}, Fraction: {cum}")

    return pitch
