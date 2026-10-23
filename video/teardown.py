import argparse
import json
import logging
import re
import subprocess
import sys

import numpy as np

log = logging.getLogger("teardown")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def gray_frames(path, fps, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32) / 255


def to_linear(f):
    return np.where(f <= 0.04045, f / 12.92, ((f + 0.055) / 1.055) ** 2.4)


def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path]).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    num, den = v["r_frame_rate"].split("/")
    return {"duration": float(j["format"]["duration"]), "w": v["width"], "h": v["height"], "fps": round(int(num) / int(den), 3), "vcodec": v["codec_name"], "acodec": a["codec_name"] if a else None}


def cuts(path, thr):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vf", f"scale=320:-2,select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"]).stderr
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", err)]


def stillness(path, fps=12):
    f = gray_frames(path, fps, 96, 54)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return float((d < 0.004).mean()), float(to_linear(f).mean())


def max_flashes_per_second(path, fps=30):
    y = to_linear(gray_frames(path, fps, 160, 90)).mean(axis=(1, 2))
    ext = [0] + [i for i in range(1, len(y) - 1) if (y[i] - y[i - 1]) * (y[i + 1] - y[i]) < 0] + [len(y) - 1]
    trans = [(b / fps, 1 if y[b] > y[a] else -1) for a, b in zip(ext, ext[1:]) if abs(y[b] - y[a]) >= 0.10 and min(y[a], y[b]) < 0.80]
    flashes = [trans[i][0] for i in range(1, len(trans)) if trans[i][1] != trans[i - 1][1]][::2]
    return max((sum(1 for u in flashes if t <= u < t + 1.0) for t in flashes), default=0)


def loudness(path):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    s = err[err.rfind("Summary"):]
    return (float(re.search(r"I:\s+(-?[0-9.]+) LUFS", s).group(1)), float(re.search(r"LRA:\s+(-?[0-9.]+) LU", s).group(1)),
            float(re.search(r"Peak:\s+(-?[0-9.]+|-inf) dBFS", s).group(1)))


def tempo(path):
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    oenv = librosa.onset.onset_strength(y=y, sr=sr)
    bpm, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr)
    return float(np.atleast_1d(bpm)[0]), librosa.frames_to_time(beats, sr=sr)


def on_beat_share(cut_times, beat_times, tol=0.083):
    if not cut_times or len(beat_times) == 0:
        return 0.0
    bt = np.asarray(beat_times)
    return float(np.mean([np.min(np.abs(bt - c)) <= tol for c in cut_times]))


def teardown(path, thr):
    p = probe(path)
    c = cuts(path, thr)
    still, lum = stillness(path)
    gaps = np.diff([0.0] + c + [p["duration"]])
    out = {"file": path, **p, "cuts": len(c), "cuts_per_min": round(len(c) / p["duration"] * 60, 1),
           "median_shot_s": round(float(np.median(gaps)), 2), "longest_shot_s": round(float(gaps.max()), 2),
           "first_cut_s": round(c[0] if c else p["duration"], 2), "near_still_share": round(still, 3),
           "mean_rel_luminance": round(lum, 3), "max_flashes_in_1s": max_flashes_per_second(path)}
    if p["acodec"]:
        i, lra, pk = loudness(path)
        bpm, beats = tempo(path)
        out.update({"lufs_i": i, "lra": lra, "sample_peak_dbfs": pk, "tempo_bpm": round(bpm, 1), "cuts_on_beat_share": round(on_beat_share(c, beats), 3)})
    return out


def main():
    ap = argparse.ArgumentParser(description="C7 M1 teardown: measure every video the same way.")
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--scene", type=float, default=0.3)
    ap.add_argument("--out", default="teardown/teardown.json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    rows = []
    for v in a.videos:
        try:
            r = teardown(v, a.scene)
            log.info(json.dumps(r))
            rows.append(r)
        except (subprocess.CalledProcessError, StopIteration, AttributeError) as e:
            log.error("failed on %s: %s", v, e)
            return 1
    with open(a.out, "w") as f:
        json.dump(rows, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
