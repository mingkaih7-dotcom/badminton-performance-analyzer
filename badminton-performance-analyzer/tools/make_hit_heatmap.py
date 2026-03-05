import argparse
import json
from pathlib import Path
import numpy as np
import cv2

def _load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def _heat_color(acc, sigma=5.0, percentile=99.0, log_scale=True):
    if sigma and sigma > 0:
        acc = cv2.GaussianBlur(acc, (0, 0), sigmaX=float(sigma), sigmaY=float(sigma))
    if log_scale:
        acc = np.log1p(acc)
    nz = acc[acc > 0]
    vmax = 1.0 if nz.size == 0 else float(np.percentile(nz, float(percentile)))
    if vmax <= 0:
        vmax = float(nz.max()) if nz.size else 1.0
    norm = np.clip(acc / vmax, 0.0, 1.0)
    img = (norm * 255.0).astype(np.uint8)
    return cv2.applyColorMap(img, cv2.COLORMAP_INFERNO)

def _draw_court_template(W, H):
    img = np.zeros((H, W, 3), dtype=np.uint8)
    line = (255, 255, 255)

    def p(xm, ym):
        sx = W / 6.1
        sy = H / 13.4
        return (int(round(xm * sx)), int(round(ym * sy)))

    cv2.rectangle(img, p(0.0, 0.0), p(6.1, 13.4), line, 2)
    net_y = 13.4 / 2.0
    cv2.line(img, p(0.0, net_y), p(6.1, net_y), line, 2)

    singles_margin = (6.1 - 5.18) / 2.0
    cv2.line(img, p(singles_margin, 0.0), p(singles_margin, 13.4), line, 1)
    cv2.line(img, p(6.1 - singles_margin, 0.0), p(6.1 - singles_margin, 13.4), line, 1)

    short_service = 1.98
    cv2.line(img, p(0.0, net_y - short_service), p(6.1, net_y - short_service), line, 1)
    cv2.line(img, p(0.0, net_y + short_service), p(6.1, net_y + short_service), line, 1)

    doubles_long_service = 0.76
    cv2.line(img, p(0.0, 13.4 - doubles_long_service), p(6.1, 13.4 - doubles_long_service), line, 1)
    cv2.line(img, p(0.0, doubles_long_service), p(6.1, doubles_long_service), line, 1)

    center_x = 6.1 / 2.0
    cv2.line(img, p(center_x, net_y - short_service), p(center_x, doubles_long_service), line, 1)
    cv2.line(img, p(center_x, net_y + short_service), p(center_x, 13.4 - doubles_long_service), line, 1)

    return img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--court_calib", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--sigma", type=float, default=5.0)
    ap.add_argument("--percentile", type=float, default=99.0)
    ap.add_argument("--log_scale", action="store_true", default=True)
    ap.add_argument("--radius", type=int, default=6)
    ap.add_argument("--clamp_outside", action="store_true", default=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    events_path = run_dir / "events" / "events.json"
    if not events_path.exists():
        raise RuntimeError(f"Missing events: {events_path}")

    events = _load_json(events_path)
    hits = [e for e in events if isinstance(e, dict) and e.get("type") == "hit" and "x" in e and "y" in e]
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = run_dir / "viz" / "court_hit_heatmap.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.court_calib:
        calib = _load_json(Path(args.court_calib))
        W, H = calib["court_size"]
        Hm = np.array(calib["H"], dtype=np.float64)

        template = _draw_court_template(int(W), int(H))
        acc = np.zeros((int(H), int(W)), dtype=np.float32)

        if len(hits) == 0:
            cv2.imwrite(str(out_path), template)
            print(str(out_path))
            return

        pts = np.array([[float(e["x"]), float(e["y"])] for e in hits], dtype=np.float32).reshape(-1, 1, 2)
        mapped = cv2.perspectiveTransform(pts, Hm).reshape(-1, 2)

        for u, v in mapped:
            if args.clamp_outside:
                u = float(np.clip(u, 0, int(W) - 1))
                v = float(np.clip(v, 0, int(H) - 1))
            else:
                if not (0 <= u < int(W) and 0 <= v < int(H)):
                    continue
            x = int(round(u))
            y = int(round(v))
            cv2.circle(acc, (x, y), int(args.radius), 1.0, -1, lineType=cv2.LINE_AA)

        heat = _heat_color(acc, sigma=args.sigma, percentile=args.percentile, log_scale=args.log_scale)
        out = cv2.addWeighted(template, 0.55, heat, 0.45, 0.0)
        cv2.imwrite(str(out_path), out)
        print(str(out_path))
        return

    video_json = run_dir / "video.json"
    meta = _load_json(video_json) if video_json.exists() else {}
    w = int(meta.get("width", 1280))
    h = int(meta.get("height", 720))
    acc = np.zeros((h, w), dtype=np.float32)

    for e in hits:
        x = int(round(float(e["x"])))
        y = int(round(float(e["y"])))
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(acc, (x, y), int(args.radius), 1.0, -1, lineType=cv2.LINE_AA)

    heat = _heat_color(acc, sigma=args.sigma, percentile=args.percentile, log_scale=args.log_scale)
    cv2.imwrite(str(out_path), heat)
    print(str(out_path))

if __name__ == "__main__":
    main()