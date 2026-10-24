#!/usr/bin/env python3
"""Render a re-ordered cut, verify it, and log it.

    python3 tools/render.py --out out/LIV_1008_MAXSTYLER_B.mp4 --cut B --opening "sign" \\
        --audio raw/FILE.mov@9.5 --drop-in-clip 4.5 \\
        raw/FILE.mov@2.0-3.7 raw/FILE.mov@8.0-9.4 raw/FILE.mov@4.0-5.4 raw/FILE.mov@14.0-17.5

Segments are in clip order. Add :X to a segment of a horizontal source to set the crop's left
edge in source pixels; without it the 9:16 crop is centred. The audio is one continuous stretch
from the --audio start, as long as the segments together (CLAUDE.md section 3.2).

Refuses: banned performers or EDC in a filename, beach and club in one clip, a plain trim of one
file, and an opening shot already logged for the same file. Warns on length outside 7-15 s and
on more than 30% reuse. After rendering it checks size, length and audio, writes the first frame
and the drop frame next to the clip for you to look at, flags them if dark, re-finds the drop in
the output, then appends the row to out/used_segments.csv (skip with --no-log).
"""
import argparse, csv, datetime, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drop as dropper  # noqa: E402
import overlap  # noqa: E402

BANNED = re.compile(r"westend|biscits|dom.?dolla|\bedc\b|_edc|edc_", re.I)
DARK = 35  # mean luma (0-255) below which a frame counts as dark


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", path],
        capture_output=True, check=True, text=True).stdout
    data = json.loads(out)
    info = {"duration": float(data["format"]["duration"]), "audio": False}
    for s in data["streams"]:
        if s["codec_type"] == "video" and "width" not in info:
            num, den = s["r_frame_rate"].split("/")
            info.update(width=s["width"], height=s["height"], fps=float(num) / float(den),
                        fps_text=s["r_frame_rate"])
        if s["codec_type"] == "audio":
            info["audio"] = True
    return info


def crop_filter(info, x):
    w, h = info["width"], info["height"]
    if abs(w * 16 - h * 9) <= max(w, h) // 100:
        return ""
    if w * 16 > h * 9:
        cw = (h * 9 // 16) // 2 * 2
        x = (w - cw) // 2 if x is None else max(0, min(x, w - cw))
        return f"crop={cw}:{h}:{x}:0,"
    ch = (w * 16 // 9) // 2 * 2
    return f"crop={w}:{ch}:0:{(h - ch) // 2},"


def luma(path, t):
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
         "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = re.findall(r"YAVG=([0-9.]+)", out)
    return float(m[-1]) if m else None


def still(path, t, dest):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path,
                    "-frames:v", "1", "-vf", "scale=540:960", dest], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--cut", required=True, choices="ABCD")
    p.add_argument("--opening", required=True, help="label of the opening shot, e.g. 'sign'")
    p.add_argument("--audio", required=True, help="FILE@START")
    p.add_argument("--drop-in-clip", type=float, help="where the drop should land in the clip, s")
    p.add_argument("--no-log", action="store_true")
    p.add_argument("segments", nargs="+")
    a = p.parse_args()

    segs = [overlap.parse_segment(s) for s in a.segments]
    audio_path, _, audio_start = a.audio.rpartition("@")
    audio_start = float(audio_start)
    files = list(dict.fromkeys([s[0] for s in segs] + [audio_path]))
    names = [os.path.basename(f) for f in files]
    problems = []

    for f in files:
        if not os.path.abspath(f).startswith(os.path.abspath(os.path.join(HERE, "..", "raw"))):
            problems.append(f"{f} is not inside raw/")
        if BANNED.search(os.path.basename(f)):
            problems.append(f"{f}: filename names a banned performer or EDC")
    if len({"BEACH" in n.upper() for n in names}) > 1:
        problems.append("beach and club footage in one clip")
    if len(files) == 1:
        starts = [s[1] for s in segs]
        if len(segs) < 3 or starts == sorted(starts):
            problems.append("one file and fewer than 3 segments out of order: that is a trim")
    for row in overlap.read_log():
        if row["source_file"] == "|".join(names) and \
                row["opening_shot"].strip().lower() == a.opening.strip().lower():
            problems.append(f"opening shot '{a.opening}' already used in {row['output_file']}")
    if problems:
        sys.exit("refused:\n  " + "\n  ".join(problems))

    total = sum(e - s for _, s, e, _ in segs)
    if not 7 <= total <= 15:
        print(f"warning: clip is {total:.2f} s, the brief wants 7-15 s")
    for name, share in overlap.report(segs):
        if share > 0.30:
            print(f"warning: {share:.0%} of this footage is already in {name}")

    infos = {f: probe(f) for f in files}
    target = infos[audio_path]
    if audio_start + total > target["duration"] + 0.05:
        sys.exit(f"refused: audio runs past the end of {audio_path}")
    idx = {f: i for i, f in enumerate(files)}

    parts, labels = [], []
    for j, (f, s, e, x) in enumerate(segs):
        info = infos[f]
        fps = "" if abs(info["fps"] - target["fps"]) < 0.01 else f",fps={target['fps_text']}"
        parts.append(f"[{idx[f]}:v]trim={s}:{e},setpts=PTS-STARTPTS,{crop_filter(info, x)}"
                     f"scale=1080:1920:flags=lanczos,setsar=1{fps}[v{j}]")
        labels.append(f"[v{j}]")
    parts.append(f"{''.join(labels)}concat=n={len(segs)}:v=1:a=0,format=yuv420p[v]")
    parts.append(f"[{idx[audio_path]}:a]atrim={audio_start}:{audio_start + total:.3f},"
                 f"asetpts=PTS-STARTPTS[a]")

    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in files:
        cmd += ["-i", f]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-r", target["fps_text"],
            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", a.out]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    subprocess.run(cmd, check=True)

    out = probe(a.out)
    base = os.path.splitext(a.out)[0]
    ok = out["width"] == 1080 and out["height"] == 1920 and out["audio"] \
        and abs(out["duration"] - total) < 0.2
    print(f"{a.out}: {out['width']}x{out['height']}, {out['duration']:.2f} s, "
          f"audio {'yes' if out['audio'] else 'NO'}  -> {'ok' if ok else 'CHECK THIS'}")

    still(a.out, 0, base + "_first.jpg")
    y = luma(a.out, 0)
    print(f"first frame: {base}_first.jpg  luma {y}{'  DARK' if y is not None and y < DARK else ''}")
    if a.drop_in_clip is not None:
        still(a.out, a.drop_in_clip, base + "_drop.jpg")
        y = luma(a.out, a.drop_in_clip)
        print(f"drop frame:  {base}_drop.jpg  luma {y}"
              f"{'  DARK: shift that segment by one beat and re-render' if y is not None and y < DARK else ''}")
        found = dropper.analyze(a.out)[0].get("drop")
        hit = found is not None and abs(found - a.drop_in_clip) <= 0.15
        print(f"drop check: planned {a.drop_in_clip:.2f} s, found {found} s -> "
              f"{'on the cut' if hit else 'MISSED, check the audio start'}")

    if a.no_log:
        return
    multi = len(names) > 1
    ranges = "|".join((f"{os.path.basename(f)}@" if multi else "") + f"{s:g}-{e:g}"
                      for f, s, e, _ in segs)
    audio = (f"{os.path.basename(audio_path)}@" if multi else "") + \
        f"{audio_start:g}-{audio_start + total:g}"
    new = not os.path.exists(overlap.LOG) or os.path.getsize(overlap.LOG) == 0
    with open(overlap.LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(overlap.COLUMNS)
        w.writerow([datetime.date.today().isoformat(), os.path.basename(a.out), "|".join(names),
                    a.cut, a.opening, ranges, audio])
    print(f"logged to {os.path.relpath(overlap.LOG)}")


if __name__ == "__main__":
    main()
