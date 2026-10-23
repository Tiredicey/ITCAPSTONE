import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, lfilter

import timeline as T

SR = 48000
log = logging.getLogger("score")


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, d, s, r):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, max(a, 1)), np.linspace(1, s, max(d, 1)), np.full(sus, s), np.linspace(s, 0, max(r, 1))])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def lp(x, hz, order=2):
    return sosfilt(butter(order, min(hz, SR / 2 - 100), "low", fs=SR, output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def add(buf, sig, t0, gain=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def heart_thump(rng, strong=1.0):
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(42 + 70 * np.exp(-t * 30)) / SR) * np.exp(-t * 14)
    click = lp(rng.standard_normal(n), 1800) * np.exp(-t * 300) * 0.25
    dub_n = int(0.24 * SR)
    td = np.arange(dub_n) / SR
    dub = np.sin(2 * np.pi * np.cumsum(55 + 60 * np.exp(-td * 34)) / SR) * np.exp(-td * 18) * 0.55
    out = np.zeros(int(0.5 * SR))
    out[:n] += body + click
    k = int(0.14 * SR)
    out[k:k + dub_n] += dub
    return out * strong


def kick(rng):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(46 + 110 * np.exp(-t * 38)) / SR) * np.exp(-t * 9)
    click = hp(rng.standard_normal(n), 2500) * np.exp(-t * 400) * 0.18
    return np.tanh(1.6 * (body + click)) * 0.9


def snare(rng):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.5
    noise = bp(rng.standard_normal(n), 1500, 7000) * np.exp(-t * 22)
    return (tone + noise) * 0.55


def hat(rng, open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000, 4) * np.exp(-t * (14 if open_ else 90)) * 0.22


def fm_bell(freq, dur, index=2.2, ratio=3.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * ratio * t) * index * np.exp(-t * 6)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 5.5)


def pad_note(m, dur, bright):
    n = int(dur * SR)
    s = sum(saw(midi_hz(m) * d, n, ph) for d, ph in ((1.0, 0.0), (1.004, 0.31), (0.996, 0.67))) / 3
    return lp(s, 900 + 2600 * bright) * env_adsr(n, 0.25, 0.3, 0.8, 0.35)


def schroeder(x, mix=0.25, decay=0.82):
    wet = np.zeros_like(x)
    combs = (1557, 1617, 1491, 1422)
    for d in combs:
        a = np.zeros(d + 1)
        a[0], a[d] = 1, -decay
        wet += lfilter([1.0], a, x)
    wet /= len(combs)
    for d, g in ((225, 0.7), (556, 0.7)):
        b = np.zeros(d + 1)
        b[0], b[d] = -g, 1
        a = np.zeros(d + 1)
        a[0], a[d] = 1, -g
        wet = lfilter(b, a, wet)
    return x * (1 - mix) + wet * mix


def build(seed):
    rng = np.random.default_rng(seed)
    N = int(round(T.TOTAL * SR))
    drums, bass, pads, arps, fx = (np.zeros(N) for _ in range(5))
    duck = np.ones(N)
    cues = []
    silent0 = T.SILENT_BEAT[0] - 1e-6

    for kind, tt in T.kick_times():
        add(drums, heart_thump(rng, 0.9) if kind == "heart" else kick(rng), tt)
        cues.append({"t": round(tt, 4), "type": kind})
        i = int(tt * SR)
        j = min(N, i + int(0.22 * SR))
        duck[i:j] = np.minimum(duck[i:j], 1 - 0.55 * np.exp(-np.arange(j - i) / SR * 14))

    for bar in range(9, 22):
        for beat in (1, 3):
            tt = T.bar_time(bar, beat)
            if tt >= silent0:
                continue
            add(drums, snare(rng), tt)
            cues.append({"t": round(tt, 4), "type": "snare"})
        for s16 in range(16):
            tt = T.bar_time(bar, s16 / 4)
            if tt < silent0:
                add(drums, hat(rng, open_=(s16 % 4 == 2)), tt, 0.8 if s16 % 2 else 0.5)

    for bar in range(3, 22):
        root = T.ROOTS[T.CHORDS[bar]]
        for e in range(8):
            tt = T.bar_time(bar, e / 2)
            if tt >= silent0:
                continue
            n = int(T.BEAT / 2 * SR)
            note = root + (12 if e % 2 else 0)
            add(bass, lp(saw(midi_hz(note), n), 380 + (220 if bar >= 18 else 0)) * env_adsr(n, 0.004, 0.08, 0.6, 0.05), tt, 0.9)

    for bar in range(26):
        ch = T.CHORDS[bar]
        bright = 0.15 if bar < 3 else 0.35 if bar < 12 else 0.6 if bar < 22 else 0.9
        end = 3 * T.BEAT if bar == 21 else T.BAR + 0.4
        for m in T.CHORD_TONES[ch]:
            add(pads, pad_note(m, end, bright), T.bar_time(bar), 0.22)
        if bar >= 22:
            add(pads, pad_note(T.ROOTS[ch] + 12, end, bright), T.bar_time(bar), 0.18)

    for bar in list(range(6, 21)) + [22, 23]:
        tones = T.CHORD_TONES[T.CHORDS[bar]]
        seq = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 24]
        for s16 in range(16):
            m = seq[s16 % 4] if (s16 // 4) % 2 == 0 else seq[(3 - s16) % 4]
            add(arps, fm_bell(midi_hz(m), 0.35), T.bar_time(bar, s16 / 4), 0.10 if s16 % 4 else 0.16)

    for bar in (0, 1, 2):
        tt = T.bar_time(bar)
        add(fx, fm_bell(midi_hz(86 + bar * 3), 1.6, 1.4, 2.0), tt, 0.22)
        cues.append({"t": round(tt, 4), "type": "chime"})
    for name, a, _ in T.SECTIONS:
        cues.append({"t": round(T.bar_time(a), 4), "type": "cut", "section": name})

    wind_n = int(3 * T.BAR * SR)
    w = lp(hp(rng.standard_normal(wind_n), 300), 2400) * np.sin(np.linspace(0, np.pi, wind_n)) * 0.20
    add(fx, w, T.bar_time(3))

    r0 = T.bar_time(20)
    rn = int((T.SILENT_BEAT[0] - r0) * SR)
    noise = rng.standard_normal(rn)
    riser = np.zeros(rn)
    for k in range(64):
        a, b = k * rn // 64, (k + 1) * rn // 64
        f = 400 * (8000 / 400) ** (k / 64)
        riser[a:b] = bp(noise[a:b], f * 0.8, min(f * 1.25, 20000))
    add(fx, riser * np.linspace(0.02, 0.5, rn) ** 1.5, r0)

    it = T.bar_time(22)
    imp_n = int(2.5 * SR)
    ti = np.arange(imp_n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-ti * 20)) / SR) * np.exp(-ti * 2.2)
    boom += lp(rng.standard_normal(imp_n), 900) * np.exp(-ti * 6) * 0.4
    add(fx, np.tanh(1.4 * boom) * 0.9, it)
    cues.append({"t": round(it, 4), "type": "impact"})

    pads *= duck
    arps *= 0.5 + 0.5 * duck
    bass *= 0.35 + 0.65 * duck
    pads = schroeder(pads, 0.35, 0.84)
    arps = schroeder(lp(arps, 7500), 0.3, 0.8)
    fx = schroeder(lp(fx, 7800), 0.25, 0.8)

    low = bass + drums * 0.95
    L = low + pads * 0.9 + arps * 1.0 + fx * 0.85
    R = low + pads * 1.0 + arps * 0.8 + fx * 0.85
    tail = int(1.2 * SR)
    for ch in (L, R):
        ch[-tail:] *= np.linspace(1, 0, tail) ** 2
        ch[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    st = np.stack([L, R], 1)
    st = st / np.abs(st).max() * 0.5
    cues.sort(key=lambda c: c["t"])
    return st.astype(np.float32), cues


def main():
    ap = argparse.ArgumentParser(description="Synthesize the 140 BPM score from oscillators, FM and noise only (no samples).")
    ap.add_argument("--out", default="build/score_raw.wav")
    ap.add_argument("--cues", default="cue_sheet.json")
    ap.add_argument("--seed", type=int, default=140)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    try:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        st, cues = build(a.seed)
        wavfile.write(a.out, SR, st)
        Path(a.cues).write_text(json.dumps({"bpm": T.BPM, "sr": SR, "duration": T.TOTAL, "cues": cues}, indent=1))
        log.info("wrote %s (%.2f s) and %d cues to %s", a.out, len(st) / SR, len(cues), a.cues)
    except Exception as e:
        log.error("score build failed: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
