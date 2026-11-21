"""Reproduce Sigma Carry and Sigma Clip and write the result ledgers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import monthly, run, score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"

EXPECTED = {
    "sigma-carry": {"end": 15843.35, "low": 500.0, "red_months": 5},
    "sigma-clip": {"end": 10815.2, "low": 628.9, "red_months": 4},
}


def main():
    OUT.mkdir(exist_ok=True)
    for name, clip in (("sigma-carry", False), ("sigma-clip", True)):
        df = run(clip)
        st = score(df)
        mo = monthly(df)
        df.to_csv(OUT / f"{name}-daily.csv", index=False)
        mo.rename("pnl").to_csv(OUT / f"{name}-monthly.csv", header=True)
        exp = EXPECTED[name]
        print(name, {k: round(st[k], 2) if isinstance(st[k], float) else st[k] for k in st})
        if abs(st["end"] - exp["end"]) > 1.0:
            raise SystemExit(f"{name} end {st['end']} != {exp['end']}")
        if abs(st["low"] - exp["low"]) > 1.0:
            raise SystemExit(f"{name} low {st['low']} != {exp['low']}")
        if st["red_months"] != exp["red_months"]:
            raise SystemExit(f"{name} red months {st['red_months']} != {exp['red_months']}")
    print("matched published accounts")


if __name__ == "__main__":
    main()
