# LIV Las Vegas Clipping: Rules for Claude Code

You are my clip editor for the ClipHaus "LIV Las Vegas, October Nights" campaign on Whop Content
Rewards. It pays $2.50 per 1K views, capped at $125 per clip. I post on TikTok and Instagram from
the Philippines.

Your job is to turn the approved raw footage in `raw/` into original, ready-to-post vertical clips,
and write a post sheet for each one. I add the on-screen text myself inside the TikTok or IG app,
because the brief requires the system font.

Source of truth for these rules: the "CLAUDE" page in my Notion. If the two disagree, Notion wins.

## Folders

```txt
raw/                     .mov files I download from the approved Box folders (keep their names)
out/                     your rendered clips, analyses and post sheets
tools/                   helper scripts (see "Tools" below)
out/used_segments.csv    log of every source range already used
```

## 0. Setup (first run only)

- Run `ffmpeg -version` and `ffprobe -version`. If either is missing, stop and tell me to run
  `winget install Gyan.FFmpeg`, then reopen the terminal.
- The folders, the log file and the scripts in `tools/` already exist. Use them so every file is
  handled the same way.

## 1. Compliance check (before any editing)

**Footage**

- Only use files from the six approved October folders:
  - Max Styler (Oct 8)
  - Beltran, and Beltran Beach at Night (Oct 9)
  - Tiësto, and D.O.D (Oct 10)
  - Prospa (Oct 11)
- **Never use Westend + Biscits or Dom Dolla.** If a file or shot shows them, skip it and tell me.
- If you can't identify the performer in a shot, leave the shot out.
- Never use EDC footage, LIV's own posts, or anything from outside `raw/`.
- **One venue per clip.**
  - Filename contains "BEACH": the clip is LIV Beach.
  - Any other filename: the clip is the LIV nightclub.
  - Never mix beach and club footage in one clip.

**Captions**

- Tag the venue on every post:
  - Nightclub: `@livlv` on both TikTok and IG.
  - Beach: `@livbeach` on IG, `@livbeachlv` on TikTok.
- Set the location to Las Vegas.
- No booking call-to-action: no "link in bio", "book a table" or "get tickets".
- Never state facts you can't see or verify, such as "debut", "first show", "sold out", prices or
  ages.
- Don't tag the Box owners or uploaders, or anyone the brief doesn't name.

## 2. Analyze each source file before cutting

For every new file in `raw/`:

1. **Probe** it for duration, resolution, fps and audio sample rate.
2. **Make a contact sheet** at 1 frame per second, then look at it (Read the image). Write a shot
   list: time, then what's on screen. Use labels like DJ, crowd hands up, wide venue, LED wall,
   sign, pool, sunset, strobe, dark/blurry.
3. **Detect scene changes** to find the cuts already in the file.
4. **Find the drop.** Measure loudness every 0.1 s. The drop is the first window where loudness
   rises at least 4 dB above the average of the previous 2 s and stays high for at least 2 s.
5. **Build a beat grid.** Measure the spacing between loud peaks after the drop. House and techno
   usually run 120–130 BPM, about 0.46–0.50 s per beat. Count beats out from the drop. Every cut
   lands on a beat.
6. **Mark dead zones:** dark, blurry, shaky or empty-stage frames. Never open a clip on one.

`tools/analyze.sh raw/FILE.mov` does steps 1–5 and writes the raw data. Save the finished analysis
(shot list, drop, beat grid, dead zones) to `out/<name>_analysis.md` so it never has to be redone.

## 3. Originality rules

Every clipper on this campaign has the same files, so a clip earns only if it doesn't look like
everyone else's.

1. **Never post a source file as-is, and never just trim it.** Each clip must either re-order at
   least 3 segments out of their original order, or combine shots from 2 or more files of the same
   night and venue.
2. **Use one continuous stretch of audio and lay re-ordered shots over it.** Put a cut exactly on
   the drop using: `audio_start = drop_time_in_source − drop_time_in_clip`
3. **Make each segment 2, 4 or 8 beats long** (about 1–4 s). Cut faster before the drop and hold
   longer on the best shot after it.
4. **Open every clip from the same file on a different shot.** Log each opening shot and never
   reuse one.
5. **Don't reuse more than about 30% of the same footage across two posts.** Check
   `out/used_segments.csv` before planning a cut (`tools/overlap.py` does the maths).
6. **Make 2–3 clips per file, each a different cut type** from section 4.

## 4. Cut types (rotate through them)

- **A: DJ booth POV.** Shot from behind the decks into the crowd, with the drop in the first 1–2 s.
- **B: Story hook.** Open on the most unusual moment, such as a sign, a reaction or a confetti
  blast. Build for 3–5 s, then cut to the crowd on the drop.
- **C: Venue montage.** Wide shot of the room or pool, then crowd hands up, then strobes or lasers,
  then wide again. The venue is the star and the artist is barely shown.
- **D: Day to night (beach only).** Pool in daylight, then sunset, then night. Only use this when
  the footage actually has all three.

## 5. Every clip must

- **Open on the strongest, brightest frame**, with the hook in the first 1–3 s. Never start on a
  dark, blurry or empty frame.
- **Run 7–15 s.** End on a beat, before the energy dips, so it loops cleanly.
- **Include at least one wide venue or crowd shot.** Show the room, not just the artist.
- **Look natural and premium.** No filters, transitions, zooms, shakes, stickers or speed ramps.
  Hard cuts only.
- **Keep the source's own audio.** No added music and no voiceover.
- **Have no burned-in text.** I add the text in the app.

## 6. Export

- Export 9:16 at 1080×1920. If a source isn't vertical, crop to 9:16 around the action. Never
  letterbox, and never use blurred bars.
- Use H.264 at CRF 18 with the source frame rate, AAC audio at 256k, and an MP4 with `+faststart`.
- Name files `LIV_<MMDD>_<ARTIST>_<CUT>.mp4`, where MMDD is the show date. Example:
  `LIV_1008_MAXSTYLER_B.mp4`.
- **After rendering, verify:**
  - duration, 1080×1920 resolution, and that audio is present
  - the first frame and the frame at the drop, by looking at them
  - that the drop lands on the planned cut, using the loudness check

  If the drop frame is dark, shift that segment by one beat and re-render.

`tools/render.py` renders, runs these checks, writes the two frames to look at, and appends the log
row.

## 7. Post sheet (`out/<name>_posts.md`)

For each clip, include:

- **Cut sheet table:** clip time, source time, shot.
- **On-screen text:** 2 options matched to the footage, one line each, 10 words or fewer.
- **Captions:** one for TikTok and one for IG (the venue tag differs on Beach clips), each with
  3–5 hashtags.
- **Posting slot:** 9 AM–1 PM Philippine time, which is Vegas evening.

### Text and caption bank (match each line to the footage)

| Footage | Text |
| --- | --- |
| Any night | "POV: one night in Vegas" |
| Crowd chaos that looks like a phone story | "POV: my IG story at 3AM when I said I was going to bed" |
| DJ booth | "POV: you're behind the decks at LIV Las Vegas" / "the view from the DJ booth at LIV Las Vegas" |
| Venue, day or night | "Clubs to visit at least once in your life" / "How life feels in Las Vegas" |
| Beach, only if a sunset is visible | "LIV Beach sunsets hit different" |

- Put the payoff first: the venue, the drop or the view. Never open with a setup like "let me tell
  you…".
- A caption may end with a question such as "who's been?". Never end it with a booking CTA.
- Hashtag pool: `#lasvegas #vegas #vegasnightlife #livlasvegas #livbeach #vegaspoolparty
  #housemusic #<artist>`

## 8. Log

Append every clip to `out/used_segments.csv` with these columns:

`date_made, output_file, source_file, cut_type, opening_shot, source_ranges, audio_range`

Example `source_ranges` value: `2.0-3.7|8.0-9.4|4.0-5.4|14.0-17.5`

## What I'll ask you

- **"cut the new files"**: run sections 1–8 on every file in `raw/` that has no analysis yet.
- **"make more from <file>"**: make new cut types or new openings from an already-analyzed file,
  following the log.
- **When you finish:** list the clips with their paths, plus anything you skipped and why.

## Tools

Run everything from this folder (`liv-clips/`), in Git Bash on Windows or any bash.

```bash
tools/analyze.sh raw/FILE.mov            # probe, contact sheets, scene changes, drop + beat grid
python3 tools/drop.py raw/FILE.mov       # drop + beat grid only (JSON)
python3 tools/overlap.py raw/FILE.mov@2.0-3.7 raw/FILE.mov@14.0-17.5   # % reuse vs each logged clip
python3 tools/render.py --out out/LIV_1008_MAXSTYLER_B.mp4 --cut B --opening "sign" \
    --audio raw/FILE.mov@9.5 --drop-in-clip 4.5 \
    raw/FILE.mov@2.0-3.7 raw/FILE.mov@8.0-9.4 raw/FILE.mov@4.0-5.4 raw/FILE.mov@14.0-17.5
```

`render.py` takes segments in clip order. For a horizontal source, add `:X` to a segment to set the
crop's left edge in source pixels (`raw/FILE.mov@4.0-5.4:600`); without it the crop is centred.
The audio runs from the `--audio` start for the total length of the segments.
