import argparse
import hashlib
import logging
import subprocess
import sys
from pathlib import Path

import skia

import timeline as T
from core import W, H, Post
from scenes import paint

log = logging.getLogger("render")


def frame(t, post, grain=1.0):
    surf = skia.Surface(W, H)
    with surf as c:
        name = paint(c, t)
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return post.apply(arr, t, grain), name


def main():
    ap = argparse.ArgumentParser(description="Deterministic renderer: frame n is a pure function of t = n / fps.")
    ap.add_argument("--out", default="build/video_only.mp4")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--stills", nargs="*", type=float, default=None, help="write PNGs at these seconds instead of a video")
    ap.add_argument("--probe", action="store_true", help="render the same t twice and compare hashes")
    ap.add_argument("--crf", type=int, default=16)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    post = Post()
    Path("build").mkdir(exist_ok=True)
    if a.probe:
        for t in (1.3, 9.9, 30.5):
            h = [hashlib.md5(frame(t, post)[0].tobytes()).hexdigest() for _ in range(2)]
            log.info("t=%.2f %s %s", t, h[0], "IDENTICAL" if h[0] == h[1] else "DIFFERENT")
            if h[0] != h[1]:
                return 3
        return 0
    if a.stills is not None:
        from PIL import Image
        for t in a.stills:
            img, name = frame(t, post)
            p = f"build/still_{t:06.2f}.png"
            Image.fromarray(img).save(p)
            log.info("%s (%s)", p, name)
        return 0
    end = a.end if a.end is not None else int(round(T.TOTAL * T.FPS))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(T.FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(a.start, end):
            img, name = frame(n / T.FPS, post)
            proc.stdin.write(img.tobytes())
            if n % 60 == 0:
                log.info("frame %d/%d %s", n, end, name)
        proc.stdin.close()
        if proc.wait() != 0:
            log.error("ffmpeg failed")
            return 1
    except BrokenPipeError:
        log.error("ffmpeg closed the pipe")
        return 1
    log.info("wrote %s", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
