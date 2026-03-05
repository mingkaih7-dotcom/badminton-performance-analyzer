from pathlib import Path
import json
import numpy as np
import cv2

def draw_overlay_video(video_path, shuttle_df, out_path, cfg, resize_wh=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tail = int(cfg.get("viz", {}).get("traj_tail", 20))
    frames = shuttle_df["Frame"].to_numpy()
    vis = shuttle_df["Visibility"].to_numpy()
    x = shuttle_df["X"].to_numpy()
    y = shuttle_df["Y"].to_numpy()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    if resize_wh is not None:
        w, h = resize_wh

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, float(fps), (w, h))

    buf = []
    fi = 0
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if resize_wh is not None:
            frame = cv2.resize(frame, resize_wh, interpolation=cv2.INTER_AREA)

        if fi < len(frames) and frames[fi] == frame_idx:
            if int(vis[fi]) == 1 and np.isfinite(x[fi]) and np.isfinite(y[fi]):
                buf.append((float(x[fi]), float(y[fi])))
            fi += 1

        if len(buf) > tail:
            buf = buf[-tail:]

        for i in range(1, len(buf)):
            p1 = (int(buf[i - 1][0]), int(buf[i - 1][1]))
            p2 = (int(buf[i][0]), int(buf[i][1]))
            cv2.line(frame, p1, p2, (0, 255, 255), 2)

        if buf:
            p = (int(buf[-1][0]), int(buf[-1][1]))
            cv2.circle(frame, p, 5, (0, 0, 255), -1)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

def _heat_acc_to_color(acc, sigma=4.0, percentile=99.0, log_scale=True):
    if sigma and sigma > 0:
        acc = cv2.GaussianBlur(acc, (0, 0), sigmaX=float(sigma), sigmaY=float(sigma))
    if log_scale:
        acc = np.log1p(acc)
    nz = acc[acc > 0]
    if nz.size == 0:
        vmax = 1.0
    else:
        vmax = float(np.percentile(nz, float(percentile)))
        if vmax <= 0:
            vmax = float(nz.max()) if nz.max() > 0 else 1.0
    norm = np.clip(acc / vmax, 0.0, 1.0)
    img = (norm * 255.0).astype(np.uint8)
    return cv2.applyColorMap(img, cv2.COLORMAP_INFERNO)

def save_heatmap_image_plane(shuttle_df, out_path, cfg=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = cfg or {}
    hcfg = cfg.get("heatmap", {})
    sigma = float(hcfg.get("sigma", 3.0))
    percentile = float(hcfg.get("percentile", 99.5))
    log_scale = bool(hcfg.get("log_scale", True))
    thickness = int(hcfg.get("thickness", 2))
    max_gap = int(hcfg.get("max_gap_frames", 2))
    max_side = int(hcfg.get("max_side", 1920))

    df = shuttle_df.copy()
    df["Frame"] = df["Frame"].astype(int)
    df["Visibility"] = df["Visibility"].astype(int)
    df = df.sort_values("Frame")
    df = df[df["Visibility"] == 1]
    df = df[np.isfinite(df["X"]) & np.isfinite(df["Y"])]

    if len(df) < 2:
        img = np.zeros((360, 640), dtype=np.uint8)
        cv2.imwrite(str(out_path), cv2.applyColorMap(img, cv2.COLORMAP_INFERNO))
        return

    xs = df["X"].to_numpy(dtype=np.float32)
    ys = df["Y"].to_numpy(dtype=np.float32)
    fs = df["Frame"].to_numpy(dtype=np.int32)

    w = max(640, int(np.nanmax(xs)) + 1)
    h = max(360, int(np.nanmax(ys)) + 1)

    scale = 1.0
    mx = max(w, h)
    if mx > max_side:
        scale = max_side / float(mx)
        w = max(1, int(round(w * scale)))
        h = max(1, int(round(h * scale)))
        xs = xs * scale
        ys = ys * scale

    acc = np.zeros((h, w), dtype=np.float32)

    prev = None
    prev_f = None
    for x, y, f in zip(xs, ys, fs):
        px = int(round(float(x)))
        py = int(round(float(y)))
        if px < 0 or px >= w or py < 0 or py >= h:
            prev = None
            prev_f = None
            continue

        cur = (px, py)

        if prev is not None and prev_f is not None and (f - prev_f) <= max_gap:
            cv2.line(acc, prev, cur, 1.0, thickness, lineType=cv2.LINE_AA)
        else:
            acc[py, px] += 1.0

        prev = cur
        prev_f = f

    color = _heat_acc_to_color(acc, sigma=sigma, percentile=percentile, log_scale=log_scale)
    cv2.imwrite(str(out_path), color)

def _load_court_calib(calib_path):
    p = Path(calib_path)
    obj = json.loads(p.read_text(encoding="utf-8"))
    W, H = obj["court_size"]
    Hm = np.array(obj["H"], dtype=np.float64)
    return (int(W), int(H), Hm)

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

def save_court_landing_heatmap(shuttle_df, rallies, out_path, court_calib_path, cfg=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not court_calib_path:
        return
    p = Path(court_calib_path)
    if not p.exists():
        return

    cfg = cfg or {}
    hcfg = cfg.get("landing_heatmap", {})
    sigma = float(hcfg.get("sigma", 5.0))
    percentile = float(hcfg.get("percentile", 99.0))
    log_scale = bool(hcfg.get("log_scale", True))
    point_radius = int(hcfg.get("point_radius", 7))
    tail_points = int(hcfg.get("tail_points", 12))

    W, H, Hm = _load_court_calib(p)
    template = _draw_court_template(W, H)
    acc = np.zeros((H, W), dtype=np.float32)

    df = shuttle_df.copy()
    df = df.sort_values("Frame")
    df = df[np.isfinite(df["X"]) & np.isfinite(df["Y"])]
    df["Frame"] = df["Frame"].astype(int)
    df["Visibility"] = df["Visibility"].astype(int)

    if not rallies:
        cv2.imwrite(str(out_path), template)
        return

    for r in rallies:
        s = int(r["start_frame"])
        e = int(r["end_frame"])
        seg = df[(df["Frame"] >= s) & (df["Frame"] <= e) & (df["Visibility"] == 1)]
        if len(seg) == 0:
            continue

        pts = seg[["X", "Y"]].to_numpy(dtype=np.float32).reshape(-1, 1, 2)
        mapped = cv2.perspectiveTransform(pts, Hm).reshape(-1, 2)

        inside = (mapped[:, 0] >= 0) & (mapped[:, 0] < W) & (mapped[:, 1] >= 0) & (mapped[:, 1] < H)

        if inside.any():
            idxs = np.where(inside)[0]
            idxs = idxs[-tail_points:] if idxs.size > tail_points else idxs
            u = float(mapped[idxs, 0].mean())
            v = float(mapped[idxs, 1].mean())
        else:
            tail = mapped[-tail_points:] if mapped.shape[0] > tail_points else mapped
            u = float(np.mean(tail[:, 0]))
            v = float(np.mean(tail[:, 1]))
            u = float(np.clip(u, 0, W - 1))
            v = float(np.clip(v, 0, H - 1))

        x = int(round(u))
        y = int(round(v))

        tmp = np.zeros((H, W), dtype=np.uint8)
        cv2.circle(tmp, (x, y), point_radius, 1, -1, lineType=cv2.LINE_AA)
        acc += tmp.astype(np.float32)

    heat = _heat_acc_to_color(acc, sigma=sigma, percentile=percentile, log_scale=log_scale)
    out = cv2.addWeighted(template, 0.55, heat, 0.45, 0.0)
    cv2.imwrite(str(out_path), out)