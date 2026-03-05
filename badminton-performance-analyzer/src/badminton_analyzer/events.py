import numpy as np

def detect_hits(shuttle_df, rallies, cfg):
    min_speed = float(cfg["hit"].get("min_speed_px_per_frame", 5.0))
    accel_th = float(cfg["hit"].get("accel_threshold", 8.0))

    frames = shuttle_df["Frame"].to_numpy()
    vis = shuttle_df["Visibility"].to_numpy()
    x = shuttle_df["X"].to_numpy()
    y = shuttle_df["Y"].to_numpy()

    valid = (vis == 1) & np.isfinite(x) & np.isfinite(y)
    x2 = np.where(valid, x, np.nan)
    y2 = np.where(valid, y, np.nan)

    events = []
    for r_idx, r in enumerate(rallies):
        s_f = r["start_frame"]
        e_f = r["end_frame"]
        m = (frames >= s_f) & (frames <= e_f) & valid
        idx = np.where(m)[0]
        if idx.size < 5:
            continue

        xs = x2[idx]
        ys = y2[idx]
        fs = frames[idx].astype(float)

        dx = np.diff(xs)
        dy = np.diff(ys)
        dt = np.diff(fs)
        dt = np.where(dt == 0, 1.0, dt)
        speed = np.sqrt((dx / dt) ** 2 + (dy / dt) ** 2)
        acc = np.abs(np.diff(speed, prepend=speed[0]))

        cand = np.where((speed >= min_speed) & (acc >= accel_th))[0]
        if cand.size == 0:
            continue

        picked = []
        last_f = -10**9
        for ci in cand:
            f = int(fs[ci])
            if f - last_f >= 6:
                picked.append(ci)
                last_f = f

        for ci in picked:
            events.append({
                "type": "hit",
                "frame": int(fs[ci]),
                "rally_index": int(r_idx),
                "x": float(xs[ci]),
                "y": float(ys[ci]),
                "speed": float(speed[ci]) if ci < speed.size else float(speed[-1])
            })

    events.sort(key=lambda e: e["frame"])
    return events
