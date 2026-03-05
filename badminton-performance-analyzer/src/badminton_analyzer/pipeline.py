from pathlib import Path
from .config import load_config
from .io import read_video_meta, read_shuttle_csv, ensure_dir, write_json, write_csv
from .rally import segment_rallies
from .events import detect_hits
from .metrics import compute_metrics
from .viz import draw_overlay_video, save_heatmap_image_plane, save_court_landing_heatmap

def run(video_path, shuttle_csv, out_dir, config_path, court_calib_path=None):
    cfg = load_config(config_path)
    out_dir = Path(out_dir)

    ensure_dir(out_dir / "tracks")
    ensure_dir(out_dir / "rallies")
    ensure_dir(out_dir / "events")
    ensure_dir(out_dir / "metrics")
    ensure_dir(out_dir / "viz")

    video_meta = read_video_meta(video_path)
    write_json(out_dir / "video.json", video_meta)

    shuttle_df = read_shuttle_csv(shuttle_csv)
    write_csv(out_dir / "tracks" / "shuttle.csv", shuttle_df)

    rallies = segment_rallies(shuttle_df, cfg)
    write_json(out_dir / "rallies" / "rallies.json", rallies)

    events = detect_hits(shuttle_df, rallies, cfg)
    write_json(out_dir / "events" / "events.json", events)

    m = compute_metrics(video_meta, rallies, events)
    write_json(out_dir / "metrics" / "metrics.json", m)

    resize_w = cfg.get("video", {}).get("resize_width", None)
    resize_h = cfg.get("video", {}).get("resize_height", None)
    resize_wh = None
    if resize_w and resize_h:
        resize_wh = (int(resize_w), int(resize_h))

    draw_overlay_video(video_path, shuttle_df, out_dir / "viz" / "overlay_raw.mp4", cfg, resize_wh=resize_wh)

    save_heatmap_image_plane(shuttle_df, out_dir / "viz" / "heatmap.png", cfg)

    save_court_landing_heatmap(shuttle_df, rallies, out_dir / "viz" / "court_landing_heatmap.png", court_calib_path, cfg)

    return str(out_dir)