#!/usr/bin/env python3
"""Plot a logged run and save it as a PNG.

    python host/plot_run.py data/sample_run.csv --out docs/telemetry.png

Temperature and humidity are drawn on two stacked axes rather than one axis
with two scales. A single pair of axes with two different units is the most
common way to make a chart lie about correlation, so it is avoided here.
"""
import argparse
import csv
import pathlib

import matplotlib
matplotlib.use("Agg")           # render to a file, no desktop window needed
import matplotlib.pyplot as plt

TEMP_COLOR = "#c2410c"
HUM_COLOR = "#1f6feb"
GRID_COLOR = "#e5e3df"
INK = "#3d3a35"
MUTED = "#8a857d"


def load(path: pathlib.Path):
    minutes, temp, hum, setpoint = [], [], [], []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                minutes.append(float(row["millis"]) / 60_000.0)
                temp.append(float(row["temperature_c"]))
                hum.append(float(row["humidity_pct"]))
                setpoint.append(float(row["setpoint_c"]))
            except (KeyError, ValueError):
                continue        # skip a partial line from an interrupted run
    if not minutes:
        raise SystemExit(f"no usable rows in {path}")
    return minutes, temp, hum, setpoint


def style(ax):
    ax.grid(True, color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID_COLOR)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="CSV file produced by log_serial.py")
    ap.add_argument("--out", default="docs/telemetry.png")
    args = ap.parse_args()

    minutes, temp, hum, setpoint = load(pathlib.Path(args.csv))

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9, 5.4), sharex=True,
        gridspec_kw={"height_ratios": [1.25, 1], "hspace": 0.22},
    )
    fig.patch.set_facecolor("#fcfcfb")

    # ---- temperature with the alarm threshold -------------------------
    ax1.plot(minutes, temp, color=TEMP_COLOR, linewidth=2)
    ax1.plot(minutes, setpoint, color=MUTED, linewidth=1.4, linestyle="--")
    ax1.fill_between(minutes, temp, setpoint,
                     where=[t > s for t, s in zip(temp, setpoint)],
                     color=TEMP_COLOR, alpha=0.12, linewidth=0)
    ax1.annotate(f"{temp[-1]:.1f} °C", (minutes[-1], temp[-1]),
                 xytext=(6, 0), textcoords="offset points",
                 color=TEMP_COLOR, fontsize=10, fontweight="bold", va="center")
    ax1.annotate(f"set point {setpoint[-1]:.1f} °C",
                 (minutes[len(minutes) // 12], setpoint[0]),
                 xytext=(0, -8), textcoords="offset points",
                 color=MUTED, fontsize=9, va="top")
    ax1.set_ylabel("Temperature (°C)", color=INK, fontsize=10)
    ax1.set_title("Sensor node telemetry", color=INK, fontsize=13,
                  fontweight="bold", loc="left", pad=12)
    style(ax1)

    # ---- humidity -----------------------------------------------------
    ax2.plot(minutes, hum, color=HUM_COLOR, linewidth=2)
    ax2.annotate(f"{hum[-1]:.1f} %", (minutes[-1], hum[-1]),
                 xytext=(6, 0), textcoords="offset points",
                 color=HUM_COLOR, fontsize=10, fontweight="bold", va="center")
    ax2.set_ylabel("Humidity (%)", color=INK, fontsize=10)
    ax2.set_xlabel("Time (minutes)", color=INK, fontsize=10)
    style(ax2)

    shaded = sum(1 for t, s in zip(temp, setpoint) if t > s)
    fig.text(0.01, 0.005,
             f"{len(minutes)} samples at 0.5 Hz  ·  "
             f"{shaded} above the set point  ·  shaded band = alarm active",
             color=MUTED, fontsize=8.5)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.085, right=0.88, top=0.9, bottom=0.12)
    fig.savefig(out, dpi=160)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
