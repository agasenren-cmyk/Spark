#!/usr/bin/env python3
"""Find the drop and the beat grid in a video's audio.

    python3 tools/drop.py raw/FILE.mov            # JSON: drop, bpm, beat grid
    python3 tools/drop.py raw/FILE.mov --series   # also print loudness every 0.1 s

Drop rule (CLAUDE.md section 2.4): the first 0.1 s window whose loudness is at least 4 dB above
the (energy) average of the previous 2 s, and stays that high for at least 2 s.
Beat grid (2.5): beat period from the spacing of loud onsets after the drop, searched in
0.40-0.55 s (109-150 BPM), then counted out from the drop. Needs only ffmpeg and Python 3.
"""
import json, math, subprocess, sys
from array import array

RATE = 16000
FRAME = RATE // 100   # 10 ms, for the beat grid
WINDOW = 10           # frames per 0.1 s window, for the drop


def frames_db(path, start=None, length=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    if length is not None:
        cmd += ["-t", str(length)]
    cmd += ["-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    pcm = array("h")
    pcm.frombytes(raw[: len(raw) - len(raw) % 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    out = []
    for i in range(0, len(pcm) - FRAME + 1, FRAME):
        s = sum(x * x for x in pcm[i : i + FRAME]) / FRAME
        out.append(10 * math.log10(s / 32768.0 ** 2) if s > 0 else -120.0)
    return out


def windows_db(frames):
    return [power_db(frames[i : i + WINDOW]) for i in range(0, len(frames) - WINDOW + 1, WINDOW)]


def power_db(dbs):
    p = sum(10 ** (d / 10) for d in dbs) / len(dbs)
    return 10 * math.log10(p) if p > 0 else -120.0


def find_drop(win, rise=4.0, before=20, hold=20, min_before=5, silence=-70.0):
    """Index of the drop window, or None. Uses up to 2 s of history (at least 0.5 s), counted
    from where the sound starts, so the silent first frames of a file are not a baseline."""
    first = next((k for k, d in enumerate(win) if d > silence), len(win))
    for i in range(first + min_before, len(win) - hold + 1):
        prev = win[max(first, i - before) : i]
        base = power_db(prev)
        if win[i] < base + rise:
            continue
        # "stays high": every half second of the next 2 s averages at least base + rise,
        # which a lone spike fails and the gaps between kicks do not
        if all(power_db(win[k : k + 5]) >= base + rise for k in range(i, i + hold, 5)):
            return i
    return None


def beat_period(onset, start, span=1600, lo=40, hi=55):
    seg = onset[start : start + span]
    if len(seg) < hi * 4:
        return None
    score = {}
    for lag in range(lo - 1, hi + 2):
        score[lag] = sum(seg[k] * seg[k + lag] for k in range(len(seg) - lag))
    best = max(range(lo, hi + 1), key=lambda l: score[l])
    a, b, c = score[best - 1], score[best], score[best + 1]
    den = a - 2 * b + c
    shift = 0.5 * (a - c) / den if den else 0.0
    return (best + max(-0.5, min(0.5, shift))) / 100.0


def snap(onset, frame, period, reach=10, beats=16):
    """Move the drop to the frame (within +-0.1 s) that best lines up with onsets on the grid."""
    def fit(f):
        return sum(onset[int(round(f + k * period * 100))]
                   for k in range(beats) if 0 <= int(round(f + k * period * 100)) < len(onset))
    return max(range(max(1, frame - reach), frame + reach + 1), key=fit)


def analyze(path):
    frames = frames_db(path)
    win = windows_db(frames)
    result = {"file": path, "duration": round(len(frames) / 100, 2)}
    i = find_drop(win)
    if i is None:
        result["drop"] = None
        result["note"] = "no window rises 4 dB over the previous 2 s and holds for 2 s"
        return result, win
    onset = [0.0] + [max(0.0, frames[k] - frames[k - 1]) for k in range(1, len(frames))]
    period = beat_period(onset, i * WINDOW)
    drop = i * WINDOW
    if period:
        drop = snap(onset, drop, period)
    result["drop"] = round(drop / 100, 2)
    result["drop_window"] = round(i / 10, 1)
    if period:
        result["beat"] = round(period, 3)
        result["bpm"] = round(60 / period, 1)
        if not 0.44 <= period <= 0.52:
            result["note"] = "beat outside 115-136 BPM; check it by ear before trusting the grid"
        d = drop / 100
        n0 = -int(d / period)
        result["grid"] = [round(d + n * period, 2)
                          for n in range(n0, int((result["duration"] - d) / period) + 1)]
    else:
        result["note"] = "less than ~2 s of audio after the drop; no beat grid"
    return result, win


def main(a):
    if not a:
        sys.exit(__doc__)
    result, win = analyze(a[0])
    if "--series" in a:
        print("\n".join(f"{k / 10:.1f} {d:.1f}" for k, d in enumerate(win)))
    grid = result.pop("grid", None)
    text = json.dumps(result, indent=1)
    if grid is not None:
        text = text[:-2] + ',\n "grid": ' + json.dumps(grid) + "\n}"
    print(text)


if __name__ == "__main__":
    main(sys.argv[1:])
