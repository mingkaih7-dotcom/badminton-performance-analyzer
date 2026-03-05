import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import cv2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df.columns = [c.strip() for c in df.columns]
    df = df.sort_values("Frame")
    df = df[(df["Visibility"].astype(int) == 1)]
    df = df[np.isfinite(df["X"]) & np.isfinite(df["Y"])]

    obj = json.loads(Path(args.calib).read_text(encoding="utf-8"))
    W, H = obj["court_size"]
    Hm = np.array(obj["H"], dtype=np.float64)

    pts = df[["X", "Y"]].to_numpy(dtype=np.float32).reshape(-1, 1, 2)
    mapped = cv2.perspectiveTransform(pts, Hm).reshape(-1, 2)

    inside = (mapped[:,0] >= 0) & (mapped[:,0] < W) & (mapped[:,1] >= 0) & (mapped[:,1] < H)
    keep = int(inside.sum())
    total = int(mapped.shape[0])
    print({"total_visible_points": total, "mapped_inside": keep, "inside_ratio": (keep / total if total else 0.0)})
    print({"mapped_x_min": float(mapped[:,0].min()), "mapped_x_max": float(mapped[:,0].max()),
           "mapped_y_min": float(mapped[:,1].min()), "mapped_y_max": float(mapped[:,1].max())})

    img = np.zeros((H, W, 3), dtype=np.uint8)
    sample = mapped[inside]
    if sample.shape[0] > 30000:
        idx = np.random.choice(sample.shape[0], 30000, replace=False)
        sample = sample[idx]

    for u, v in sample:
        x = int(round(u))
        y = int(round(v))
        img[y, x] = (0, 0, 255)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), img)

if __name__ == "__main__":
    main()