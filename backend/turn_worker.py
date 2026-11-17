"""Execute one private chat turn and emit a single JSON result."""
import json
import sys
from time import monotonic

from .engine import SaarthiEngine
from .execution import timings


def main() -> None:
    payload = json.load(sys.stdin)
    report: dict[str, float] = {}
    token = timings.set(report)
    started = monotonic()
    try:
        result = SaarthiEngine().run(**payload)
        result["timings_ms"] = {**report, "engine": round((monotonic() - started) * 1000, 2)}
        json.dump(result, sys.stdout, default=str, allow_nan=False)
    finally:
        timings.reset(token)


if __name__ == "__main__":
    main()
