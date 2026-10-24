#!/usr/bin/env python3
"""How much of a planned cut reuses footage already logged in out/used_segments.csv.

    python3 tools/overlap.py raw/FILE.mov@2.0-3.7 raw/FILE.mov@8.0-9.4 raw/FILE.mov@14.0-17.5

Prints, for every logged clip that shares a source file, the share of the planned footage it
already used. CLAUDE.md section 3.5: keep it under about 30%.
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "..", "out", "used_segments.csv")
COLUMNS = ["date_made", "output_file", "source_file", "cut_type", "opening_shot",
           "source_ranges", "audio_range"]


def parse_segment(text):
    """'raw/FILE.mov@2.0-3.7[:X]' -> (path, start, end, x or None)."""
    path, _, rng = text.rpartition("@")
    if not path:
        raise ValueError(f"segment needs FILE@START-END: {text}")
    rng, _, x = rng.partition(":")
    a, _, b = rng.partition("-")
    start, end = float(a), float(b)
    if end <= start:
        raise ValueError(f"segment ends before it starts: {text}")
    return path, start, end, (int(x) if x else None)


def logged_ranges(row):
    """{source name: [(start, end), ...]} for one log row."""
    files = row["source_file"].split("|")
    out = {}
    for item in filter(None, row["source_ranges"].split("|")):
        name, sep, rng = item.rpartition("@")
        name = name if sep else files[0]
        a, _, b = rng.partition("-")
        out.setdefault(name, []).append((float(a), float(b)))
    return out


def read_log():
    if not os.path.exists(LOG):
        return []
    with open(LOG, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def shared(planned, used):
    return sum(max(0.0, min(b, d) - max(a, c)) for a, b in planned for c, d in used)


def report(segments):
    """[(output_file, share 0-1)] for logged clips that touch the same sources."""
    planned = {}
    for path, start, end, _ in segments:
        planned.setdefault(os.path.basename(path), []).append((start, end))
    total = sum(b - a for rs in planned.values() for a, b in rs)
    out = []
    for row in read_log():
        used = logged_ranges(row)
        common = sum(shared(planned[n], used[n]) for n in planned if n in used)
        if any(n in used for n in planned):
            out.append((row["output_file"], common / total if total else 0.0))
    return out


def main(a):
    if not a:
        sys.exit(__doc__)
    rows = report([parse_segment(s) for s in a])
    if not rows:
        print("no logged clip uses these files yet")
    for name, share in sorted(rows, key=lambda r: -r[1]):
        flag = "  OVER 30%" if share > 0.30 else ""
        print(f"{share:5.0%}  {name}{flag}")


if __name__ == "__main__":
    main(sys.argv[1:])
