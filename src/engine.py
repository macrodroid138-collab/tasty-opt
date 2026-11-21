"""Normative implementation of Sigma Carry and Sigma Clip.

Dollar results are in scaled dollars. See traders/SHARED.md. The order of
operations inside the day loop is part of the result; do not reorder it.
"""

from __future__ import annotations

import math
import pandas as pd

from src.paths import project_root

ROOT = project_root()
DATA = ROOT / "data"

R = 0.043
Q = 0.012
FEE = 1.0          # dollars per leg
SLIP = 0.02        # premium, once per order
SCALE = 691.0      # session open is mapped to this price
IV_FLOOR = 0.11
RANGE_SKIP = 16.0  # prior session high-low, scaled points
GAP_RESET = 10     # calendar days; a longer gap drops the prior range
ENTRY_MINUTE = 60  # 10:30
CLOSE_MINUTE = 345 # 3:15
BANK_CUTOFF = 300  # 2:30; no far-wing buyback after this
WIDTH = 5
START_EQUITY = 700.0
START_DAY = "2022-01-05"


def ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs(S: float, K: float, T: float, sig: float, opt: str) -> float:
    if T <= 1e-12 or sig <= 0 or S <= 0 or K <= 0:
        return max(S - K, 0.0) if opt == "c" else max(K - S, 0.0)
    disc_q = math.exp(-Q * T)
    disc_r = math.exp(-R * T)
    vol = sig * math.sqrt(T)
    d1 = (math.log(S / K) + (R - Q + 0.5 * sig * sig) * T) / vol
    d2 = d1 - vol
    if opt == "c":
        return max(0.0, S * disc_q * ncdf(d1) - K * disc_r * ncdf(d2))
    return max(0.0, K * disc_r * ncdf(-d2) - S * disc_q * ncdf(-d1))


def time_to_expiry(minute: float) -> float:
    """Year-fraction from this minute until 16:00, with a 1.2-minute floor."""
    hours_left = max((390.0 - minute) / 60.0, 0.02)
    return hours_left / 6.5 / 252.0


def call_spread(S: float, minute: float, short: int, width: int, sig: float) -> float:
    t = time_to_expiry(minute)
    return bs(S, short, t, sig, "c") - bs(S, short + width, t, sig, "c")


def put_spread(S: float, minute: float, short: int, width: int, sig: float) -> float:
    t = time_to_expiry(minute)
    return bs(S, short, t, sig, "p") - bs(S, short - width, t, sig, "p")


def load_inputs():
    sessions = pd.read_parquet(DATA / "sessions.parquet")
    sessions["day"] = pd.to_datetime(sessions["day"])
    path = pd.read_parquet(DATA / "path.parquet")
    path["day"] = pd.to_datetime(path["day"])
    iv = pd.read_csv(DATA / "session_iv.csv")
    iv["day"] = pd.to_datetime(iv["day"])
    by_day = {pd.Timestamp(d): g[["minute", "scaled"]].to_numpy() for d, g in path.groupby("day")}
    sig = {pd.Timestamp(r.day): float(r.sig) for r in iv.itertuples()}
    src = {pd.Timestamp(r.day): r.iv_source for r in iv.itertuples()}
    return sessions, by_day, sig, src


def _close_package(cash, minute, S, put, call, sig):
    p = put_spread(S, minute, put[0], put[1], sig) if put else 0.0
    c = call_spread(S, minute, call[0], call[1], sig) if call else 0.0
    n = (2 if put else 0) + (2 if call else 0)
    cash -= (p + c) * 100.0 + FEE * n + SLIP * 100.0
    return cash


def trade_day(points, close_px, sig, clip: bool) -> float:
    """One session. Returns scaled-dollar pnl, or 0.0 when the day is filtered out.

    points: sequence of (minute_from_0930, scaled_price) with minute < 345.
    """
    morn = [S for m, S in points if m < ENTRY_MINUTE]
    morning_range = (max(morn) - min(morn)) if len(morn) >= 2 else 0.0
    pts = [(m, S) for m, S in points if m >= ENTRY_MINUTE - 1e-9]
    if len(pts) < 2 or sig < IV_FLOOR:
        return 0.0
    anchor = pts[0][1]
    sigma_points = anchor * sig * math.sqrt(time_to_expiry(pts[0][0]))
    dist = max(6, int(round(sigma_points)))
    if morning_range >= dist:
        return 0.0

    put_k = int(round(anchor)) - dist
    call_k = int(round(anchor)) + dist
    put = (put_k, WIDTH)
    call = (call_k, WIDTH)
    credit = put_spread(anchor, pts[0][0], put_k, WIDTH, sig) + call_spread(anchor, pts[0][0], call_k, WIDTH, sig)
    cash = credit * 100.0 - FEE * 4 - SLIP * 100.0
    pending = None
    bank_at = dist + 2

    for minute, price in pts[1:]:
        if pending is not None:
            if pending["dir"] == "down" and price >= anchor - 4:
                pending = None
            elif pending is not None and pending["dir"] == "up" and price <= anchor + 4:
                pending = None
            elif pending is not None and minute + 1e-9 >= pending["minute"] + 30:
                pending = None

        if clip and put and call and put[1] == WIDTH and call[1] == WIDTH:
            cost = put_spread(price, minute, put[0], put[1], sig) + call_spread(price, minute, call[0], call[1], sig)
            if cost <= credit * 0.40:
                return cash - cost * 100.0 - FEE * 4 - SLIP * 100.0

        if put and put[1] == WIDTH and price <= put[0] - 1:
            k = put[0]
            cash -= put_spread(price, minute, k - 2, 3, sig) * 100.0 + FEE * 2 + SLIP * 100.0
            put = (k, 2)
        if call and call[1] == WIDTH and price >= call[0] + 1:
            k = call[0]
            cash -= call_spread(price, minute, k + 2, 3, sig) * 100.0 + FEE * 2 + SLIP * 100.0
            call = (k, 2)

        if clip and (put or call):
            liq = _close_package(cash, minute, price, put, call, sig)
            if liq <= -100.0:
                return liq

        if pending is None and minute < BANK_CUTOFF and (put or call):
            if call and price <= anchor - bank_at:
                k, w = call
                cash -= call_spread(price, minute, k, w, sig) * 100.0 + FEE * 2 + SLIP * 100.0
                call = None
                pending = {"dir": "down", "minute": minute}
            elif put and price >= anchor + bank_at:
                k, w = put
                cash -= put_spread(price, minute, k, w, sig) * 100.0 + FEE * 2 + SLIP * 100.0
                put = None
                pending = {"dir": "up", "minute": minute}

    if put or call:
        cash = _close_package(cash, CLOSE_MINUTE, close_px, put, call, sig)
    return cash


def run(clip: bool) -> pd.DataFrame:
    sessions, by_day, sigmap, srcmap = load_inputs()
    sessions = sessions.sort_values("day").reset_index(drop=True)
    start = sessions.index[sessions["day"] >= START_DAY][0]
    equity = START_EQUITY
    pending_loss = False
    rows = []
    prev_range = float(sessions.loc[start - 1, "range_pts"])
    prev_day = pd.Timestamp(sessions.loc[start - 1, "day"])
    for i in range(start, len(sessions)):
        day = pd.Timestamp(sessions.loc[i, "day"])
        gap = (day - prev_day).days
        range_skip = gap <= GAP_RESET and prev_range >= RANGE_SKIP
        sig = sigmap[day]
        raw = 0.0 if range_skip else trade_day(by_day[day], float(sessions.loc[i, "close_px"]), sig, clip)
        if range_skip or raw == 0.0:
            pnl = 0.0
            kind = "range" if range_skip else "flat"
        elif pending_loss:
            pnl = 0.0
            pending_loss = False
            kind = "loss_skip"
        else:
            pnl = raw
            kind = "trade"
            if pnl < 0:
                pending_loss = True
        equity += pnl
        rows.append((day, pnl, equity, kind, sig, srcmap[day]))
        prev_range = float(sessions.loc[i, "range_pts"])
        prev_day = day
    return pd.DataFrame(rows, columns=["day", "pnl", "equity", "kind", "sig", "iv_source"])


def monthly(df: pd.DataFrame) -> pd.Series:
    return df.groupby(df["day"].dt.to_period("M"))["pnl"].sum()


def score(df: pd.DataFrame) -> dict:
    mo = monthly(df)
    red = mo[mo < -0.5]
    traded = df[df["kind"] == "trade"]
    wins = traded[traded["pnl"] > 0]
    losses = traded[traded["pnl"] < 0]
    return {
        "end": float(df["equity"].iloc[-1]),
        "low": float(df["equity"].min()),
        "low_day": str(df.loc[df["equity"].idxmin(), "day"].date()),
        "median_month": float(mo.median()),
        "month_spread": float(mo.std(ddof=1)),
        "biggest_month": float(mo.max()),
        "worst_month": float(mo.min()),
        "red_months": int(len(red)),
        "red_sum": float(red.sum()) if len(red) else 0.0,
        "trades": int(len(traded)),
        "win_rate": float((traded["pnl"] > 0).mean()) if len(traded) else 0.0,
        "median_win": float(wins["pnl"].median()) if len(wins) else 0.0,
        "median_loss": float(losses["pnl"].median()) if len(losses) else 0.0,
        "months": int(len(mo)),
    }
