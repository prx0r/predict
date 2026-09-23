"""bneck2 advise — confidence-weighted advice sequences (NORTHSTAR-5).

Advice is a persistent object per holding: OPEN -> FILLED -> CLOSED.
Each window: a(i,t) = signal * confidence; |a| < 0.10 -> HOLD.
Confidence per family = Wilson-lower-mapped hit rate, measured from
receipts — never assumed. Buybacks trigger on signal flip or retrace
to trailing reference, sized by |a| again.
"""
from __future__ import annotations


def confidence_from_lower(lo: float) -> float:
    """Map Wilson lower bound to [0,1] sizing multiplier."""
    return round(min(max((lo - 0.5) * 4.0, 0.0), 1.0), 3)


def advise(signal: float, confidence: float,
           dust: float = 0.10) -> dict:
    """One window's advice: fraction of position to trade + side."""
    a = float(signal) * float(confidence)
    if abs(a) < dust:
        return {"action": "HOLD", "fraction": 0.0, "raw": round(a, 4)}
    side = "SELL" if a < 0 else "BUY"
    return {"action": side, "fraction": round(min(abs(a), 1.0), 3),
            "raw": round(a, 4)}


def buyback_trigger(entry_price: float, current_price: float,
                    signal_now: float, signal_then: float,
                    trail_low: float | None = None) -> dict:
    """Rebuy when signal flips positive or price retraces to trailing ref."""
    flip = signal_then <= 0 < signal_now
    retrace = (trail_low is not None and trail_low > 0
               and current_price <= trail_low * 1.02)
    if flip or retrace:
        return {"rebuy": True,
                "reason": "flip" if flip else "retrace"}
    return {"rebuy": False, "reason": ""}


def sequence_update(seq: dict | None, advice: dict,
                    price: float) -> dict:
    """Fold one window into the persistent advice sequence."""
    seq = dict(seq) if seq else {"state": "FLAT", "history": []}
    seq["history"] = (seq.get("history", []) + [{
        "action": advice["action"], "fraction": advice["fraction"],
        "price": price}])[-52:]
    if advice["action"] == "SELL" and advice["fraction"] >= 0.5:
        seq["state"] = "SHORT-WATCH"
    elif advice["action"] == "BUY" and advice["fraction"] >= 0.5:
        seq["state"] = "LONG"
    elif advice["action"] == "HOLD":
        pass
    else:
        seq["state"] = "TRIMMED"
    return seq
