#!/usr/bin/env python3
"""Generate a realistic sample run so the plotting script can be tried out
before any hardware or simulator is connected.

    python host/make_sample.py --out data/sample_run.csv
"""
import argparse
import math
import pathlib
import random


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/sample_run.csv")
    ap.add_argument("--minutes", type=float, default=20.0)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    random.seed(args.seed)
    period_ms = 2000
    n = int(args.minutes * 60_000 / period_ms)

    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = 26.0
    hum = 64.0
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("millis,temperature_c,humidity_pct,setpoint_c,alarm\n")
        for i in range(n):
            t = i * period_ms
            minutes = t / 60_000

            # a slow warm-up with a small ripple and sensor noise on top
            target = 26.0 + 8.0 * (1 - math.exp(-minutes / 6.0)) \
                     + 0.6 * math.sin(minutes * 1.3)
            temp += 0.3 * (target - temp) + random.gauss(0, 0.05)

            # humidity falls as the air warms
            hum += 0.3 * ((64.0 - 1.1 * (temp - 26.0)) - hum) + random.gauss(0, 0.08)

            setpoint = 31.5
            alarm = 1 if temp > setpoint else 0
            f.write(f"{t},{temp:.2f},{hum:.2f},{setpoint:.2f},{alarm}\n")

    print(f"wrote {n} samples to {path}")


if __name__ == "__main__":
    main()
