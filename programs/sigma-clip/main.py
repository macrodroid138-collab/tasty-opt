"""Sigma Clip, independent of Sigma Carry.

  python programs/sigma-clip/main.py --mode demo --day 2024-12-18
  python programs/sigma-clip/main.py --mode live
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from programs.common.tasty import TastyClient  # noqa: E402
from src.paths import project_root  # noqa: E402
from src.trace import trace_day  # noqa: E402

ROOT = project_root()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sigma Clip")
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--day", default="2023-01-17")
    args = parser.parse_args()
    client = TastyClient(args.mode)
    print(json.dumps({"trader": "sigma-clip", "tasty": client.status().__dict__}, default=str))
    if args.mode == "live":
        if "needs" in client.status().message:
            sys.exit(2)
        return
    frames = trace_day(args.day, clip=True)
    out = ROOT / "results" / f"trace-sigma-clip-{args.day}.json"
    out.write_text(json.dumps(frames))
    print(json.dumps({"day": args.day, "frames": len(frames), "pnl": frames[-1]["pnl"] if frames else None, "wrote": str(out)}))


if __name__ == "__main__":
    main()
