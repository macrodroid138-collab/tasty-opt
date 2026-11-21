"""Step through one session and record what the engine decided.

The pnl of the last frame matches trade_day. The quote tape attached to the
entry frame is a demonstration of the sanitizer and the walk around the
model credit. Historical option quotes are not in the study.
"""

from __future__ import annotations

import math

import pandas as pd

from src.engine import (
    BANK_CUTOFF,
    CLOSE_MINUTE,
    ENTRY_MINUTE,
    FEE,
    IV_FLOOR,
    SLIP,
    WIDTH,
    _close_package,
    call_spread,
    load_inputs,
    put_spread,
    time_to_expiry,
    trade_day,
)
from programs.common.quotes import LegQuote, PackageQuote, QuoteBook
from programs.common.walk import OrderWalk


def _clock(minute: float) -> str:
    total = 9 * 60 + 30 + int(minute)
    return f"{total // 60:02d}:{total % 60:02d}"


def _tape(credit: float) -> list[dict]:
    """A short scripted quote tape around the model credit, including one flash."""
    book = QuoteBook()
    walk = OrderWalk(urgent=False)
    frames = []
    # five good quotes, one absurd flash, five more good quotes
    samples = [credit, credit + 0.01, credit - 0.01, credit, credit + 0.02,
               credit + 2.50, credit, credit - 0.01, credit, credit, credit]
    for i, price in enumerate(samples):
        ts = i * 0.4
        leg = LegQuote(max(price, 0.01) - 0.02, max(price, 0.01) + 0.02, ts) if price < 2 else LegQuote(0.01, 3.0, ts)
        state = book.consider([leg, leg, leg, leg], PackageQuote(price, "credit", ts, 691.0, credit))
        frames.append({
            "t": round(ts, 1),
            "quote": None if state.last_reject else round(price, 2),
            "reject": state.last_reject,
            "median": None if state.value is None else state.value,
            "tradable": state.tradable,
            "samples": state.samples,
        })
    if book.state.value is not None:
        status = walk.start(book.state.value)
        frames.append({"t": 4.0, "walk": {"attempt": status.attempt, "working": status.working, "phase": status.phase, "note": status.note}})
        status = walk.fill()
        frames.append({"t": 4.2, "walk": {"attempt": status.attempt, "working": status.working, "phase": status.phase, "note": status.note}})
    return frames


def trace_day(day: str, clip: bool) -> list[dict]:
    sessions, by_day, sigmap, srcmap = load_inputs()
    sessions["day"] = pd.to_datetime(sessions["day"])
    target = pd.Timestamp(day)
    row = sessions[sessions["day"] == target]
    if row.empty:
        raise SystemExit(f"{day} is not in the study")
    row = row.iloc[0]
    prior = sessions[sessions["day"] < target].iloc[-1]
    points = [(float(m), float(s)) for m, s in by_day[target]]
    sig = float(sigmap[target])
    close_px = float(row["close_px"])
    gap = (target - pd.Timestamp(prior["day"])).days
    range_skip = gap <= 10 and float(prior["range_pts"]) >= 16
    base = {
        "day": day,
        "trader": "sigma-clip" if clip else "sigma-carry",
        "sig": sig,
        "ivSource": srcmap[target],
        "priorRange": round(float(prior["range_pts"]), 2),
    }
    frames: list[dict] = []

    def push(minute, phase, note, **extra):
        frames.append({**base, "minute": minute, "clock": _clock(minute) if minute is not None else "09:30", "phase": phase, "note": note, "pnl": extra.get("pnl"), **extra})

    if range_skip:
        push(0, "skip", f"Prior range {float(prior['range_pts']):.1f} scaled points is at least 16. No trade.", pnl=0.0)
        return frames
    if sig < IV_FLOOR:
        push(0, "skip", f"Volatility {sig:.1%} is under 11%. No trade.", pnl=0.0)
        return frames
    morn = [s for m, s in points if m < ENTRY_MINUTE]
    pts = [(m, s) for m, s in points if m >= ENTRY_MINUTE - 1e-9]
    if len(pts) < 2:
        push(0, "skip", "No 10:30 print.", pnl=0.0)
        return frames
    morning_range = max(morn) - min(morn)
    anchor = pts[0][1]
    dist = max(6, int(round(anchor * sig * math.sqrt(time_to_expiry(pts[0][0])))))
    put_k = int(round(anchor)) - dist
    call_k = int(round(anchor)) + dist
    if morning_range >= dist:
        push(ENTRY_MINUTE, "skip", f"First hour ranged {morning_range:.1f}, which already covers the {dist}-point short. No trade.", pnl=0.0, dist=dist, anchor=round(anchor, 2))
        return frames

    credit = put_spread(anchor, pts[0][0], put_k, WIDTH, sig) + call_spread(anchor, pts[0][0], call_k, WIDTH, sig)
    cash = credit * 100.0 - FEE * 4 - SLIP * 100.0
    push(pts[0][0], "entry", f"Sold the {dist}-point condor for {credit:.2f} credit. Fees $4, slippage $2.",
         pnl=None, dist=dist, anchor=round(anchor, 2),
         strikes={"putLong": put_k - 5, "putShort": put_k, "callShort": call_k, "callLong": call_k + 5},
         credit=round(credit, 4), cash=round(cash, 2), put="5-wide", call="5-wide",
         tape=_tape(credit))
    put = (put_k, WIDTH)
    call = (call_k, WIDTH)
    pending = None
    bank_at = dist + 2
    next_watch = 75.0
    for minute, price in pts[1:]:
        while minute >= next_watch:
            push(next_watch, "watching", f"Still watching. Scaled price {price:.2f}. Nothing new to do.",
                 price=round(price, 2), dist=dist, anchor=round(anchor, 2), cash=round(cash, 2),
                 put="flat" if not put else f"{put[1]}-wide", call="flat" if not call else f"{call[1]}-wide",
                 pending=None if not pending else pending["dir"])
            next_watch += 15
        note = None
        phase = "managing"
        if pending is not None:
            if pending["dir"] == "down" and price >= anchor - 4:
                pending = None
                note = "Price came back inside 4 points. The pending flag cleared."
            elif pending is not None and pending["dir"] == "up" and price <= anchor + 4:
                pending = None
                note = "Price came back inside 4 points. The pending flag cleared."
            elif pending is not None and minute + 1e-9 >= pending["minute"] + 30:
                pending = None
                note = "Thirty minutes passed. The pending flag cleared."
        if clip and put and call and put[1] == WIDTH and call[1] == WIDTH:
            cost = put_spread(price, minute, put[0], put[1], sig) + call_spread(price, minute, call[0], call[1], sig)
            if cost <= credit * 0.40:
                cash = cash - cost * 100.0 - FEE * 4 - SLIP * 100.0
                push(minute, "buyback", f"Untouched condor could be bought for {cost:.2f}, which is 40% of the {credit:.2f} credit. Bought it.",
                     pnl=round(cash, 2), price=round(price, 2), dist=dist, anchor=round(anchor, 2), cash=round(cash, 2), put="flat", call="flat")
                _check(day, clip, close_px, points, cash)
                return frames
        if put and put[1] == WIDTH and price <= put[0] - 1:
            k = put[0]
            cash -= put_spread(price, minute, k - 2, 3, sig) * 100.0 + FEE * 2 + SLIP * 100.0
            put = (k, 2)
            note = f"Price traded through the put short {k}. Cut that wing to 2-wide."
            phase = "touch"
        if call and call[1] == WIDTH and price >= call[0] + 1:
            k = call[0]
            cash -= call_spread(price, minute, k + 2, 3, sig) * 100.0 + FEE * 2 + SLIP * 100.0
            call = (k, 2)
            note = f"Price traded through the call short {k}. Cut that wing to 2-wide."
            phase = "touch"
        if clip and (put or call):
            liq = _close_package(cash, minute, price, put, call, sig)
            if liq <= -100.0:
                push(minute, "stop", "The day is down $100. Flattened.", pnl=round(liq, 2), price=round(price, 2), dist=dist, anchor=round(anchor, 2), cash=round(liq, 2), put="flat", call="flat")
                _check(day, clip, close_px, points, liq)
                return frames
        if pending is None and minute < BANK_CUTOFF and (put or call):
            if call and price <= anchor - bank_at:
                k, w = call
                cash -= call_spread(price, minute, k, w, sig) * 100.0 + FEE * 2 + SLIP * 100.0
                call = None
                pending = {"dir": "down", "minute": minute}
                note = f"Price is {bank_at} points under the anchor. Bought back the call wing."
                phase = "bank"
            elif put and price >= anchor + bank_at:
                k, w = put
                cash -= put_spread(price, minute, k, w, sig) * 100.0 + FEE * 2 + SLIP * 100.0
                put = None
                pending = {"dir": "up", "minute": minute}
                note = f"Price is {bank_at} points over the anchor. Bought back the put wing."
                phase = "bank"
        if note:
            push(minute, phase, note, pnl=None, price=round(price, 2), dist=dist, anchor=round(anchor, 2), cash=round(cash, 2),
                 put="flat" if not put else f"{put[1]}-wide", call="flat" if not call else f"{call[1]}-wide",
                 pending=None if not pending else pending["dir"])
    if put or call:
        cash = _close_package(cash, CLOSE_MINUTE, close_px, put, call, sig)
    push(CLOSE_MINUTE, "close", "15:15. Bought back whatever was still open.", pnl=round(cash, 2), dist=dist, anchor=round(anchor, 2), cash=round(cash, 2),
         put="flat" if not put else f"{put[1]}-wide", call="flat" if not call else f"{call[1]}-wide")
    _check(day, clip, close_px, points, cash)
    return frames


def _check(day, clip, close_px, points, cash) -> None:
    official = trade_day(points, close_px, _sig(day), clip)
    if abs(official - cash) > 0.01:
        raise RuntimeError(f"trace pnl {cash} != engine {official} on {day}")


def _sig(day: str) -> float:
    _, _, sigmap, _ = load_inputs()
    return float(sigmap[pd.Timestamp(day)])
