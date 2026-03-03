# tools/run_fibo_lab.py
from __future__ import annotations

import os
import argparse

from atlas.backtest.fibo_lab import scan_folder, save_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data_csv", help="Carpeta raíz donde están los CSV")
    parser.add_argument("--out", default="artifacts/fibo_lab_report.json", help="Salida del reporte")
    parser.add_argument("--pivot_left", type=int, default=3)
    parser.add_argument("--pivot_right", type=int, default=3)
    parser.add_argument("--tol", type=float, default=0.008)
    parser.add_argument("--lookahead", type=int, default=120)
    parser.add_argument("--min_rows", type=int, default=400)

    args = parser.parse_args()

    root = os.path.abspath(args.root)

    report = scan_folder(
        root_dir=root,
        pivot_left=args.pivot_left,
        pivot_right=args.pivot_right,
        tol=args.tol,
        lookahead=args.lookahead,
        min_rows=args.min_rows,
    )

    out_path = os.path.abspath(args.out)
    save_report(report, out_path)

    print("OK ->", out_path)
    print("Summary:", report.get("summary"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())