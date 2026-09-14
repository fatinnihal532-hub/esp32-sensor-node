#!/usr/bin/env python3
"""Read CSV telemetry from the sensor node and save it to a file.

The firmware prints one comma-separated line per sample. This script copies
those lines into a CSV file and echoes them to the screen so you can watch the
run happen.

Examples
--------
    python host/log_serial.py --port COM5                 # Windows
    python host/log_serial.py --port /dev/ttyUSB0         # Linux
    python host/log_serial.py --port /dev/ttyUSB0 --out data/run1.csv

Lines that start with '#' are firmware messages, not data. They are shown on
screen but kept out of the CSV file.
"""
import argparse
import datetime as dt
import pathlib
import sys

try:
    import serial  # provided by the pyserial package
except ImportError:
    sys.exit("pyserial is not installed. Run: pip install -r requirements.txt")

HEADER = "millis,temperature_c,humidity_pct,setpoint_c,alarm"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", required=True, help="serial port the board is on")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default=None, help="output CSV path")
    args = ap.parse_args()

    out_path = pathlib.Path(
        args.out or f"data/run_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Listening on {args.port} at {args.baud} baud. Ctrl+C to stop.")
    print(f"Writing to {out_path}")

    written_header = False
    rows = 0

    with serial.Serial(args.port, args.baud, timeout=2) as port, \
         out_path.open("w", encoding="utf-8", newline="") as out:
        try:
            while True:
                line = port.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                if line.startswith("#"):
                    print(line)
                    continue

                if line.startswith("millis"):
                    if not written_header:
                        out.write(HEADER + "\n")
                        written_header = True
                    continue

                if not written_header:          # board was already running
                    out.write(HEADER + "\n")
                    written_header = True

                out.write(line + "\n")
                out.flush()                     # survive an unplugged cable
                rows += 1
                print(f"[{rows:5d}] {line}")
        except KeyboardInterrupt:
            print(f"\nStopped. {rows} samples saved to {out_path}")


if __name__ == "__main__":
    main()
