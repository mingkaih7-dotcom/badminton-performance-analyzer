import argparse
from pathlib import Path
import pandas as pd

from utils.general import write_pred_video

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--traj_len", type=int, default=8)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df.columns = [c.strip() for c in df.columns]

    required = {"Frame", "X", "Y", "Visibility"}
    if not required.issubset(set(df.columns)):
        lower = {c.lower(): c for c in df.columns}
        mapped = {}
        for k in ["frame", "x", "y", "visibility"]:
            if k not in lower:
                raise ValueError(f"CSV missing column: {k}. Got columns: {list(df.columns)}")
            mapped[k] = lower[k]
        df = df[[mapped["frame"], mapped["x"], mapped["y"], mapped["visibility"]]].copy()
        df.columns = ["Frame", "X", "Y", "Visibility"]
    else:
        df = df[["Frame", "X", "Y", "Visibility"]].copy()

    df["Frame"] = df["Frame"].astype(int)
    df["X"] = pd.to_numeric(df["X"], errors="coerce").fillna(0).astype(int)
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce").fillna(0).astype(int)
    df["Visibility"] = pd.to_numeric(df["Visibility"], errors="coerce").fillna(0).astype(int)

    pred_dict = {
        "Frame": df["Frame"].tolist(),
        "X": df["X"].tolist(),
        "Y": df["Y"].tolist(),
        "Visibility": df["Visibility"].tolist(),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    used = write_pred_video(args.video, pred_dict, str(out_path), traj_len=args.traj_len)
    print(f"Saved overlay: {out_path} (codec={used})")

if __name__ == "__main__":
    main()