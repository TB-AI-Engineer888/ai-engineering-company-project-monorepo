"""
Safe snippet for basic pandas cleaning. Copy and adapt for your dataset.
Run: python pandas_clean.py  (ensure pandas is installed)

Prints shape and column names only. Row contents are not printed.
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import pandas as pd
    except ImportError:
        print("ERROR: pandas is not installed.", file=sys.stderr)
        return 1

    try:
        frame = pd.read_csv("data.csv")
    except FileNotFoundError:
        print("ERROR: data.csv was not found. Place the file next to this script and try again.", file=sys.stderr)
        return 1
    except OSError as exc:
        reason = exc.strerror or "input/output error"
        print(f"ERROR: data.csv could not be read ({reason}).", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: data.csv could not be read. Check that it is a valid CSV.", file=sys.stderr)
        return 1

    if frame.empty:
        print("ERROR: data.csv has no rows to clean.", file=sys.stderr)
        return 1

    print("df_shape", frame.shape)
    print("df_dtypes", frame.dtypes)

    frame = frame.dropna(axis=1, how="all")
    print("df_shape_after_drop_all_null_cols", frame.shape)

    frame.columns = frame.columns.str.strip().str.lower().str.replace(" ", "_")
    print("df_columns", list(frame.columns))

    before = len(frame)
    frame = frame.drop_duplicates()
    print("rows_dropped_duplicates", before - len(frame))
    print("df_shape_after_clean", frame.shape)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
