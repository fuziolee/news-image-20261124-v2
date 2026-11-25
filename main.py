#!/usr/bin/env python3
"""News-image rescue v2 renderer: "The World in One Day - Tuesday, 24 November 2026".

Draws a dense newspaper front page (1024x1024) summing up 24 November 2026
world news: 4 hero stories with drawn illustration motifs, 12 mid-size
stories, 21 one-liners, a UTC timeline and a world map. Standard library
only: no Pillow, no network, no fonts from disk. Text is drawn with a
bitmap font defined in this file, and the PNG is encoded by hand
(zlib + struct). Output is deterministic: two runs produce byte-identical
files.

Usage:  python3 main.py
Writes entry.png to $MAKEFUN_OUTPUT_DIR (or /output, or ./entry.png).
"""

import os
import struct
import sys
import zlib

# ---------------------------------------------------------------------------
# Bitmap font: every glyph is a 5-wide x 9-tall grid ('#' = ink, '.' = blank).
# Capitals and digits occupy rows 0-6. Lowercase x-height letters occupy
# rows 2-6, ascenders rows 0-6, descenders rows 2-8 (they drop below the
# baseline, which is what keeps lowercase 'g' visibly distinct from '9':
# '9' is full height with its tail curving left inside the cap height,
# while 'g' is x-height with a tail that drops below the baseline and
# hooks LEFT along the bottom row).
# ---------------------------------------------------------------------------

_BLANK = "....."


def _c(*rows):
    """Capital / digit glyph: 7 rows given, padded with 2 blank rows."""
    return tuple(rows) + (_BLANK, _BLANK)


def _x(*rows):
    """Lowercase x-height glyph: 5 rows given, 2 blank above and below."""
    return (_BLANK, _BLANK) + tuple(rows) + (_BLANK, _BLANK)


def _a(*rows):
    """Lowercase ascender glyph: 7 rows given, padded with 2 blank rows."""
    return tuple(rows) + (_BLANK, _BLANK)


def _d(*rows):
    """Lowercase descender glyph: 7 rows given (rows 2-8), 2 blank above."""
    return (_BLANK, _BLANK) + tuple(rows)


def _r(*rows):
    """Raw glyph: all 9 rows given."""
    return tuple(rows)


FONT = {
    # --- capitals ---
    "A": _c(".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": _c("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": _c(".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": _c("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": _c("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": _c("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": _c(".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": _c("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": _c(".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": _c("..###", "....#", "....#", "....#", "....#", "#...#", ".###."),
    "K": _c("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": _c("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": _c("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": _c("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": _c(".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": _c("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": _c(".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": _c("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": _c(".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": _c("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": _c("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": _c("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": _c("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": _c("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": _c("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": _c("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    # --- digits ---
    # '9' is full height: closed bowl on top, tail down the right side
    # curving left on the LAST row of the cap height. 'g' (below) is
    # x-height with a descender - they cannot be confused.
    "0": _c(".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": _c("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": _c(".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": _c("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": _c("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": _c("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": _c(".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": _c("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": _c(".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": _c(".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
}

# --- lowercase ---
# 'g': single-story, closed upper bowl, tail down the right side that
# drops BELOW the baseline and hooks LEFT along the bottom row. Compare
# with '9' above: different height, different tail, different bowl.
FONT.update({
    "a": _x(".###.", "....#", ".####", "#...#", ".###."),
    "b": _a("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": _x(".###.", "#....", "#....", "#....", ".###."),
    "d": _a("....#", "....#", ".####", "#...#", "#...#", "#...#", ".###."),
    "e": _x(".###.", "#...#", "#####", "#....", ".###."),
    "f": _a("..##.", ".#...", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": _d(".###.", "#...#", "#...#", ".###.", "....#", "#...#", "####."),
    "h": _a("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": _a("..#..", ".....", "..#..", "..#..", "..#..", "..#..", ".###."),
    "j": _r("..#..", ".....", "...#.", "...#.", "...#.", "...#.", "...#.",
            "...#.", ".##.."),
    "k": _a("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": _a("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": _x("##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": _x("####.", "#...#", "#...#", "#...#", "#...#"),
    "o": _x(".###.", "#...#", "#...#", "#...#", ".###."),
    "p": _d("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "q": _d(".###.", "#...#", "#...#", ".###.", "....#", "....#", "....#"),
    "r": _x("#.##.", "##..#", "#....", "#....", "#...."),
    "s": _x(".####", "#....", ".###.", "....#", "####."),
    "t": _a(".#...", ".#...", "####.", ".#...", ".#...", ".#...", ".##.."),
    "u": _x("#...#", "#...#", "#...#", "#...#", ".###."),
    "v": _x("#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": _x("#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "x": _x("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": _d("#...#", "#...#", "#...#", ".###.", "..#..", "..#..", ".##.."),
    "z": _x("#####", "...#.", "..#..", ".#...", "#####"),
})

# --- punctuation and symbols ---
FONT.update({
    " ": _r(*[_BLANK] * 9),
    ".": _r(*[_BLANK] * 6, ".##..", _BLANK, _BLANK),
    ",": _r(*[_BLANK] * 5, ".##..", ".##..", ".#...", "#...."),
    ";": _r(_BLANK, _BLANK, ".##..", _BLANK, _BLANK, ".##..", ".##..",
            ".#...", "#...."),
    ":": _r(_BLANK, _BLANK, ".##..", ".##..", _BLANK, ".##..", ".##..",
            _BLANK, _BLANK),
    "!": _c("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": _c(".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": _c("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': _c(".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "(": _c("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": _c(".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "-": _c(".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "\u2013": _c(".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "\u2014": _c(".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": _c("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "%": _c("##..#", "##.#.", "..#..", ".#...", "#..##", "#..##", "....."),
    "&": _c(".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "$": _c("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": _c(".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "+": _c(".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": _c(".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": _c(".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
    "\u00b7": _r(_BLANK, _BLANK, _BLANK, ".##..", _BLANK, _BLANK, _BLANK,
                _BLANK, _BLANK),
    "\u20ac": _c(".###.", "#...#", "#....", "####.", "#....", "#...#", ".###."),
    "\u2022": _r(_BLANK, _BLANK, _BLANK, ".###.", ".###.", _BLANK, _BLANK,
                _BLANK, _BLANK),
    "\u00b0": _c(".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
    "<": _c("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": _c(".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "_": _c(".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "[": _c(".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": _c(".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "\\": _c("#....", ".#...", ".#...", "..#..", "...#.", "...#.", "....#"),
    "@": _c(".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "~": _c(".....", ".....", ".##.#", "#.#.#", ".....", ".....", "....."),
    "^": _c("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "`": _c(".#...", "..#..", ".....", ".....", ".....", ".....", "....."),
    "{": _c("..##.", ".#...", ".#...", ".##..", ".#...", ".#...", "..##."),
    "}": _c(".##..", "...#.", "...#.", "..##.", "...#.", "...#.", ".##.."),
    "|": _c("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
})

# Normalise curly quotes etc. to glyphs we have.
NORMALISE = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u00a0": " ",
}

_FALLBACK = FONT["?"]


def glyph_rows(ch):
    ch = NORMALISE.get(ch, ch)
    return FONT.get(ch, _FALLBACK)

# ---------------------------------------------------------------------------
# Canvas + PNG encoder (stdlib only)
# ---------------------------------------------------------------------------

PAPER = (247, 241, 222)
INK = (22, 19, 16)
RED = (178, 34, 34)
LIGHT_RULE = (176, 164, 138)
LAND = (122, 138, 96)
WHITE = (255, 255, 255)
SKY = (183, 205, 224)
SEA = (64, 110, 150)
DARKSEA = (38, 74, 110)

REGION_COLOURS = {
    "Europe": (37, 99, 180),
    "Middle East": (214, 110, 24),
    "Asia": (122, 63, 160),
    "Americas": (178, 34, 34),
    "Africa": (34, 139, 60),
    "Oceania": (0, 139, 139),
    "Global": (110, 110, 110),
}


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = colour

    def fill_rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = colour
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def hline(self, x, y, w, colour, thick=1):
        self.fill_rect(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.fill_rect(x, y, thick, h, colour)

    def rect_outline(self, x, y, w, h, colour, thick=1):
        self.hline(x, y, w, colour, thick)
        self.hline(x, y + h - thick, w, colour, thick)
        self.vline(x, y, h, colour, thick)
        self.vline(x + w - thick, y, h, colour, thick)

    def fill_circle(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, colour)

    def circle_outline(self, cx, cy, r, colour, thick=1):
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if abs(d - r) <= thick / 2.0 + 0.4:
                    self.set(xx, yy, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham line with square-ish thickness."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.fill_rect(x - thick // 2, y - thick // 2, thick, thick,
                           colour)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy


def _png_chunk(kind, data):
    chunk = struct.pack(">I", len(data)) + kind + data
    chunk += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return chunk


def write_png(path, canvas):
    w, h = canvas.w, canvas.h
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += canvas.px[y * w * 3:(y + 1) * w * 3]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------------------
# Text engine
# ---------------------------------------------------------------------------

def char_width(scale):
    return int(round(5 * scale))


def char_gap(scale):
    return 1 if scale <= 2 else 2


def advance(scale):
    return char_width(scale) + char_gap(scale)


def bold_px(scale):
    """Extra output pixels boldening adds to each glyph stroke."""
    return max(1, int(round(scale / 3.0)))


def text_width(s, scale, bold=False):
    w = 0
    for ch in s:
        w += advance(scale)
    if s:
        w -= char_gap(scale)
    if bold:
        w += bold_px(scale)
    return w


def line_height(scale):
    return int(round(9 * scale)) + (1 if scale <= 1 else 2)


def draw_text(cv, x, y, s, scale, colour, bold=False):
    """Draw text with its top at y. Returns the x just past the text."""
    cw = char_width(scale)
    chh = int(round(9 * scale))
    gap = char_gap(scale)
    cx = x
    for ch in s:
        rows = glyph_rows(ch)
        for fy in range(9):
            row = rows[fy]
            oy0 = y + (fy * chh) // 9
            oy1 = y + ((fy + 1) * chh) // 9
            if oy1 <= oy0:
                oy1 = oy0 + 1
            for fx in range(5):
                if row[fx] != "#":
                    continue
                ox0 = cx + (fx * cw) // 5
                ox1 = cx + ((fx + 1) * cw) // 5
                if ox1 <= ox0:
                    ox1 = ox0 + 1
                if bold:
                    ox1 += bold_px(scale)
                cv.fill_rect(ox0, oy0, ox1 - ox0, oy1 - oy0, colour)
        cx += advance(scale)
    return cx


def draw_text_centred(cv, cx, y, s, scale, colour, bold=False):
    draw_text(cv, cx - text_width(s, scale, bold) // 2, y, s, scale,
              colour, bold)


def wrap_text(s, scale, max_w, bold=False):
    """Greedy word wrap. Returns a list of lines that fit max_w."""
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, s, scale, colour, max_w, bold=False,
                 max_lines=None, lh=None):
    """Draw wrapped text, return y just below the last line."""
    if lh is None:
        lh = line_height(scale)
    lines = wrap_text(s, scale, max_w, bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        draw_text(cv, x, y + i * lh, line, scale, colour, bold)
    return y + len(lines) * lh

# ---------------------------------------------------------------------------
# The 37 stories of Tuesday, 24 November 2026.
# Region totals: Europe 9, Middle East 8, Asia 8, Americas 5, Africa 4,
# Oceania 3, Global 1 = 37 (4 heroes + 12 mid + 21 one-liners).
# CLAIM = one side's account, not independently confirmed.
# Date rule: happened or first reported 24 Nov 2026.
# ---------------------------------------------------------------------------

HEROES = [
    {
        "num": 1, "region": "Middle East", "topic": "CONFLICT", "claim": True,
        "headline": "Iran claims three tankers hit mines in Strait of Hormuz",
        "summary": "Iran's Revolutionary Guard says three \"violating\" oil "
        "tankers caught fire after striking naval mines in the strait, "
        "despite a US escort; no vessel names given and no maritime "
        "authority has confirmed it. (Reuters, 24 Nov)",
    },
    {
        "num": 2, "region": "Europe", "topic": "WAR", "claim": False,
        "headline": "Russian strike kills 2, injures 40 in Zaporizhzhia",
        "summary": "An overnight strike partly destroyed a five-storey "
        "apartment block and a house; officials said 2 people were killed "
        "and 40 injured, including four children. (Reuters, 24 Nov)",
    },
    {
        "num": 3, "region": "Americas", "topic": "CONFLICT", "claim": True,
        "headline": "Car bomb hits governor's office in Colombia; 23 hurt",
        "summary": "A car bomb exploded outside the Meta governor's office "
        "in Villavicencio, injuring 23 people; the president blamed "
        "drug-trafficking groups, but no group claimed it. "
        "(JKN / News Central TV, 24 Nov)",
    },
    {
        "num": 4, "region": "Asia", "topic": "DEFENCE", "claim": False,
        "headline": "Russian warplanes enter S. Korea's air zone",
        "summary": "Several Russian military aircraft entered South Korea's "
        "air defence identification zone near Ulleung Island; jets were "
        "scrambled. No airspace violation. (Reuters, 24 Nov)",
    },
]

# Mid-size stories: headline trimmed to fit bold scale 2 in a 157px column;
# facts and summaries unchanged from the verified v1 entry.
SMALLS = [
    ("Europe", "WAR", False,
     "Zelenskyy: Ukraine hit Russian ship Sparta II",
     "Kyiv says the strike targeted a weapons cargo; the ship was towed "
     "away. (Bloomberg, 24 Nov)"),
    ("Europe", "DIPLOMACY", False,
     "Moscow warns Estonia it is 'on verge of open war'",
     "Tallinn will shut its land border from 1 Dec; Russia summoned "
     "Estonia's envoy. (Reuters, 24 Nov)"),
    ("Europe", "SECURITY", True,
     "NATO warns Russia 'may launch nuke satellite'",
     "Russia could launch a nuclear-armed satellite within weeks, "
     "Western intel says. (Defense News)"),
    ("Middle East", "CONFLICT", False,
     "Israeli strikes kill six in Gaza",
     "Medics: a Hamas security chief and two police officers among the "
     "dead. (Reuters, 24 Nov)"),
    ("Middle East", "DIPLOMACY", False,
     "Hamas agrees to disarm in Gaza",
     "A 15-point plan agreed 30 July has factions give up weapons. "
     "(JBizNews, 24 Nov)"),
    ("Asia", "SPACE", False,
     "Shenzhou-24 crew includes first foreign astronaut",
     "Pakistan's Zeeshan Ali will be the first foreign astronaut aboard "
     "Tiangong. (Xinhua, 24 Nov)"),
    ("Asia", "POLITICS", True,
     "Ex-police chief charged with treason",
     "Listyo Sigit is accused of a wiretap plot to undermine President "
     "Prabowo. (Reuters, 24 Nov)"),
    ("Asia", "POLITICS", True,
     "Hasina: I'll return to Bangladesh on 16 December",
     "Dhaka says she can return only by extradition, \"in handcuffs\". "
     "(Reuters, 24 Nov)"),
    ("Asia", "DISASTER", False,
     "5.6 quake hits Nepal's far east, felt in 3 countries",
     "Struck Taplejung at 07:17 local; felt in India, Bhutan and "
     "Bangladesh. (The Hindu, 24 Nov)"),
    ("Africa", "POLITICS", False,
     "Arrest sought for ex-president Rajoelina",
     "Warrants sought for the ousted ex-president and a former prime "
     "minister. (Africanews, 24 Nov)"),
    ("Africa", "CONFLICT", True,
     "DR Congo plane missing; rebels claim shoot-down",
     "Kinshasa says a military plane is missing; rebels claim they shot "
     "it down. (BBC Africa, 24 Nov)"),
    ("Oceania", "CLIMATE", False,
     "Kiribati evacuates Kanton Island",
     "All 40-50 residents moved to Tarawa; return may take four years. "
     "(TVNZ / PINA, 24 Nov)"),
]

ONE_LINERS = [
    # Europe (3)
    "Visegrad leaders reject Costa's \u20ac1.58tn EU budget plan "
    "(Reuters)",
    "EU car sales up 5.4% in October; battery EVs take 23.4% share "
    "(ACEA)",
    "Pentagon yet to approve about 60 Patriot interceptors for Ukraine "
    "(Financial Times)",
    # Middle East (4)
    "Netanyahu presses Trump for renewed strikes on Iran "
    "(The Business Standard)",
    "Gulf leaders meet in Qatar to avert new US\u2013Iran strikes "
    "(Times of Middle East)",
    "Israel arrests 10 after settler attacks on Palestinians and "
    "diplomats (Times of Middle East)",
    "Thousands displaced as Israeli siege tightens on Hebron "
    "(Times of Middle East)",
    # Asia (3)
    "Kospi jumps 7.2%, Nikkei 3.9% as Nvidia CEO comeback lifts Asian "
    "tech (SCMP)",
    "Anwar: Beijing 'extremely reasonable' in South China Sea talks "
    "(SCMP)",
    "Kim Yo Jong threatens to close Switzerland's Pyongyang office "
    "(AP / KCNA)",
    # Americas (4)
    "Trump pardons turkeys Freedom and Feathers at the White House "
    "(White House)",
    "Rubio: US did not help Flavio Bolsonaro flee Brazil "
    "(Al Jazeera)",
    "Court video shows Bolsonaro damaging ankle monitor with hot iron "
    "(DPA)",
    "WHO chief Tedros visits Cuba amid health-system collapse "
    "(Al Jazeera)",
    # Africa (3)
    "60+ killed in reprisal attacks in Niger State, Nigeria "
    "(BusinessDay)",
    "DA and ActionSA strike six-party coalition deal in Nelson Mandela "
    "Bay (IOL)",
    "Joburg mayoral vote delayed as coalition talks continue "
    "(AllAfrica)",
    # Oceania (3)
    "Coalition opposes Australia\u2013Vanuatu treaty over net-zero clause "
    "(AAP)",
    "Australia seeks Solomon Islands pact as PM Wale arrives in "
    "Canberra (Bloomberg)",
    "PNG parliament begins vote on Bougainville independence "
    "ratification (The Conversation)",
    # Global (1)
    "World ran 1.46C above pre-industrial as strongest-ever El Nino "
    "looms (Beyond2C / NASA)",
]

TIMELINE = [
    ("00:48", "Russian warplanes enter South Korea's air zone; jets "
     "scrambled (Reuters)"),
    ("02:30", "Car bomb explodes outside Meta governor's office, "
     "Villavicencio (JKN)"),
    ("07:01", "60+ killed in Nigeria reprisal attacks first reported "
     "(BusinessDay)"),
    ("10:39", "Rubio: US did not help Flavio Bolsonaro flee Brazil "
     "(Al Jazeera)"),
    ("12:32", "Madagascar seeks arrest warrants for ex-president "
     "Rajoelina (Africanews)"),
    ("19:00", "Trump pardons Thanksgiving turkeys Freedom and Feathers "
     "(White House)"),
]

# Stylised world map, 56 columns x 28 rows, '#' = land. Equirectangular:
# col 0 = 180W, col 55 = 180E; row 0 = 90N, row 27 = 60S.
MAP_ROWS = [
    "........................................................",
    "........####...###.....................................",
    "...######..########..###..........##################....",
    "..###############...####..######.####################..",
    ".....###########.....#..########.####################..",
    ".....###########....#..#######..#####################..",
    ".....##########......#######....##########..#########...",
    ".....#########......#######.....#########..##########...",
    ".....#########......######..############..########..##..",
    ".....#########.......####..#########..##########..###...",
    "......########......###############..######.#####.......",
    "......####..........##############..#####..####.........",
    ".......###..........#############..#####..####..........",
    ".........##.........############...####...###...........",
    ".........######....##########.......##...####...........",
    ".........#######....#########...........######..........",
    ".........#######....########............######..........",
    ".........######......######.............######..........",
    ".........######.......####..............#######.........",
    ".........######.......###..............########.........",
    ".........#####........###..............########.........",
    ".........#####........##...............#######..#.......",
    ".........####.........##...............######....##......",
    ".........####..........................###.......#.......",
    ".........###............................................",
    ".........##.............................................",
    ".........##.............................................",
    "........................................................",
]

# Hero dot positions on the map grid (col, row): Hormuz, Zaporizhzhia,
# Villavicencio (Colombia), Ulleung Island (South Korea).
HERO_DOTS = [(37, 12), (33, 8), (17, 16), (48, 10)]

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

W = H = 1024
MX = 20            # side margin
CW = W - 2 * MX    # content width = 984
RIGHT = W - MX     # 1004


def draw_motif_tanker(cv, x, y, w, h):
    """Oil tanker on the sea, smoke from its funnel (Hormuz hero)."""
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + 24, w, h - 24, SEA)
    # Smoke puffs.
    cv.fill_circle(x + 46, y + 6, 4, INK)
    cv.fill_circle(x + 52, y + 3, 3, INK)
    # Funnel.
    cv.fill_rect(x + 42, y + 10, 8, 14, RED)
    # Hull.
    cv.fill_rect(x + 6, y + 24, 58, 10, INK)
    cv.line(x + 6, y + 24, x + 1, y + 30, INK, 2)
    cv.line(x + 64, y + 24, x + 69, y + 30, INK, 2)
    cv.fill_rect(x + 6, y + 34, 58, 2, INK)
    # Deck cargo.
    cv.fill_rect(x + 12, y + 18, 12, 6, WHITE)
    cv.fill_rect(x + 26, y + 18, 12, 6, WHITE)
    # Waves.
    for wy in (y + 40, y + 46):
        for wx in range(x + 2, x + w - 6, 8):
            cv.line(wx, wy, wx + 4, wy - 2, WHITE, 1)
            cv.line(wx + 4, wy - 2, wx + 8, wy, WHITE, 1)


def draw_motif_block(cv, x, y, w, h):
    """Damaged apartment block with a blast above it (Zaporizhzhia hero)."""
    cv.fill_rect(x, y, w, h, SKY)
    # Blast starburst.
    bx, by = x + 35, y + 10
    for dx, dy in ((-12, -4), (-8, -8), (0, -9), (8, -8), (12, -4),
                   (-12, 4), (12, 4)):
        cv.line(bx, by, bx + dx, by + dy, RED, 2)
    cv.fill_circle(bx, by, 4, RED)
    # Building.
    cv.fill_rect(x + 16, y + 18, 38, h - 18, PAPER)
    cv.rect_outline(x + 16, y + 18, 38, h - 18, INK, 1)
    # Crack down the facade.
    cv.line(x + 34, y + 18, x + 30, y + 28, INK, 1)
    cv.line(x + 30, y + 28, x + 36, y + 36, INK, 1)
    cv.line(x + 36, y + 36, x + 32, y + 44, INK, 1)
    # Windows.
    for wy in (y + 24, y + 32, y + 40):
        for wx in (x + 21, x + 42):
            cv.fill_rect(wx, wy, 6, 5, INK)


def draw_motif_car(cv, x, y, w, h):
    """Car with an explosion burst above it (Colombia hero)."""
    cv.fill_rect(x, y, w, h, SKY)
    # Explosion burst.
    bx, by = x + 35, y + 9
    for dx, dy in ((-13, -3), (-9, -8), (0, -9), (9, -8), (13, -3),
                   (-13, 5), (13, 5), (-6, 8), (6, 8)):
        cv.line(bx, by, bx + dx, by + dy, RED, 2)
    cv.fill_circle(bx, by, 5, RED)
    cv.fill_circle(bx - 8, by + 4, 2, RED)
    cv.fill_circle(bx + 9, by + 3, 2, RED)
    # Car body.
    cv.fill_rect(x + 8, y + 30, 54, 9, INK)
    cv.fill_rect(x + 20, y + 22, 28, 8, INK)
    cv.fill_rect(x + 24, y + 24, 8, 5, SKY)
    cv.fill_rect(x + 34, y + 24, 8, 5, SKY)
    # Wheels.
    cv.fill_circle(x + 18, y + 41, 5, INK)
    cv.fill_circle(x + 18, y + 41, 2, WHITE)
    cv.fill_circle(x + 52, y + 41, 5, INK)
    cv.fill_circle(x + 52, y + 41, 2, WHITE)
    # Ground line.
    cv.hline(x + 4, y + 47, w - 8, INK, 1)


def draw_motif_jets(cv, x, y, w, h):
    """Fighter jets with contrails and radar arcs (South Korea hero)."""
    cv.fill_rect(x, y, w, h, SKY)
    # Radar arcs, bottom right.
    for r in (8, 14, 20):
        cv.circle_outline(x + w - 12, y + h - 4, r, DARKSEA, 1)
    # Big jet: delta, nose to the right.
    jx, jy = x + 14, y + 16
    cv.line(jx, jy, jx + 30, jy + 6, INK, 2)
    cv.line(jx + 30, jy + 6, jx + 8, jy + 6, INK, 2)
    cv.line(jx + 8, jy + 6, jx + 2, jy + 12, INK, 2)
    cv.line(jx + 2, jy + 12, jx, jy, INK, 2)
    cv.line(jx + 12, jy + 3, jx + 16, jy + 9, INK, 1)
    # Contrail.
    cv.line(jx - 2, jy + 4, x + 2, jy + 2, WHITE, 1)
    cv.line(jx - 2, jy + 8, x + 6, jy + 8, WHITE, 1)
    # Small jet below.
    kx, ky = x + 30, y + 34
    cv.line(kx, ky, kx + 20, ky + 4, INK, 2)
    cv.line(kx + 20, ky + 4, kx + 6, ky + 4, INK, 2)
    cv.line(kx + 6, ky + 4, kx + 2, ky + 8, INK, 2)
    cv.line(kx + 2, ky + 8, kx, ky, INK, 2)
    cv.line(kx - 2, ky + 3, x + 16, ky + 1, WHITE, 1)


MOTIFS = [draw_motif_tanker, draw_motif_block, draw_motif_car,
          draw_motif_jets]


def draw_hero(cv, x, y, w, hero):
    colour = REGION_COLOURS[hero["region"]]
    # Numbered circle.
    cx, cy = x + 13, y + 13
    cv.fill_circle(cx, cy, 12, colour)
    draw_text_centred(cv, cx, cy - 7, str(hero["num"]), 1.5, WHITE, bold=True)
    # Tag line: REGION · TOPIC [+ CLAIM].
    tx = x + 32
    tag = hero["region"].upper() + " \u00b7 " + hero["topic"]
    nx = draw_text(cv, tx, y + 2, tag, 1, colour, bold=True)
    if hero["claim"]:
        draw_text(cv, nx + 6, y + 2, "\u2014 CLAIM", 1, RED, bold=True)
    # Illustration motif, top right of the card.
    mx, my, mw, mh = x + w - 78, y + 8, 70, 52
    cv.rect_outline(mx, my, mw, mh, INK, 1)
    MOTIFS[hero["num"] - 1](cv, mx + 1, my + 1, mw - 2, mh - 2)
    # Headline, bold scale 3, up to 3 lines.
    lines = wrap_text(hero["headline"], 3, w - 32 - 86, bold=True)
    if len(lines) > 3:
        print("OVERFLOW hero %d headline: %d lines" % (hero["num"], len(lines)),
              file=sys.stderr)
    hy = y + 16
    for i, line in enumerate(lines[:3]):
        draw_text(cv, tx, hy + i * line_height(3), line, 3, INK, bold=True)
    # Summary, up to 3 lines.
    sy = hy + 3 * line_height(3) + 3
    lines = wrap_text(hero["summary"], 1, w - 32)
    if len(lines) > 3:
        print("OVERFLOW hero %d summary: %d lines" % (hero["num"], len(lines)),
              file=sys.stderr)
    for i, line in enumerate(lines[:3]):
        draw_text(cv, tx, sy + i * 10, line, 1, INK)


def draw_small(cv, x, y, w, small):
    region, topic, claim, headline, summary = small
    colour = REGION_COLOURS[region]
    tag = region.upper() + " \u00b7 " + topic
    nx = draw_text(cv, x, y, tag, 1, colour, bold=True)
    if claim:
        draw_text(cv, nx + 6, y, "CLAIM", 1, RED, bold=True)
    cy = y + 12
    lines = wrap_text(headline, 2, w, bold=True)
    if len(lines) > 4:
        print("OVERFLOW small headline: %d lines: %s"
              % (len(lines), headline), file=sys.stderr)
    for i, line in enumerate(lines[:4]):
        draw_text(cv, x, cy + i * line_height(2), line, 2, INK, bold=True)
    cy += len(lines[:4]) * line_height(2) + 2
    lines = wrap_text(summary, 1, w)
    if len(lines) > 4:
        print("OVERFLOW small summary: %d lines: %s"
              % (len(lines), headline), file=sys.stderr)
    for i, line in enumerate(lines[:4]):
        draw_text(cv, x, cy + i * 9, line, 1, INK)


def draw_timeline_entry(cv, x, y, col_w, time, text):
    prefix = time + " \u2014 "
    indent = text_width(prefix, 1, bold=True)
    draw_text(cv, x, y, time, 1, RED, bold=True)
    draw_text(cv, x + text_width(time, 1, bold=True), y, " \u2014 ", 1, INK)
    lines = wrap_text(text, 1, col_w - indent)
    if len(lines) > 2:
        print("OVERFLOW timeline: %d lines: %s" % (len(lines), text),
              file=sys.stderr)
    for i, line in enumerate(lines[:2]):
        draw_text(cv, x + indent, y + i * 11, line, 1, INK)


def draw_map(cv, x, y, cell):
    for r, row in enumerate(MAP_ROWS):
        row = (row + "." * 56)[:56]
        for c, ch in enumerate(row):
            if ch == "#":
                cv.fill_rect(x + c * cell, y + r * cell, cell, cell, LAND)
    # Hero dots, numbered, in region colours.
    for hero, (gc, gr) in zip(HEROES, HERO_DOTS):
        colour = REGION_COLOURS[hero["region"]]
        cx = x + gc * cell + cell // 2
        cy = y + gr * cell + cell // 2
        cv.fill_circle(cx, cy, 8, colour)
        cv.circle_outline(cx, cy, 8, WHITE, 1)
        draw_text_centred(cv, cx, cy - 5, str(hero["num"]), 1, WHITE,
                          bold=True)


def draw_page():
    cv = Canvas(W, H, PAPER)
    cv.rect_outline(10, 10, W - 20, H - 20, INK, 2)

    # --- kicker ---
    draw_text(cv, MX, 16, "ONE DAY OF WORLD NEWS, ONE PICTURE", 1.5, INK,
              bold=True)
    right = "37 STORIES \u00b7 7 REGIONS"
    draw_text(cv, RIGHT - text_width(right, 1.5, bold=True), 16, right, 1.5,
              INK, bold=True)
    cv.hline(MX, 34, CW, INK, 2)

    # --- masthead + date line ---
    draw_text_centred(cv, W // 2, 40, "THE WORLD IN ONE DAY", 5, INK,
                      bold=True)
    draw_text_centred(cv, W // 2, 88, "Tuesday, 24 November 2026", 2, INK,
                      bold=True)
    cv.hline(MX, 110, CW, INK, 2)
    cv.hline(MX, 114, CW, INK, 1)

    # --- UTC timeline ---
    cv.fill_rect(MX, 122, 10, 10, RED)
    draw_text(cv, MX + 14, 120, "THE DAY IN UTC", 2, INK, bold=True)
    col_w = 320
    for i, (time, text) in enumerate(TIMELINE):
        col = i % 3
        row = i // 3
        draw_timeline_entry(cv, MX + col * 328, 142 + row * 22, col_w,
                            time, text)
    cv.hline(MX, 190, CW, INK, 1)

    # --- heroes: 2 x 2 ---
    hero_w, hero_h = 486, 138
    for i, hero in enumerate(HEROES):
        hx = MX + (i % 2) * (hero_w + 12)
        hy = 196 + (i // 2) * (hero_h + 8)
        draw_hero(cv, hx, hy, hero_w, hero)
    cv.vline(512, 196, 2 * hero_h + 8, LIGHT_RULE, 1)
    cv.hline(MX, 340, CW, LIGHT_RULE, 1)
    cv.hline(MX, 486, CW, INK, 1)

    # --- smalls: 2 rows x 6 ---
    small_w = 157
    for i, small in enumerate(SMALLS):
        col = i % 6
        row = i // 6
        sx = MX + col * (small_w + 8)
        sy = 492 + row * 136
        draw_small(cv, sx, sy, small_w, small)
    for col in range(1, 6):
        vx = MX + col * (small_w + 8) - 4
        cv.vline(vx, 492, 2 * 130 + 6, LIGHT_RULE, 1)
    cv.hline(MX, 624, CW, LIGHT_RULE, 1)
    cv.hline(MX, 764, CW, INK, 1)

    # --- bottom band: map + one-liners ---
    draw_text(cv, MX, 770, "WHERE IT HAPPENED", 2, INK, bold=True)
    map_x = MX + 4
    draw_map(cv, map_x, 792, 3)
    # Legend, flowed into rows inside the map column (width 240).
    lx, ly = MX + 4, 882
    for region in ["Europe", "Middle East", "Asia", "Americas", "Africa",
                   "Oceania", "Global"]:
        item_w = 12 + text_width(region, 1) + 8
        if lx + item_w > MX + 244:
            lx = MX + 4
            ly += 11
        cv.fill_rect(lx, ly + 1, 8, 8, REGION_COLOURS[region])
        draw_text(cv, lx + 12, ly, region, 1, INK)
        lx += item_w
    draw_text(cv, MX + 4, 908, "1-4 = the four hero stories", 1, INK)

    ox = 264
    draw_text(cv, ox, 770, "ALSO ON TUESDAY 24 NOVEMBER", 2, INK, bold=True)
    col_w = 240
    groups = [ONE_LINERS[0:7], ONE_LINERS[7:14], ONE_LINERS[14:21]]
    for gi, group in enumerate(groups):
        cx = ox + gi * (col_w + 10)
        cy = 792
        for item in group:
            lines = wrap_text(item, 1, col_w)
            if len(lines) > 3:
                print("OVERFLOW one-liner: %d lines: %s"
                      % (len(lines), item), file=sys.stderr)
            for i, line in enumerate(lines):
                draw_text(cv, cx, cy + i * 9, line, 1, INK)
            cy += len(lines) * 9 + 1
        if cy > 952:
            print("OVERFLOW one-liner column %d ends at y=%d" % (gi, cy),
                  file=sys.stderr)

    # --- red DATE CHECK banner ---
    cv.fill_rect(MX, 958, CW, 24, RED)
    banner = ("DATE CHECK \u2014 Every story here happened or was first "
              "reported on Tuesday, 24 November 2026.")
    draw_text_centred(cv, W // 2, 962, banner, 1.5, WHITE, bold=True)

    # --- footer ---
    draw_text_centred(
        cv, W // 2, 988,
        "Every story here happened or was first reported on 24 November "
        "2026. CLAIM = one side's account, not independently confirmed.",
        1, INK)
    draw_text_centred(
        cv, W // 2, 1000,
        "Sources: Reuters, Bloomberg, Al Jazeera, AP, BBC, Xinhua, "
        "The Hindu, SCMP and others.",
        1, INK)
    return cv


def output_path():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(outdir, exist_ok=True)
        probe = os.path.join(outdir, ".write-test")
        with open(probe, "wb") as f:
            f.write(b"")
        os.remove(probe)
        return os.path.join(outdir, "entry.png")
    except OSError:
        return os.path.join(os.getcwd(), "entry.png")


def glyph_test(path):
    """Large-scale check that lowercase 'g' cannot be read as '9'."""
    cv = Canvas(900, 330, PAPER)
    draw_text(cv, 20, 20, "g 9", 8, INK, bold=True)
    draw_text(cv, 20, 110, "grounds", 4, INK, bold=True)
    draw_text(cv, 20, 170, "Johannesburg", 4, INK, bold=True)
    draw_text(cv, 20, 230, "43.9bn", 4, INK, bold=True)
    draw_text(cv, 20, 290, "g9 g9 g9  --  9g 9g 9g", 2, INK)
    write_png(path, cv)


def main():
    assert len(HEROES) == 4, len(HEROES)
    assert len(SMALLS) == 12, len(SMALLS)
    assert len(ONE_LINERS) == 21, len(ONE_LINERS)
    assert len(TIMELINE) == 6, len(TIMELINE)
    if "--glyph-test" in sys.argv:
        path = sys.argv[sys.argv.index("--glyph-test") + 1]
        glyph_test(path)
        print("wrote %s" % path)
        return
    cv = draw_page()
    path = output_path()
    write_png(path, cv)
    print("wrote %s (%d bytes)" % (path, os.path.getsize(path)))


if __name__ == "__main__":
    main()
