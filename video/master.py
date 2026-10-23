import argparse
import json
import logging
import re
import subprocess
import sys

log = logging.getLogger("master")
JSON_RE = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.S)


def ffmpeg_json(args):
    err = subprocess.run(args, capture_output=True, text=True, check=True).stderr
    return json.loads(JSON_RE.search(err).group(0))


def main():
    ap = argparse.ArgumentParser(description="Limit, then two-pass linear loudnorm a WAV to a web loudness target.")
    ap.add_argument("--src", default="build/score_raw.wav")
    ap.add_argument("--out", default="build/score_master.wav")
    ap.add_argument("--target", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    ap.add_argument("--lra", type=float, default=11.0)
    ap.add_argument("--drive", type=float, default=8.0, help="dB of gain into the limiter")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    pre = f"volume={a.drive}dB,alimiter=limit=0.70:attack=2:release=60:level=disabled"
    base = f"loudnorm=I={a.target}:TP={a.tp}:LRA={a.lra}"
    try:
        m = ffmpeg_json(["ffmpeg", "-hide_banner", "-nostats", "-i", a.src, "-af", f"{pre},{base}:print_format=json", "-f", "null", "-"])
        log.info("pass 1: I=%s TP=%s LRA=%s", m["input_i"], m["input_tp"], m["input_lra"])
        ln = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
        r = ffmpeg_json(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", a.src, "-af", f"{pre},{ln}", "-ar", "48000", "-c:a", "pcm_s24le", a.out])
        log.info("pass 2: mode=%s output I=%s TP=%s", r["normalization_type"], r["output_i"], r["output_tp"])
        if r["normalization_type"] != "linear":
            log.error("loudnorm fell back to dynamic mode; adjust --drive")
            return 2
    except (subprocess.CalledProcessError, AttributeError, KeyError) as e:
        log.error("mastering failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
