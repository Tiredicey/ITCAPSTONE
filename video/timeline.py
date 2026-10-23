BPM = 140
BEAT = 60.0 / BPM
BAR = 4 * BEAT
FPS = 30
TOTAL = 26 * BAR
LEAD = 3 / FPS

SECTIONS = [
    ("circle", 0, 3),
    ("fall", 3, 6),
    ("array", 6, 9),
    ("bottle", 9, 12),
    ("chat", 12, 15),
    ("crew", 15, 18),
    ("climax", 18, 21),
    ("plunge", 21, 22),
    ("title", 22, 26),
]

CHORDS = {
    0: "Dm", 1: "Dm", 2: "Dm",
    3: "Dm", 4: "Bb", 5: "F", 6: "C",
    7: "Dm", 8: "Bb", 9: "F", 10: "C",
    11: "Dm", 12: "Bb", 13: "F", 14: "C",
    15: "Dm", 16: "Bb", 17: "F", 18: "Bb",
    19: "C", 20: "A", 21: "A",
    22: "Dm", 23: "Dm", 24: "Dm", 25: "Dm",
}

CHORD_TONES = {
    "Dm": (62, 65, 69), "Bb": (58, 62, 65), "F": (60, 65, 69),
    "C": (60, 64, 67), "A": (57, 61, 64),
}
ROOTS = {"Dm": 38, "Bb": 34, "F": 41, "C": 36, "A": 33}

SILENT_BEAT = (22 * BAR - BEAT, 22 * BAR)


def bar_time(bar, beat=0.0):
    return bar * BAR + beat * BEAT


def section_at(t):
    for name, a, b in SECTIONS:
        if bar_time(a) <= t < bar_time(b):
            return name, t - bar_time(a), bar_time(b) - bar_time(a)
    name, a, b = SECTIONS[-1]
    return name, t - bar_time(a), bar_time(b) - bar_time(a)


def kick_times():
    out = []
    for bar in range(0, 25):
        for beat in range(4):
            tt = bar_time(bar, beat)
            if SILENT_BEAT[0] - 1e-6 <= tt < SILENT_BEAT[1] - 1e-6:
                continue
            if bar < 3:
                out.append(("heart", tt))
                continue
            if bar >= 24 and beat > 0:
                continue
            out.append(("kick", tt))
    return out
