import argparse
from pathlib import Path
import sys
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from badminton_analyzer.config import load_config
from badminton_analyzer.io import read_shuttle_csv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred_csv", required=True)
    ap.add_argument("--gt_csv", required=True)
    ap.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "default.yaml"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    th = float(cfg["eval"].get("dist_threshold_px", 12.0))

    pred = read_shuttle_csv(args.pred_csv)
    gt = read_shuttle_csv(args.gt_csv)

    m = min(len(pred), len(gt))
    pred = pred.iloc[:m].reset_index(drop=True)
    gt = gt.iloc[:m].reset_index(drop=True)

    pvis = pred["Visibility"].to_numpy()
    gvis = gt["Visibility"].to_numpy()

    px = pred["X"].to_numpy()
    py = pred["Y"].to_numpy()
    gx = gt["X"].to_numpy()
    gy = gt["Y"].to_numpy()

    ok_vis = (pvis == 1) & (gvis == 1) & np.isfinite(px) & np.isfinite(py) & np.isfinite(gx) & np.isfinite(gy)
    dist = np.sqrt((px - gx) ** 2 + (py - gy) ** 2)
    hit = ok_vis & (dist <= th)

    denom = int(np.sum(gvis == 1))
    acc = float(np.sum(hit)) / denom if denom > 0 else 0.0
    mean_dist = float(np.mean(dist[ok_vis])) if np.any(ok_vis) else 0.0

    print({"frames": m, "gt_visible_frames": denom, "dist_threshold_px": th, "accuracy": acc, "mean_dist_visible": mean_dist})

if __name__ == "__main__":
    main()
