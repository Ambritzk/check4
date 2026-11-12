#!/usr/bin/env python3
"""Graph reply data rate against request data rate from ping_data.csv.

usage: python3 plot_ping.py [ping_data.csv] [--log] [--no-show]
needs: pip install pandas matplotlib
"""
import argparse
import sys

import matplotlib.pyplot as plt
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default="ping_data3.csv")
    ap.add_argument("--log", action="store_true", help="log-log axes")
    ap.add_argument("--no-show", action="store_true", help="only save the PNG")
    ap.add_argument("-o", "--output", default="ping_rates.png")
    args = ap.parse_args()

    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        sys.exit(f"File not found: {args.csv}")

    df = df.dropna(subset=["req_rate_bps", "reply_rate_bps"])
    if df.empty:
        sys.exit("No usable rows in the CSV.")

    # Work in Mbit/s
    df["req"] = df["req_rate_bps"] / 1e6
    df["reply"] = df["reply_rate_bps"] / 1e6
    df = df.sort_values("req")

    # Plateau estimate: points where replies fall clearly below requests
    df["ratio"] = df["reply"] / df["req"]
    limited = df[df["ratio"] < 0.9]
    plateau = limited["reply"].median() if len(limited) >= 2 else None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Left: reply rate vs request rate
    for size, g in df.groupby("packet_size"):
        g = g.sort_values("req")
        ax1.plot(g["req"], g["reply"], marker="o", label=f"{size} B")

    top = df["req"].max()
    ax1.plot([0, top], [0, top], "k--", linewidth=1, label="y = x (no loss)")
    if plateau is not None:
        ax1.axhline(plateau, color="red", linestyle=":", linewidth=1.5,
                    label=f"plateau ≈ {plateau:.3f} Mbit/s")

    ax1.set_xlabel("Request data rate (Mbit/s)")
    ax1.set_ylabel("Reply data rate (Mbit/s)")
    ax1.set_title("Reply rate vs request rate")
    ax1.grid(True, alpha=0.3)
    ax1.legend(title="Payload size")
    if args.log:
        ax1.set_xscale("log")
        ax1.set_yscale("log")

    # Right: loss vs request rate
    if "loss_pct" in df.columns:
        for size, g in df.groupby("packet_size"):
            g = g.sort_values("req")
            ax2.plot(g["req"], g["loss_pct"], marker="o", label=f"{size} B")
        ax2.set_xlabel("Request data rate (Mbit/s)")
        ax2.set_ylabel("Packet loss (%)")
        ax2.set_title("Loss vs request rate")
        ax2.grid(True, alpha=0.3)
        ax2.legend(title="Payload size")
        if args.log:
            ax2.set_xscale("log")
    else:
        ax2.axis("off")

    fig.tight_layout()
    fig.savefig(args.output, dpi=150)
    print(f"Saved {args.output}")

    if plateau is not None:
        print(f"Estimated plateau: {plateau:.4f} Mbit/s "
              f"({plateau * 1e6:.0f} bit/s)")
    else:
        print("No clear plateau: replies tracked requests across the whole range "
              f"(max reply rate {df['reply'].max():.4f} Mbit/s). "
              "Try smaller intervals.")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()