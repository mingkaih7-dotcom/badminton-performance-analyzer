import argparse
from pathlib import Path
import sys
import shutil
import subprocess

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from badminton_analyzer.io import read_video_meta, read_shuttle_csv, write_json, write_csv, ensure_dir
from badminton_analyzer.viz import draw_overlay_video

def _which(name):
    try:
        return shutil.which(name)
    except Exception:
        return None

def transcode_h264(in_path, out_path):
    ffmpeg = _which("ffmpeg")
    if not ffmpeg:
        return False
    cmd = [
        ffmpeg, "-y",
        "-i", str(in_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--run_dir", required=True)
    ap.add_argument("--tail", type=int, default=20)
    ap.add_argument("--copy_to_tracks", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    ensure_dir(run_dir)
    ensure_dir(run_dir / "viz")
    if args.copy_to_tracks:
        ensure_dir(run_dir / "tracks")

    meta = read_video_meta(args.video)
    write_json(run_dir / "video.json", meta)

    df = read_shuttle_csv(args.csv)
    write_csv(run_dir / "shuttle.csv", df)
    if args.copy_to_tracks:
        write_csv(run_dir / "tracks" / "shuttle.csv", df)

    cfg = {"viz": {"traj_tail": int(args.tail)}}

    raw_out = run_dir / "viz" / "overlay_raw.mp4"
    draw_overlay_video(args.video, df, raw_out, cfg, resize_wh=None)

    h264_out = run_dir / "viz" / "overlay_h264.mp4"
    ok = transcode_h264(raw_out, h264_out)
    if ok:
        try:
            shutil.copyfile(h264_out, run_dir / "overlay_h264.mp4")
        except Exception:
            pass
    else:
        try:
            shutil.copyfile(raw_out, run_dir / "overlay.mp4")
        except Exception:
            pass

    print(str(run_dir))

if __name__ == "__main__":
    main()