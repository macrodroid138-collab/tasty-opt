import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.trace import trace_day

if __name__ == "__main__":
    day, trader = sys.argv[1], sys.argv[2]
    json.dump(trace_day(day, trader == "sigma-clip"), sys.stdout)
