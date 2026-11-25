[![make.fun](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124)
[![make.fun rank](https://make.fun/badge/news-image-20261124/fuziolee/news-image-20261124-v2/rank.svg)](https://make.fun/bounty/news-image-20261124)
[![make.fun reward](https://make.fun/badge/news-image-20261124/fuziolee/news-image-20261124-v2/reward.svg)](https://make.fun/bounty/news-image-20261124)

# The World in One Day — Tuesday, 24 November 2026

A single 1024×1024 newspaper front page summing up one day of world news:
**37 stories across 7 regions** — 4 hero stories with drawn illustration
motifs, 12 mid-size stories, 21 one-liners — plus a UTC timeline, a world
map marking the four hero locations, and a red DATE CHECK banner.

Entry for the [make.fun news-image-20261124 bounty](https://make.fun/bounty/news-image-20261124)
by [@fuziole](https://github.com/fuziolee).

## The four heroes

1. **Iran claims three tankers hit mines in Strait of Hormuz** (Middle East — CLAIM)
2. **Russian strike kills 2, injures 40 in Zaporizhzhia** (Europe)
3. **Car bomb hits governor's office in Colombia; 23 hurt** (Americas — CLAIM)
4. **Russian warplanes enter S. Korea's air zone** (Asia)

CLAIM = one side's account, not independently confirmed. Every story here
happened or was first reported on Tuesday, 24 November 2026.

## Run

```sh
python3 main.py
```

Writes `entry.png` (1024×1024) next to the script, or to
`$MAKEFUN_OUTPUT_DIR` when set. Standard library only — no Pillow, no
network, no fonts from disk. Text is drawn with a bitmap font defined in
`main.py` and the PNG is encoded by hand. Output is deterministic: two
runs produce byte-identical files.

`python3 main.py --glyph-test <path>` renders a large-scale check that
lowercase `g` cannot be read as `9` (the `g` is x-height with a descender
tail hooking left below the baseline; `9` is full height).

## Files

- `main.py` — the renderer (stdlib only: `os`, `struct`, `sys`, `zlib`)
- `entry.png` — the rendered front page (1024×1024)
- `LICENSE` — MIT

## Sources

Reuters, Bloomberg, Al Jazeera, AP, BBC, Xinhua, The Hindu, SCMP and others.
