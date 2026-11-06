import argparse
import base64
import datetime
import html
import io
import json
import math
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tomllib
import urllib.request
import webbrowser
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ASSETS = REPO / "assets"
THEME_KEYS = (
    "board", "holes", "lilac", "paper", "ink", "scrawl_board", "scrawl_paper",
    "on_board", "dim", "loaner", "banner", "banner_edge", "edge", "shadow",
)
PREVIEW = HERE / "preview"
NUMBERS = PREVIEW / "numbers.json"


def check_colour(where, value, key):
    if key == "shadow" or (key == "edge" and value == ""):
        return
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value)):
        raise SystemExit(f"{where} is '{value}'. Colours look like #1B1C24.")


def load_settings():
    text = (HERE / "shop.toml").read_text(encoding="utf-8")
    if "<<<<<<<" in text:
        raise SystemExit("shop.toml has a clash: the same lines changed here and on GitHub. Find the <<<<<<< marks, keep the version you want, delete the marks, then run git stash drop.")
    try:
        config = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"shop.toml has a typo: {e}")
    for section in ("page", "shop", "github", "labels", "fonts", "theme", "colors", "cards"):
        if section not in config:
            raise SystemExit(f"shop.toml is missing the '{section}' section")
    for key in ("owner", "login", "discord", "avatar", "footer", "skip_in_stats"):
        if key not in config["shop"]:
            raise SystemExit(f"shop.toml is missing '{key}' in [shop]")
    for key in ("work_order", "goes_back", "get_it", "warning", "stars"):
        if key not in config["labels"]:
            raise SystemExit(f"shop.toml is missing '{key}' in [labels]")
    for key in ("typewriter", "typewriter_bold", "stencil", "handwriting"):
        if key not in config["fonts"]:
            raise SystemExit(f"shop.toml is missing '{key}' in [fonts]")
        if not (HERE / "fonts" / config["fonts"][key]).exists():
            raise SystemExit(f"font file '{config['fonts'][key]}' isn't in .profile/fonts")
    for name in ("dark", "light"):
        values = config["theme"].get(name)
        if values is None:
            raise SystemExit(f"shop.toml is missing [theme.{name}]")
        for key in THEME_KEYS:
            if key not in values:
                raise SystemExit(f"shop.toml is missing '{key}' in [theme.{name}]")
        for key, value in values.items():
            check_colour(f"theme.{name}.{key}", value, key)
    for key, value in config["colors"].items():
        check_colour(f"colors.{key}", value, key)
    if not (HERE / config["shop"]["avatar"]).exists():
        raise SystemExit(f"avatar file '{config['shop']['avatar']}' isn't in .profile")
    return config


CONFIG = load_settings()
SHOP = CONFIG["shop"]
LOGIN = SHOP["login"]
LABELS = CONFIG["labels"]

FONT_FILES = {
    "c": CONFIG["fonts"]["typewriter"],
    "b": CONFIG["fonts"]["typewriter_bold"],
    "s": CONFIG["fonts"]["stencil"],
    "r": CONFIG["fonts"]["handwriting"],
}
FONT_NAMES = {"c": "cp", "b": "cb", "s": "bs", "r": "rb"}
fonts = {k: TTFont(HERE / "fonts" / v) for k, v in FONT_FILES.items()}
widths = {k: (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm) for k, f in fonts.items()}
font_cache = {}
warnings = []


def theme_from(name, values):
    th = dict(values, name=name)
    th["edge"] = f' stroke="{values["edge"]}"' if values["edge"] else ""
    return th


THEMES = {name: theme_from(name, values) for name, values in CONFIG["theme"].items()}
COLORS = CONFIG["colors"]
BLUE_TEXT = "§brand_blue"
STEEL_DARK = "§steel_dark"
TAPE = "§tape"
TAPE_TEXT = "§label_paper"
DOOR = "§door"
AMBER = "§amber"
AMBER_SOFT = "§amber_soft"

DEFS = """
<linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="§steel_top"/><stop offset=".5" stop-color="§steel"/><stop offset="1" stop-color="§steel_bottom"/></linearGradient>
<linearGradient id="steelh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="§steel_dark"/><stop offset=".35" stop-color="§steel_shine"/><stop offset=".7" stop-color="§steel_mid"/><stop offset="1" stop-color="§steel_shade"/></linearGradient>
<radialGradient id="blade" cx=".38" cy=".3" r=".85"><stop offset="0" stop-color="§blade_shine"/><stop offset=".55" stop-color="§blade_mid"/><stop offset="1" stop-color="§blade_edge"/></radialGradient>
<pattern id="hazard" width="22" height="22" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="22" height="22" fill="§hazard_black"/><rect width="11" height="22" fill="§bright_blue"/></pattern>
<filter id="drop" x="-6%" y="-10%" width="112%" height="125%"><feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="#000" flood-opacity="SHADOW"/></filter>
<filter id="small" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="SHADOW"/></filter>
<filter id="paper" x="-6%" y="-10%" width="112%" height="125%"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="7" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 .15 0 0 0 0 .15 0 0 0 0 .2 0 0 0 .13 0" result="g"/><feComposite in="g" in2="SourceAlpha" operator="in" result="gg"/><feDropShadow in="SourceGraphic" dx="0" dy="5" stdDeviation="6" flood-color="#000" flood-opacity="SHADOW" result="s"/><feMerge><feMergeNode in="s"/><feMergeNode in="gg"/></feMerge></filter>
<filter id="brushed" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".008 .7" numOctaves="2" seed="3" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .22 0" result="g"/><feComposite in="g" in2="SourceAlpha" operator="in" result="gg"/><feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="gg"/></feMerge></filter>
<filter id="stamp" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".5" numOctaves="2" seed="11" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.2 1.9" result="m"/><feComposite in="SourceGraphic" in2="m" operator="in"/></filter>
"""


def measure(text, font, size):
    cmap, hmtx, upm = widths[font]
    total = 0
    for ch in text:
        name = cmap.get(ord(ch))
        total += hmtx[name][0] if name else upm * 0.5
    spacing = size * 0.025 * len(text) if font == "s" else 0
    return total * size / upm + spacing


def wrap(text, font, size, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if measure(trial, font, size) > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def embed_font(key, chars):
    chars = "".join(sorted(set(chars)))
    cached = font_cache.get((key, chars))
    if cached:
        return cached
    font = TTFont(HERE / "fonts" / FONT_FILES[key], recalcTimestamp=False)
    options = subset.Options()
    options.layout_features = ["kern"]
    options.hinting = False
    options.notdef_outline = True
    options.name_IDs = []
    sub = subset.Subsetter(options)
    sub.populate(text=chars)
    sub.subset(font)
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    encoded = base64.b64encode(out.getvalue()).decode()
    font_cache[(key, chars)] = encoded
    return encoded


class Card:
    def __init__(self, card_id, width, height, theme):
        self.id = card_id
        self.w = width
        self.h = height
        self.th = theme
        self.parts = []
        self.css = []
        self.chars = {}
        self.defs = []
        self.span = (0, width)
        self.alt = []
        self.baselines = []

    def add(self, svg):
        self.parts.append(svg)

    def text(self, x, y, s, font="c", size=20, fill=None, anchor="start", rot=None, limit=None, target=None):
        fill = fill or self.th["ink"]
        self.chars.setdefault(font, set()).update(s)
        w = measure(s, font, size)
        left = x if anchor == "start" else x - w / 2 if anchor == "middle" else x - w
        right = left + w
        hi = limit if limit is not None else self.w
        if right > hi + 0.5 or left < -0.5:
            warnings.append(f"{self.id}: '{s}' runs too wide by {max(right - hi, -left):.0f}px. Shorten it.")
        self.baselines.append((y, s))
        attrs = f'x="{x:g}" y="{y:g}" class="{font}" font-size="{size:g}" fill="{fill}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if rot:
            attrs += f' transform="rotate({rot:g} {x:g} {y:g})"'
        el = f"<text {attrs}>{html.escape(s, quote=False)}</text>"
        if target is not None:
            target.append(el)
        else:
            self.parts.append(el)
        return w

    def scrawl(self, x, y, s, size=34, fill=None, anchor="start", rot=None, limit=None, target=None):
        return self.text(x, y, s, "r", size, fill or self.th["scrawl_paper"], anchor, rot, limit, target)

    def paint(self, match):
        name = match.group(1)
        value = self.th.get(name, COLORS.get(name))
        if value is None:
            raise SystemExit(f"colour '{name}' is missing from shop.toml")
        return value

    def render(self):
        for y, s in self.baselines:
            if y > self.h:
                warnings.append(f"{self.id}: '{s}' falls off the bottom of the card. Too many lines for this style.")
        style = []
        for key, chars in self.chars.items():
            data = embed_font(key, chars)
            style.append(f"@font-face{{font-family:{FONT_NAMES[key]};src:url(data:font/woff2;base64,{data}) format('woff2')}}")
            extra = "stroke-width:.4px;paint-order:stroke;" if key == "r" else ""
            style.append(f".{key}{{font-family:{FONT_NAMES[key]},monospace;{extra}}}")
        style.append("text{white-space:pre}.r{stroke:currentColor}.s{letter-spacing:.025em}")
        style.extend(self.css)
        style.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        defs = DEFS.replace("SHADOW", str(self.th["shadow"])) + "".join(self.defs)
        body = "".join(self.parts)
        x0, x1 = self.span
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} 0 {x1 - x0} {self.h}" width="{x1 - x0}" height="{self.h}">'
            f"<style>{''.join(style)}</style><defs>{defs}</defs>{body}</svg>"
        )
        return re.sub(r"§(\w+)", self.paint, svg)


def screw(x, y, r=6, angle=30):
    a = math.radians(angle)
    dx, dy = math.cos(a) * r * 0.7, math.sin(a) * r * 0.7
    return (
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#blade)" stroke="#0007"/>'
        f'<line x1="{x - dx:.1f}" y1="{y - dy:.1f}" x2="{x + dx:.1f}" y2="{y + dy:.1f}" stroke="#2228" stroke-width="1.6"/>'
    )


def hook(x, y, color="§steel_dark"):
    return (
        f'<circle cx="{x}" cy="{y}" r="5" fill="§pin"/>'
        f'<path d="M{x} {y}v9a4 4 0 0 0 8 0" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
    )


def blade_path(cx, cy, outer, inner, teeth):
    points = []
    for i in range(teeth):
        a0 = 2 * math.pi * i / teeth
        a1 = 2 * math.pi * (i + 0.72) / teeth
        a2 = 2 * math.pi * (i + 1) / teeth
        points.append((cx + inner * math.cos(a0), cy + inner * math.sin(a0)))
        points.append((cx + outer * math.cos(a1), cy + outer * math.sin(a1)))
        points.append((cx + inner * math.cos(a2), cy + inner * math.sin(a2)))
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in points) + "Z"


def screwdriver(fill=None):
    if fill:
        return f'<path d="M-9 8a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v28l-5 6h-3v36l-3 6h-1l-3-6v-36h-3l-5-6z" fill="{fill}"/>'
    return (
        '<rect x="-3" y="36" width="6" height="42" fill="url(#steelh)"/><path d="M-3 78h6l-2 7h-2z" fill="§blade_edge"/>'
        '<path d="M-9 8a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v28l-5 6h-8l-5-6z" fill="§brand_blue"/>'
        '<path d="M-4 9v26M0 9v26M4 9v26" stroke="§handle_ridge" stroke-width="1.5"/>'
    )


def roller(fill=None):
    if fill:
        return '<path d="M-30 6h60v22h-60zM30 17h7v22h-34v12h-6v-18h34v-10h-1zM-6 51h12v34h-12z" fill="%s"/>' % fill
    return (
        '<path d="M30 17h5v20h-35v14" fill="none" stroke="§steel_dark" stroke-width="3.5"/>'
        '<rect x="-30" y="6" width="60" height="22" rx="4" fill="§roller"/><rect x="-30" y="20" width="60" height="8" rx="3" fill="§roller_shade"/>'
        '<rect x="-6" y="51" width="12" height="34" rx="4" fill="§handle_dark"/>'
    )


def hammer(fill=None):
    if fill:
        return f'<path d="M-30 6h40l18 4-6 10-12-2h-40zM-5 20h10v64h-10z" fill="{fill}"/>'
    return (
        '<rect x="-5" y="20" width="10" height="64" rx="3" fill="§handle_dark"/>'
        '<path d="M-30 6h40l18 4-6 10-12-2h-40z" fill="url(#steel)"/><rect x="-33" y="6" width="5" height="12" rx="1" fill="§blade_edge"/>'
    )


def wrench(fill):
    return (
        f'<path d="M-15 4l6 13h18l6-13a22 22 0 0 1 1 30l-5 5v42a7 7 0 0 1-22 0v-42l-5-5a22 22 0 0 1 1-30z" fill="{fill}"/>'
    )


def hero(th, d, o):
    c = Card(o["_id"], 840, 400, th)
    c.span = (-2, 842)
    panel = [f'<path d="M6 6H834V394H6Z" fill="{th["board"]}" filter="url(#drop)"/>']
    c.defs.append('<clipPath id="pan"><path d="M6 6H834V394H6Z"/></clipPath>')
    holes = []
    cx, cy = 150, 165
    for ix in range(0, 31):
        for iy in range(0, 15):
            x, y = 20 + ix * 28, 18 + iy * 28
            dist = math.hypot(x - cx, y - cy)
            if dist < 142:
                continue
            if 275 < x < 640 or (x > 610 and y > 320) or (y > 305 and x < 275):
                continue
            holes.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{th["holes"]}"/>')
    panel.append('<g clip-path="url(#pan)">' + "".join(holes) + "</g>")
    panel.extend(screw(x, y) for x, y in [(22, 22), (818, 22), (22, 378), (818, 378)])
    c.add('<g class="on">' + "".join(panel) + "</g>")
    c.css.append(".on{animation:on .8s linear 1}@keyframes on{0%{opacity:.55}30%{opacity:.8}45%{opacity:.62}100%{opacity:1}}")

    c.add(f'<circle cx="{cx}" cy="30" r="5" fill="§pin"/>')
    c.defs.append(f'<clipPath id="face"><circle cx="{cx}" cy="{cy}" r="100"/></clipPath>')
    blade = [
        f'<path d="M{cx} 30V44" stroke="§steel_dark" stroke-width="2.5"/>',
        f'<path d="{blade_path(cx, cy, 130, 116, 40)}" fill="url(#blade)" filter="url(#small)"/>',
        f'<circle cx="{cx}" cy="{cy}" r="107" fill="none" stroke="§blade_edge" stroke-width="1.5"/>',
        f'<circle cx="{cx}" cy="{cy}" r="103" fill="§face_ring"/>',
        f'<circle cx="{cx}" cy="{cy}" r="100" fill="§pale"/>',
        f'<image href="{d["_avatar"]}" x="{cx - 100}" y="{cy - 100}" width="200" height="200" clip-path="url(#face)"/>',
    ]
    c.add(f'<g transform="rotate(4 {cx} 30)">' + "".join(blade) + "</g>")

    c.add(f'<rect x="34" y="322" width="232" height="44" rx="4" fill="{BLUE_TEXT}" filter="url(#small)"/>')
    c.add(screw(46, 344, 4) + screw(254, 344, 4))
    c.text(150, 351, o["badge"], "b", 20, "§white", "middle", limit=266)

    c.text(290, 132, o["name"], "s", 130, th["on_board"], limit=650)
    c.text(292, 180, o["aka"], "c", 20, th["dim"], limit=650)
    c.text(292, 222, o["lead"], "b", 20, th["on_board"], limit=650)
    c.text(292, 250, o["sub"], "c", 20, th["on_board"], limit=650)

    lines = o["tape"]
    slot = 100 / len(lines)
    tape = []
    for i, line in enumerate(lines):
        w = measure(line, "b", 20) + 28
        c.defs.append(f'<clipPath id="t{i}"><rect class="tr{i}" x="290" y="292" width="{w:.0f}" height="44"/></clipPath>')
        tape.append(
            f'<g class="tl{i}" clip-path="url(#t{i})"><path d="M290 298H{290 + w:.0f}l-5 18 5 18H290Z" fill="{TAPE}"/>'
        )
        c.text(304, 323, line, "b", 20, TAPE_TEXT, limit=815, target=tape)
        tape.append("</g>")
        a = i * slot
        typed = a + slot * 0.32
        cut = a + slot * 0.92
        c.css.append(
            f".tl{i}{{opacity:{1 if i == 0 else 0};animation:tl{i} 24s linear -2s infinite}}"
            f"@keyframes tl{i}{{0%,{max(a - 0.01, 0):.2f}%{{opacity:0}}{a:.2f}%,{cut:.2f}%{{opacity:1}}{cut + 0.01:.2f}%,100%{{opacity:0}}}}"
            f".tr{i}{{animation:tr{i} 24s steps({len(line) + 2}) -2s infinite}}"
            f"@keyframes tr{i}{{0%,{a:.2f}%{{transform:translateX(-{w:.0f}px)}}{typed:.2f}%,100%{{transform:none}}}}"
        )
    c.add("".join(tape))

    if len(o["wall"]) > 4:
        warnings.append(f'{o["_id"]}: the tool wall holds 4, and you have {len(o["wall"])}.')
    tools = {"hammer": hammer, "screwdriver": screwdriver, "roller": roller, "wrench": None}
    spots = [(695, 30), (785, 30), (695, 172), (785, 172)]
    for (x, y), (label, tool_name) in zip(spots, o["wall"]):
        if tool_name not in tools:
            raise SystemExit(f'{o["_id"]}: tool "{tool_name}" doesn\'t exist. Choose from: {", ".join(tools)}')
        tool = tools[tool_name]
        c.add(f'<circle cx="{x}" cy="{y - 8}" r="4.5" fill="§pin"/>')
        if tool:
            c.add(f'<path d="M{x} {y - 8}v14" stroke="§steel_dark" stroke-width="3" stroke-linecap="round"/>')
            c.add(f'<g transform="translate({x} {y})" filter="url(#small)">{tool()}</g>')
        else:
            c.add(f'<g transform="translate({x} {y})">{wrench(th["lilac"])}</g>')
        plate = measure(label, "b", 15) + 12
        c.add(f'<rect x="{x - plate / 2:.1f}" y="{y + 92}" width="{plate:.1f}" height="23" rx="2" fill="{th["banner"]}"/>')
        c.text(x, y + 108, label, "b", 15, TAPE_TEXT, "middle")
    c.scrawl(818, 360, o["corner_note"], 28, th["scrawl_board"], "end", limit=822)
    late = o["late_note"][th["name"]]
    c.scrawl(290, 380, late, 36, th["scrawl_board"], limit=818 - measure(o["corner_note"], "r", 28) - 4)
    hung = [label for label, tool_name in o["wall"] if tool_name != "wrench"]
    gone = " The wrench is missing." if len(hung) < len(o["wall"]) else ""
    c.alt = [
        o["name"], o["aka"], f'{o["lead"]} {o["sub"]}', o["badge"],
        "Label tape: " + " ".join(lines), f'Tool wall: {", ".join(hung)}.{gone}', o["corner_note"], late,
    ]
    return c


def rules(th, d, o):
    c = Card(o["_id"], 840, 246, th)
    c.span = (14, 826)
    plate = "M34 22H806a12 12 0 0 1 12 12V192a12 12 0 0 1-12 12H34a12 12 0 0 1-12-12V34A12 12 0 0 1 34 22Z"
    inner = [f'<path d="{plate}" fill="{BLUE_TEXT}" filter="url(#drop)"/>']
    inner.append(f'<path d="{plate}" fill="none" stroke="§white" stroke-opacity=".55" stroke-width="2.5" transform="translate(420 113) scale(.975 .93) translate(-420 -113)"/>')
    inner.append(screw(38, 38, 5, 20) + screw(802, 38, 5, 70) + screw(38, 188, 5, 60) + screw(802, 188, 5, 40))
    c.parts.append('<g>' + "".join(inner))
    c.text(52, 104, o["title"][0], "s", 58, "§white", limit=228)
    c.text(52, 160, o["title"][1], "s", 58, "§white", limit=228)
    if len(o["rows"]) > 2:
        warnings.append(f'{o["_id"]}: holds 2 rules plus the scrawled one, and you have {len(o["rows"])}.')
    if any(len(row) > 2 for row in o["rows"]):
        warnings.append(f'{o["_id"]}: each rule holds 2 lines.')
    y = 62
    for row in o["rows"]:
        for part in row:
            c.text(236, y, part, "b", 22, "§white", limit=800)
            y += 27
        y += 9
    c.add("</g>")
    c.add('<g transform="rotate(-1 560 200)"><path d="M300 176H806l-6 10 6 10-6 10 6 10H300l5-10-5-10 5-10z" fill="§pale" filter="url(#small)"/></g>')
    c.scrawl(324, 208, o["scrawl"], 36, "§pencil", rot=-1, limit=800)
    c.alt = [" ".join(o["title"])] + [" ".join(row) for row in o["rows"]] + [o["scrawl"]]
    return c


def key_shape(x, y):
    return (
        f'<g transform="translate({x} {y})" filter="url(#small)">'
        '<path fill-rule="evenodd" d="M-24 24a24 24 0 1 1 48 0a24 24 0 1 1-48 0zM-7 10a7 7 0 1 0 14 0a7 7 0 1 0-14 0z" fill="url(#blade)"/>'
        '<path d="M-5 46h10v76h-5v-6h-11v-8h11v-5h-8v-8h8v-49z" fill="url(#steelh)" stroke="§blade_edge" stroke-width=".7"/>'
        "</g>"
    )


def fob(c, th, small, big):
    c.add(f'<path d="M130 34V66" stroke="{STEEL_DARK}" stroke-width="2.4"/>')
    c.add(f'<rect x="14" y="64" width="232" height="118" rx="50" fill="{th["paper"]}" filter="url(#paper)"/>')
    c.add(f'<rect x="14" y="64" width="232" height="118" rx="50" fill="{th["paper"]}"{th["edge"]}/>')
    c.add(f'<rect x="22" y="72" width="216" height="102" rx="43" fill="none" stroke="{th["ink"]}" stroke-width="1.5" opacity=".5"/>')
    c.add(f'<circle cx="130" cy="72" r="4" fill="{th["ink"]}"/>')
    c.text(130, 112, small, "c", 20, th["ink"], "middle")
    c.text(130, 154, big, "s", 37, th["ink"], "middle", limit=232)


def rail(c, th):
    c.add(f'<rect x="4" y="10" width="400" height="20" rx="3" fill="url(#steel)" filter="url(#small)"/>')
    c.add(screw(18, 20, 5) + screw(390, 20, 5))


def shelf_label(th, d, o):
    c = Card(o["_id"], 840, 62, th)
    c.span = (4, 836)
    words = o["words"]
    w = measure(words, "s", 30) + 44
    c.add(f'<path d="M12 10H{12 + w:.0f}l-8 19 8 19H12Z" fill="{th["banner"]}" stroke="{th["banner_edge"]}" filter="url(#small)"/>')
    c.text(32, 40, words, "s", 30, TAPE_TEXT)
    c.alt = [f"{words}."]
    return c


def key(th, d, o):
    c = Card(o["_id"], 408, 244, th)
    c.span = (-4, 412)
    rail(c, th)
    c.add(hook(130, 24))
    c.add(hook(330, 24))
    c.add(key_shape(330, 38))
    fob(c, th, o["small"], o["big"])
    c.scrawl(16, 228, o["scrawl"], 36, th["scrawl_board"], limit=404)
    c.alt = [f'{o["small"]}: {o["big"]}. {o["scrawl"]}']
    return c


def manual(th, d, o):
    c = Card(o["_id"], 840, 640, th)
    c.span = (26, 830)
    scrawl = "§pencil"
    slot = len(c.parts)
    c.parts.append("")
    c.text(74, 64, o["title"], "s", 52, TAPE_TEXT)
    c.text(74, 110, o["model"], "c", 20, limit=818)

    def tick(x, y, on):
        c.add(f'<rect x="{x}" y="{y - 15}" width="17" height="17" fill="none" stroke="{th["ink"]}" stroke-width="1.6"/>')
        if on:
            c.add(f'<path d="M{x + 3} {y - 7}l4 5 8-13" fill="none" stroke="{BLUE_TEXT}" stroke-width="3" stroke-linecap="round"/>')

    def tick_label(x, y, on, label):
        tick(x, y, on)
        c.text(x + 25, y, label, "c", 20)
        return x + 25 + measure(label, "c", 20) + 24

    x = 74
    c.text(x, 140, o["question"], "b", 20)
    x += measure(o["question"], "b", 20) + 18
    for label, on in o["answers"]:
        x = tick_label(x, 140, on, label)

    c.add(f'<path d="M74 156H800" stroke="{th["ink"]}" stroke-opacity=".35"/>')
    c.text(74, 186, o["unit_title"], "b", 20)
    y = 214
    for line in wrap(o["unit_text"], "c", 20, 470):
        c.text(74, y, line, "c", 20, limit=550)
        y += 27
    for i, line in enumerate(o["unit_notes"]):
        c.scrawl(568, 226 + i * 32, line, 34, scrawl, rot=-3, limit=806)

    y += 8
    c.text(74, y, o["tools_title"], "b", 20)
    y += 28
    c.text(74, y, o["tools_intro"], "c", 20)
    y += 28
    for row in o["tools"]:
        x = 74
        for label, on in row:
            x = tick_label(x, y, on, label)
        y += 28
    c.text(74, y, o["tools_outro"], "c", 20)
    for i, line in enumerate(o["tools_notes"]):
        c.scrawl(568, y - 72 + i * 32, line, 34, scrawl, rot=-2, limit=806)

    y += 22
    c.add(f'<path d="M74 {y}H800" stroke="{th["ink"]}" stroke-opacity=".35"/>')
    y += 30
    c.text(74, y, o["issues_title"], "b", 20)
    y += 10
    c.add(f'<rect x="74" y="{y}" width="726" height="30" fill="{th["ink"]}"/>')
    c.text(86, y + 22, o["issues_head"][0], "b", 20, TAPE_TEXT)
    c.text(520, y + 22, o["issues_head"][1], "b", 20, TAPE_TEXT)
    y += 30
    for issue, status in o["issues"]:
        c.text(86, y + 22, issue, "c", 20, limit=510)
        c.text(520, y + 22, status, "b", 20, BLUE_TEXT, limit=800)
        y += 31
        c.add(f'<path d="M74 {y}H800" stroke="{th["ink"]}" stroke-opacity=".3"/>')
    bottom = y + 22
    page = f"M34 14H816a6 6 0 0 1 6 6V{bottom - 6}a6 6 0 0 1-6 6H34Z"
    teeth = (bottom - 14) // 9
    tear = "M34 14" + "".join(f"l{-4 if i % 2 else 4} 9" for i in range(teeth)) + f"L34 {bottom}"
    body = [f'<path d="{page}" fill="{th["paper"]}" filter="url(#paper)"/><path d="{page}" fill="{th["paper"]}"{th["edge"]}/>']
    body.append(f'<path d="{tear}" fill="none" stroke="#0003" stroke-width="1.2"/>')
    body.append(f'<path d="M34 14H816a6 6 0 0 1 6 6V78H34Z" fill="{th["ink"]}"/>')
    c.parts[slot] = '<g>' + "".join(body)
    c.add("</g>")
    c.h = bottom + 22
    ticks = [pair for row in o["tools"] for pair in row]
    answers = " ".join(f'{label} {"ticked" if on else "unticked"}.' for label, on in o["answers"])
    on = ", ".join(label.lower() for label, state in ticks if state)
    off = ", ".join(label.lower() for label, state in ticks if not state)
    issues = " ".join(f"{a}, {b[0].lower()}{b[1:]}." for a, b in o["issues"])
    c.alt = [
        o["title"], o["model"], f'{o["question"]} {answers}',
        f'{o["unit_title"]}: {o["unit_text"]}', " ".join(o["unit_notes"]),
        f'{o["tools_title"]}: {o["tools_intro"].rstrip(":")}. Ticked: {on}. Not ticked: {off}. {o["tools_outro"]}',
        " ".join(o["tools_notes"]), f'{o["issues_title"]}: {issues}',
    ]
    return c


def tag_path(x0, y0, x1, y1, cut=22):
    return f"M{x0 + cut} {y0}H{x1 - cut}L{x1} {y0 + cut}V{y1 - cut}L{x1 - cut} {y1}H{x0 + cut}L{x0} {y1 - cut}V{y0 + cut}Z"


def work_order(th, d, o):
    c = Card(o["_id"], 840, 600, th)
    c.span = (8, 832)
    lx, vx = 76, 240
    right = 800
    vw = right - vx
    eye_x = 46
    top = 34
    p = c.parts
    start = len(p)

    c.text(lx, top + 36, LABELS["work_order"], "c", 20)
    base = top + 96
    name_w = c.text(lx, base, o["repo"], "s", o["name_size"], th["ink"], limit=630 if o.get("stamp") else right)
    if o.get("note"):
        c.scrawl(lx + name_w + 20, base - 6, o["note"], 36, th["scrawl_paper"], limit=right)

    x = lx
    box_y = base + 16
    first_box = None
    stars = star_label(d, o["repo"])
    for label in o["fits"] + stars:
        w = measure(label, "c", 20) + 22
        c.add(f'<rect x="{x}" y="{box_y}" width="{w:.0f}" height="34" fill="none" stroke="{th["ink"]}" stroke-width="1.4"/>')
        c.text(x + 11, box_y + 24, label, "c", 20, limit=right)
        first_box = first_box or (x, w)
        x += w + 10
    y = box_y + 34
    if o.get("under_fits"):
        c.add(f'<path d="M{lx + 34} {y + 28}c-8-6-11-14-10-24m-6 7l6-8 7 7" fill="none" stroke="{th["scrawl_paper"]}" stroke-width="2"/>')
        c.scrawl(lx + 50, y + 34, o["under_fits"], 34, th["scrawl_paper"], limit=right)
        y += 42
    y += 14

    for label, value in o["rows"]:
        c.add(f'<path d="M{lx} {y}H{right}" stroke="{th["ink"]}" stroke-opacity=".3"/>')
        c.text(lx, y + 27, label, "b", 20, limit=vx - 8)
        lines = wrap(value, "c", 20, vw)
        for i, line in enumerate(lines):
            c.text(vx, y + 27 + i * 27, line, "c", 20, limit=right)
        y += 16 + len(lines) * 27

    block_top = y
    c.add(f'<path d="M{lx} {y}H{right}" stroke="{th["ink"]}" stroke-opacity=".3"/>')
    c.text(lx + 8, y + 27, LABELS["goes_back"], "b", 20, BLUE_TEXT, limit=vx - 8)
    lines = wrap(o["back"], "b", 20, vw)
    for i, line in enumerate(lines):
        c.text(vx, y + 27 + i * 27, line, "b", 20, BLUE_TEXT, limit=right)
    y += 16 + len(lines) * 27
    for k, v in o.get("back_rows", []):
        vlines = wrap(v, "c", 20, right - vx - 222)
        c.text(vx, y + 16, k, "b", 20, limit=vx + 214)
        for i, line in enumerate(vlines):
            c.text(vx + 222, y + 16 + i * 27, line, "c", 20, limit=right)
        y += max(1, len(vlines)) * 27 + 6
    c.add(f'<rect x="{lx - 4}" y="{block_top + 6}" width="5" height="{y - block_top - 8}" fill="{BLUE_TEXT}"/>')
    c.add(f'<path d="M{lx} {y + 4}H{right}" stroke="{th["ink"]}" stroke-opacity=".3"/>')
    c.text(lx, y + 32, LABELS["get_it"], "b", 20, limit=vx - 8)
    url = repo_url(o["repo"])
    c.text(vx, y + 32, url, "b", 20, BLUE_TEXT, limit=right + 10)
    c.add(f'<path d="M{vx} {y + 37}H{vx + measure(url, "b", 20):.0f}" stroke="{BLUE_TEXT}" stroke-width="1.5"/>')
    y += 62

    sw = o["sticker_width"]
    sx = lx - 10
    warn = wrap(o["warning"], "b", 20, sw - 56)
    sh = 62 + len(warn) * 26
    sticker_top = y
    sticker = [
        f'<rect x="{sx}" y="{sticker_top}" width="{sw}" height="{sh}" fill="url(#hazard)" filter="url(#small)"/>',
        f'<rect x="{sx + 12}" y="{sticker_top + 12}" width="{sw - 24}" height="{sh - 24}" fill="§label_paper"/>',
    ]
    p.append(f'<g transform="rotate({o["sticker_tilt"]} {sx + sw / 2} {sticker_top + sh / 2})">' + "".join(sticker))
    c.text(sx + 28, sticker_top + 40, LABELS["warning"], "b", 20, BLUE_TEXT)
    for i, line in enumerate(warn):
        c.text(sx + 28, sticker_top + 66 + i * 26, line, "b", 20, "§dark_ink", limit=sx + sw)
    c.add("</g>")

    side_lines = o.get("side_note", [])
    for i, line in enumerate(side_lines):
        c.scrawl(sx + sw + 16, sticker_top + 32 + i * o.get("side_step", 34), line, o.get("side_size", 34), th["scrawl_paper"], rot=-2, limit=810)

    bottom = sticker_top + sh + 20
    if side_lines:
        bottom = max(bottom, sticker_top + o.get("side_step", 34) * len(side_lines) + 12)
    tag = tag_path(16, top, 824, bottom)
    extras = [
        f'<path d="{tag}" fill="{th["paper"]}" filter="url(#paper)"/><path d="{tag}" fill="{th["paper"]}"{th["edge"]}/>',
        f'<circle cx="{eye_x}" cy="{top + 30}" r="13" fill="{STEEL_DARK}"/><circle cx="{eye_x}" cy="{top + 30}" r="7" fill="§eyelet"/>',
        f'<path d="M{eye_x} {top + 30}L{eye_x} 9" stroke="§pin" stroke-width="2.2"/>',
    ]
    if o.get("smudge"):
        px, py = eye_x + 4, top + 66
        extras.append(
            f'<g fill="{th["ink"]}" opacity=".16"><ellipse cx="{px}" cy="{py}" rx="8" ry="6.5"/><circle cx="{px - 9}" cy="{py - 8}" r="3"/><circle cx="{px - 3}" cy="{py - 12}" r="3"/><circle cx="{px + 4}" cy="{py - 12}" r="3"/><circle cx="{px + 10}" cy="{py - 8}" r="3"/></g>'
        )
    if o.get("stamp"):
        sx0 = 640
        extras.append(
            f'<g transform="rotate(8 730 {top + 54})" filter="url(#stamp)"><rect x="{sx0}" y="{top + 28}" width="176" height="48" rx="4" fill="none" stroke="{BLUE_TEXT}" stroke-width="4"/>'
        )
        hold = []
        c.text(728, top + 66, o["stamp"], "s", 36, BLUE_TEXT, "middle", target=hold)
        extras.extend(hold)
        extras.append("</g>")
    p[start:start] = extras

    c.h = bottom + 30
    idx = "".join(ch for ch in o["_id"] if ch.isalpha())
    delay = 8 + 12 * o["_order"]
    c.css.append(
        f".s{idx},.n{idx}{{transform-box:view-box;transform-origin:{eye_x}px 9px}}"
        f".s{idx}{{animation:settle 1.2s ease-out 1}}"
        f".n{idx}{{animation:nudge 30s ease-in-out {delay}s infinite}}"
        "@keyframes settle{0%{transform:rotate(1.5deg)}35%{transform:rotate(-.8deg)}65%{transform:rotate(.35deg)}100%{transform:none}}"
        "@keyframes nudge{0%,95%,100%{transform:none}96.5%{transform:rotate(.6deg)}98%{transform:rotate(-.25deg)}}"
    )
    p[start:] = [f'<g class="s{idx}"><g class="n{idx}">' + "".join(p[start:]) + "</g></g>"]
    c.add(f'<circle cx="{eye_x}" cy="9" r="4.5" fill="§pin"/>')
    head = [f'{LABELS["work_order"]}: {o["repo"]}.'] + [o[k] for k in ("note", "stamp") if o.get(k)]
    if o.get("stamp"):
        head[-1] += "."
    fits = " ".join(f'{part.replace(": ", " ")}.' for part in o["fits"]) + "".join(f" {part}." for part in stars)
    c.alt = head + [fits] + [o[k] for k in ("under_fits",) if o.get(k)]
    c.alt += [f"{label}: {value}" for label, value in o["rows"]]
    c.alt += [f'{LABELS["goes_back"]} {o["back"]}'] + [f"{k}: {v}" for k, v in o.get("back_rows", [])]
    c.alt += [f'{LABELS["get_it"]}: {url}.', f'{LABELS["warning"]}: {o["warning"]}']
    if side_lines:
        c.alt.append(" ".join(side_lines))
    return c


def repo_url(repo):
    return f"github.com/{LOGIN}/{repo}"


def star_count(d, repo):
    if f"stars_{repo}" not in d:
        warnings.append(f"repo '{repo}' was not found under {LOGIN} on GitHub. Check the spelling.")
    return d.get(f"stars_{repo}", "0")


def star_label(d, repo):
    count = star_count(d, repo)
    return [] if count == "0" else [f'{LABELS["stars"]}: {count}']


def drawer(th, d, o):
    c = Card(o["_id"], 840, 312, th)
    c.span = (-4, 844)
    repo = o["repo"]
    c.add('<path d="M28 66L58 18H782L812 66Z" fill="§handle_dark" filter="url(#small)"/>')
    c.add(
        f'<g fill="none" stroke="{STEEL_DARK}" stroke-width="5"><circle cx="190" cy="52" r="20"/><circle cx="190" cy="52" r="11"/></g>'
        '<g transform="rotate(-24 430 50)"><rect x="370" y="44" width="46" height="13" rx="4" fill="§brand_blue"/><rect x="416" y="48" width="58" height="5" fill="§steel"/></g>'
        '<circle cx="660" cy="50" r="19" fill="§roller"/><circle cx="660" cy="50" r="8" fill="§handle_dark"/>'
    )
    face = "M12 66H828a8 8 0 0 1 8 8V292a10 10 0 0 1-10 10H14a10 10 0 0 1-10-10V74a8 8 0 0 1 8-8Z"
    c.add(f'<path d="{face}" fill="url(#steel)" filter="url(#drop)"/><path d="{face}" fill="url(#steel)" filter="url(#brushed)"/>')
    c.add('<path d="M4 76H836" stroke="#fff" stroke-opacity=".7" stroke-width="2"/><path d="M4 294H836" stroke="§cabinet_edge" stroke-width="3"/>')
    ink = "§dark_ink"
    c.add('<rect x="24" y="88" width="376" height="150" fill="§label_paper" filter="url(#small)"/>')
    if len(o["lines"]) > 5:
        warnings.append(f'{o["_id"]}: the drawer label holds 5 lines, and you have {len(o["lines"])}.')
    y = 116
    for line, weight in o["lines"]:
        c.text(38, y, line, "b" if weight == "bold" else "c", 20, ink, limit=398)
        y += 26
    c.add('<rect x="420" y="86" width="150" height="88" fill="§label_paper" stroke="§blade_edge" stroke-width="3"/>')
    c.text(495, 130, repo, "s", 40, ink, "middle", limit=568)
    c.text(495, 160, o["sub"], "c", 20, ink, "middle", limit=568)
    c.add('<path d="M430 192h130v10a24 24 0 0 1-24 24h-82a24 24 0 0 1-24-24z" fill="url(#steelh)" stroke="§cabinet_edge" stroke-width="2" filter="url(#small)"/>')
    for i, line in enumerate(o["scrawl"]):
        c.scrawl(700, 134 + i * 42, line, 40, "§pencil", "middle", limit=822)
    for part in star_label(d, repo):
        c.text(816, 222, part, "c", 20, ink, "end")
    c.text(38, 272, LABELS["get_it"], "b", 20, ink)
    url = repo_url(repo)
    c.text(130, 272, url, "b", 20, BLUE_TEXT)
    c.add(f'<path d="M130 277H{130 + measure(url, "b", 20):.0f}" stroke="{BLUE_TEXT}" stroke-width="1.5"/>')
    c.alt = [f'{repo}. {o["sub"]}.'] + [line for line, _ in o["lines"]] + [" ".join(o["scrawl"]), f'{LABELS["get_it"]}: {url}.']
    return c


def loaner(th, d, o):
    c = Card(o["_id"], 640, 372, th)
    c.add(hook(200, 20) + hook(400, 20))
    fork = (
        '<g filter="url(#small)" transform="translate(110 0) scale(.72 1)"><rect x="24" y="36" width="440" height="11" rx="5" fill="§cabinet"/>'
        '<path d="M12 28h26v8h-6v12h6v8H12v-8h6V36h-6z" fill="§cabinet"/>'
        '<path d="M464 20h16v43h-16z" fill="url(#steel)"/>'
        '<path d="M480 20h84l12 3-12 3h-68v6h68l12 3-12 3h-68v6h68l12 3-12 3h-68v6h68l12 3-12 3h-84z" fill="url(#steel)" stroke="§blade_edge" stroke-width=".8"/></g>'
    )
    c.add(fork)
    c.add(f'<path d="M260 47V108M380 47V108" fill="none" stroke="{STEEL_DARK}" stroke-width="2"/>')
    tag = tag_path(56, 92, 584, 358, 18)
    c.add(f'<path d="{tag}" fill="{th["loaner"]}" filter="url(#paper)"/><path d="{tag}" fill="{th["loaner"]}"{th["edge"]}/>')
    for ex in (260, 380):
        c.add(f'<circle cx="{ex}" cy="108" r="7" fill="{STEEL_DARK}"/><circle cx="{ex}" cy="108" r="3.5" fill="§eyelet"/>')
    c.add(f'<g transform="rotate(4 500 134)" filter="url(#stamp)"><rect x="428" y="110" width="140" height="44" rx="4" fill="none" stroke="{BLUE_TEXT}" stroke-width="4"/>')
    c.text(498, 144, o["stamp"], "s", 32, BLUE_TEXT, "middle")
    c.add("</g>")
    c.text(78, 148, o["repo"], "s", 42, "§dark_ink", limit=570)
    y = 188
    for line in wrap(o["text"], "c", 20, 490):
        c.text(78, y, line, "c", 20, "§dark_ink", limit=570)
        y += 27
    back = f'{LABELS["goes_back"]} {o["back"]}'
    c.text(78, y + 4, back, "b", 20, BLUE_TEXT, limit=570)
    c.scrawl(570, y + 66, o["scrawl"], 36, "§pencil", "end", rot=-1, limit=580)
    star_count(d, o["repo"])
    c.alt = [f'{o["stamp"]}. {o["repo"]}. {o["text"]}', back, o["scrawl"]]
    return c


def stock(th, d, o):
    c = Card(o["_id"], 840, 300, th)
    c.span = (0, 840)
    c.add(f'<rect x="100" y="8" width="640" height="46" rx="3" fill="{th["banner"]}" stroke="{th["banner_edge"]}" filter="url(#small)"/>')
    c.text(118, 41, o["title"], "s", 30, TAPE_TEXT, limit=330)
    c.text(722, 39, o["note"], "c", 20, TAPE_TEXT, "end", limit=736)
    body = "M8 52H832V284a6 6 0 0 1-6 6H14a6 6 0 0 1-6-6Z"
    c.add(f'<path d="{body}" fill="§cabinet" filter="url(#drop)"/>')
    if len(o["bins"]) > 4:
        warnings.append(f'{o["_id"]}: holds 4 bins, and you have {len(o["bins"])}.')
    sizes = d["_sizes"]
    whole = sum(sizes.values())
    c.alt = [f'{o["title"]}. {o["note"]}']
    for i, item in enumerate(o["bins"]):
        name, note = item["name"], item["note"]
        pct = percent(sum(sizes.get(lang, 0) for lang in item["languages"]), whole)
        c.alt.append(f'{name} {pct}. {" ".join(note)}')
        x = 18 + i * 203
        c.add(f'<rect x="{x}" y="62" width="196" height="218" rx="3" fill="url(#steel)" filter="url(#brushed)"/>')
        c.add(f'<path d="M{x + 10} 72h176v84h-176z" fill="§label_paper" stroke="§cabinet_edge" stroke-width="2"/>')
        c.text(x + 98, 100, name, "s", 24, "§dark_ink", "middle", limit=x + 190)
        c.text(x + 98, 144, pct, "s", 36, BLUE_TEXT, "middle", limit=x + 190)
        for j, line in enumerate(note):
            c.scrawl(x + 98, 192 + j * 26, line, 31, "§pencil", "middle", limit=x + 196)
        c.add(f'<path d="M{x + 60} 252h76v10a10 10 0 0 1-10 10h-56a10 10 0 0 1-10-10z" fill="url(#steelh)" stroke="§cabinet_edge" stroke-width="1.5"/>')
    return c


def timecard(th, d, o):
    c = Card(o["_id"], 840, 408, th)
    c.span = (4, 836)
    pitch = 14.4
    grid_x, grid_y = 42, 238
    weeks = d["_weeks"]
    top = max((day["c"] for week in weeks for day in week), default=1) or 1
    holes = []
    for w, week in enumerate(weeks):
        for day in week:
            r = 2.3 + 3.6 * min(1, math.sqrt(day["c"] / top)) if day["c"] else 1.4
            holes.append(f'<circle cx="{grid_x + w * pitch:.1f}" cy="{grid_y + day["w"] * pitch:.1f}" r="{r:.1f}"/>')
    shape = "M34 12H806L828 34V394H12V34Z"
    c.defs.append(
        f'<mask id="punch" maskUnits="userSpaceOnUse" x="0" y="0" width="840" height="408"><rect width="840" height="408" fill="#fff"/><g fill="#000">{"".join(holes)}</g></mask>'
    )
    if th["name"] == "light":
        c.add(f'<rect x="{grid_x - 10}" y="{grid_y - 10}" width="{pitch * 53 + 8:.0f}" height="{pitch * 7 + 6:.0f}" fill="§dark_ink"/>')
    c.add(f'<g filter="url(#drop)"><path d="{shape}" fill="{th["paper"]}" mask="url(#punch)"/></g>')
    if th["edge"]:
        c.add(f'<path d="{shape}" fill="none"{th["edge"]}/>')
    c.text(36, 62, o["title"], "s", 42, limit=300)
    c.text(804, 44, o["name"], "c", 20, anchor="end")
    c.text(804, 70, o["department"], "c", 20, anchor="end")
    c.add(f'<path d="M36 84H804" stroke="{th["ink"]}" stroke-opacity=".4"/>')
    if len(o["columns"]) > 3:
        warnings.append(f'{o["_id"]}: holds 3 columns, and you have {len(o["columns"])}.')
    for x, (label, value, note) in zip((36, 300, 564), o["columns"]):
        c.text(x, 114, label, "c", 20, limit=x + 250)
        c.text(x, 170, value, "s", 54, BLUE_TEXT if x == 36 else th["ink"], limit=x + 250)
        c.scrawl(x, 206, note, 31, th["scrawl_paper"], limit=x + 250)
    c.text(36, 352, o["legend"], "c", 20)
    c.text(804, 352, o["filled"], "c", 20, anchor="end")
    c.text(36, 378, o["machine"], "c", 20, limit=804)
    c.alt = [f'{o["title"]}. {o["name"]}. {o["department"]}.']
    c.alt += [f"{label}: {value}. {note}" for label, value, note in o["columns"]]
    c.alt += [f'{o["machine"]} {o["filled"]}.', o["legend"]]
    return c


def closer(th, d, o):
    c = Card(o["_id"], 840, 404, th)
    c.span = (-2, 840)
    door = "M34 8H806L832 34V396H8V34Z"
    c.defs.append(f'<clipPath id="door"><path d="{door}"/></clipPath>')
    c.defs.append(
        f'<radialGradient id="pool" gradientUnits="userSpaceOnUse" cx="640" cy="120" r="420"><stop offset="0" stop-color="{AMBER_SOFT}" stop-opacity=".55"/><stop offset=".35" stop-color="{AMBER}" stop-opacity=".32"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>'
    )
    c.add(f'<path d="{door}" fill="{DOOR}" filter="url(#drop)"/>')
    c.add(f'<g stroke="§door_panel" stroke-width="2" fill="none"><path d="M40 40H800V366H40Z"/></g>')
    c.add('<rect x="2" y="70" width="14" height="60" rx="3" fill="url(#steel)"/><rect x="2" y="280" width="14" height="60" rx="3" fill="url(#steel)"/>')

    c.add(f'<g class="lit" clip-path="url(#door)"><rect x="8" y="8" width="824" height="388" fill="url(#pool)"/></g>')
    c.add(f'<g class="eyes"><ellipse cx="470" cy="70" rx="9" ry="6" fill="{"§bright_blue"}"/><ellipse cx="510" cy="70" rx="9" ry="6" fill="§bright_blue"/></g>')

    c.add('<path d="M120 14L170 70M280 14L230 70" stroke="§blade_edge" stroke-width="3" stroke-dasharray="7 4"/><circle cx="120" cy="14" r="4" fill="§blade_edge"/><circle cx="280" cy="14" r="4" fill="§blade_edge"/>')
    c.add('<rect x="70" y="68" width="260" height="110" rx="5" fill="§label_paper" filter="url(#small)"/><rect x="78" y="76" width="244" height="94" rx="3" fill="none" stroke="§dark_ink" stroke-width="2"/>')
    c.text(200, 150, o["sign"], "s", 72, "§dark_ink", "middle", limit=322)
    for i, line in enumerate(o["scrawl"]):
        c.scrawl(52, 240 + i * 42, line, 42, "§chalk", limit=400)

    c.add('<g stroke="§steel_dark" fill="none"><path d="M650 8v22" stroke-width="3"/><path d="M700 40v44" stroke-width="1.6" stroke-dasharray="3 3"/></g>')
    c.add('<path d="M618 30h64l18 40h-100z" fill="§cabinet"/><ellipse cx="650" cy="70" rx="50" ry="7" fill="§amber_soft"/><circle cx="700" cy="88" r="3.5" fill="§steel_dark"/>')

    tape_y = 96
    lines = wrap(o["note"], "c", 20, 350)
    lines2 = wrap(o["note_bold"], "b", 20, 350)
    h = (len(lines) + len(lines2)) * 26 + 34
    c.add(f'<g transform="rotate(-.8 600 200)"><rect x="412" y="{tape_y}" width="382" height="{h}" fill="§note_paper" filter="url(#small)"/>')
    if tape_y + h + 54 > 372:
        warnings.append(f'{o["_id"]}: the note is too long and runs into the lines below it.')
    y = tape_y + 30
    for line in lines:
        c.text(428, y, line, "c", 20, "§dark_ink", limit=790)
        y += 26
    y += 4
    for line in lines2:
        c.text(428, y, line, "b", 20, "§dark_ink", limit=790)
        y += 26
    c.add("</g>")
    c.add('<g class="lit">')
    c.scrawl(428, tape_y + h + 54, o["lit"], 44, AMBER, limit=810)
    c.add("</g>")
    c.scrawl(790, 372, o["food"], 31, AMBER_SOFT, "end", limit=810)
    c.css.append(
        ".lit{animation:lit 24s linear infinite}@keyframes lit{0%,88.9%{opacity:1}89%,99.3%{opacity:0}99.4%,100%{opacity:1}}"
        ".eyes{opacity:0;animation:eyes 24s linear infinite}@keyframes eyes{0%,89%{opacity:0}89.5%,93%{opacity:1}93.2%,93.9%{opacity:0}94%,99.2%{opacity:1}99.3%,100%{opacity:0}}"
    )
    c.alt = [f'{o["sign"]}. {" ".join(o["scrawl"])}', o["note"], o["note_bold"], o["lit"], o["food"]]
    return c


STYLES = {
    "hero": hero, "key": key, "shelf_label": shelf_label, "work_order": work_order, "drawer": drawer,
    "loaner": loaner, "manual": manual, "rules": rules, "stock": stock, "timecard": timecard, "closer": closer,
}


def token():
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def graphql(query, **variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body, {"Authorization": f"bearer {token()}", "User-Agent": "pops-shop"})
    with urllib.request.urlopen(req) as res:
        out = json.load(res)
    if out.get("errors"):
        raise SystemExit(out["errors"])
    return out["data"]


def short_size(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    return f"{n / 1_000:.0f} KB"


def percent(part, whole):
    share = part / whole * 100 if whole else 0
    return "under 1%" if share < 0.5 else f"{share:.0f}%"


def fetch():
    q = """query($login:String!,$cursor:String){user(login:$login){followers{totalCount}
      repositories(first:100,after:$cursor,ownerAffiliations:OWNER,privacy:PUBLIC){totalCount pageInfo{hasNextPage endCursor}
      nodes{name isFork stargazerCount languages(first:30){edges{size node{name}}}}}}}"""
    repos, cursor, followers, total = [], None, 0, 0
    while True:
        u = graphql(q, login=LOGIN, cursor=cursor)["user"]
        followers = u["followers"]["totalCount"]
        total = u["repositories"]["totalCount"]
        repos += u["repositories"]["nodes"]
        if not u["repositories"]["pageInfo"]["hasNextPage"]:
            break
        cursor = u["repositories"]["pageInfo"]["endCursor"]

    sizes = {}
    for r in repos:
        if r["isFork"] or r["name"] in SHOP["skip_in_stats"]:
            continue
        for e in r["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]

    cal = """query($login:String!,$from:DateTime,$to:DateTime){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""
    now = datetime.datetime.now(datetime.timezone.utc)
    this_year = graphql(cal, login=LOGIN)["user"]["contributionsCollection"]["contributionCalendar"]
    today = now.date()

    weeks = [[{"c": d["contributionCount"], "w": d["weekday"]} for d in w["contributionDays"]] for w in this_year["weeks"]][-53:]
    data = {
        "repos": str(total),
        "followers": str(followers),
        "stars_total": str(sum(r["stargazerCount"] for r in repos)),
        "contributions": f"{this_year['totalContributions']:,}",
        "date": today.isoformat(),
        "_weeks": weeks,
        "_sizes": sizes,
    }
    for r in repos:
        lua = sum(e["size"] for e in r["languages"]["edges"] if e["node"]["name"] in ("Lua", "Luau"))
        data.setdefault(f'stars_{r["name"]}', str(r["stargazerCount"]))
        data.setdefault(f'lua_{r["name"]}', short_size(lua))
    return data


def avatar_uri():
    path = HERE / SHOP["avatar"]
    kinds = {".webp": "webp", ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg"}
    if path.suffix.lower() not in kinds:
        raise SystemExit("avatar must be a webp, png or jpg")
    return f"data:image/{kinds[path.suffix.lower()]};base64," + base64.b64encode(path.read_bytes()).decode()


def lint(text, where):
    found = re.search(r".{0,30}[–—].{0,30}", text)
    if found:
        raise SystemExit(f"{where} has a long dash, in: {found.group(0)}. Swap it for a comma or a period.")


def fill(value, tokens):
    if isinstance(value, str):
        def swap(match):
            if match.group(1) not in tokens:
                raise SystemExit(f"shop.toml uses {{{match.group(1)}}}, which doesn't exist. See HOWTO.md for the list.")
            return tokens[match.group(1)]
        return re.sub(r"\{([\w.-]+)\}", swap, value)
    if isinstance(value, list):
        return [fill(v, tokens) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, tokens) for k, v in value.items()}
    return value


def tokens_from(d):
    words = {k: v for k, v in SHOP.items() if isinstance(v, str) and k != "footer"}
    return {**words, **{k: v for k, v in d.items() if isinstance(v, str)}}


def parse_page():
    rows = []
    for entry in CONFIG["page"]:
        parts = entry.split(" + ")
        if len(parts) > 1:
            rows.append([(part.strip(), f"{99.6 / len(parts):g}%") for part in parts])
            continue
        bits = entry.split()
        if len(bits) > 2 or (len(bits) == 2 and not bits[1].endswith("%")):
            raise SystemExit(f'page entry "{entry}" looks wrong. Use "name", "name 76%" or "name + name".')
        rows.append([(bits[0], bits[1] if len(bits) > 1 else "100%")])
    return rows


def picture(card_id, width, alt):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{card_id}-dark.svg">'
        f'<img src="assets/{card_id}-light.svg" width="{width}" alt="{alt}"></picture>'
    )


def link_for(o):
    if o.get("link"):
        return o["link"]
    return f'https://{repo_url(o["repo"])}' if o.get("repo") else "#"


def draw(card_id, settings, theme, d):
    style = settings.get("style")
    if style not in STYLES:
        raise SystemExit(f'card {card_id}: style "{style}" doesn\'t exist. Choose from: {", ".join(STYLES)}')
    try:
        return STYLES[style](theme, d, settings)
    except KeyError as e:
        raise SystemExit(f"card {card_id} is missing the setting {e} in shop.toml")
    except (ValueError, TypeError, IndexError, AttributeError):
        raise SystemExit(f"card {card_id}: a list in shop.toml has the wrong shape. Compare it with the same style's other cards.")


def build(d):
    ASSETS.mkdir(exist_ok=True)
    tokens = tokens_from(d)
    cards = fill(CONFIG["cards"], tokens)
    LABELS.update(fill(CONFIG["labels"], tokens))
    settings = fill(CONFIG["github"], tokens)
    lint(settings["bio"], "bio")
    if len(settings["bio"]) > 160:
        warnings.append(f'bio is {len(settings["bio"])} characters. GitHub allows 160.')
    for repo, text in settings["descriptions"].items():
        lint(text, f"{repo} description")
        if len(text) > 350:
            warnings.append(f"{repo} description is {len(text)} characters. GitHub allows 350.")
    rows = parse_page()
    used = [card_id for row in rows for card_id, _ in row]
    for card_id in used:
        if card_id not in cards:
            raise SystemExit(f'page lists "{card_id}" but shop.toml has no [cards.{card_id}]')
    order = 0
    total = 0
    alts = {}
    expected = set()
    for card_id in used:
        o = dict(cards[card_id], _id=card_id, _order=order)
        order += o.get("style") == "work_order"
        for theme in THEMES.values():
            card = draw(card_id, o, theme, d)
            svg = card.render()
            lint(svg, card.id)
            name = f"{card.id}-{theme['name']}.svg"
            (ASSETS / name).write_text(svg, encoding="utf-8")
            expected.add(name.casefold())
            total += len(svg)
            if len(svg) > 200_000:
                warnings.append(f"{card.id}: {len(svg)} bytes")
            if theme["name"] == "dark":
                alts[card_id] = html.escape(" ".join(" ".join(card.alt).split()), quote=True)
    for old in ASSETS.glob("*.svg"):
        if old.name.casefold() not in expected:
            old.unlink()
    lines = ['<div align="center">', ""]
    for row in rows:
        lines.append("".join(f'<a href="{link_for(cards[i])}">{picture(i, w, alts[i])}</a>' for i, w in row))
        lines.append("")
    lines += [fill(SHOP["footer"], tokens), "", "</div>", ""]
    readme = "\n".join(lines)
    lint(readme, "README")
    (REPO / "README.md").write_text(readme, encoding="utf-8")
    print(f"built, {total // 1024} KB of svg")
    for w in dict.fromkeys(warnings):
        print("WARN", w)


PAGE = """<!doctype html><meta charset=utf-8><title>Profile preview</title><style>
body{margin:0;background:BG;color:FG;font:14px/1.5 -apple-system,'Segoe UI',sans-serif}
.wrap{display:flex;gap:24px;max-width:1216px;margin:0 auto;padding:24px 32px}
.side{width:296px;flex:none}.side img{width:296px;border-radius:50%;border:1px solid LINE}
.side h1{font-size:24px;margin:16px 0 0;font-weight:600}.side .log{font-size:20px;color:MUTE;font-weight:300}
.side p{font-size:16px}.main{flex:1;min-width:0}
.box{border:1px solid LINE;border-radius:6px;padding:24px;background:BOX}
.crumb{font-size:12px;margin-bottom:16px;font-family:monospace}
.md img{max-width:100%}.md p{margin:0 0 16px}.md code{background:CODE;padding:.2em .4em;border-radius:6px;font-size:85%}
.md a{text-decoration:none}
</style><div class=wrap><div class=side><img src="AVATAR"><h1>OWNER</h1><div class=log>LOGIN</div><p>BIOTEXT</p></div>
<div class=main><div class=box><div class=crumb>LOGIN / README.md</div><div class=md>CONTENT</div></div></div></div>"""
PAGE_COLORS = {
    "dark": dict(BG="#0d1117", FG="#e6edf3", LINE="#30363d", MUTE="#8b949e", BOX="#0d1117", CODE="#6e768166"),
    "light": dict(BG="#ffffff", FG="#1f2328", LINE="#d1d9e0", MUTE="#59636e", BOX="#ffffff", CODE="#818b981f"),
}


def find_browser():
    names = ["msedge", "chrome", "google-chrome", "chromium"]
    roots = [os.environ.get(k, "") for k in ("ProgramFiles(x86)", "ProgramFiles")]
    spots = [Path(r) / "Microsoft/Edge/Application/msedge.exe" for r in roots if r]
    spots += [Path(r) / "Google/Chrome/Application/chrome.exe" for r in roots if r]
    found = [shutil.which(n) for n in names] + [str(p) for p in spots if p.exists()]
    return next((f for f in found if f), None)


def preview(d, open_it):
    PREVIEW.mkdir(exist_ok=True)
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    browser = find_browser()
    tall = sum(int(re.search(r'height="(\d+)"', f.read_text(encoding="utf-8")).group(1)) for f in ASSETS.glob("*-dark.svg"))
    pages = []
    for theme in PAGE_COLORS:
        text = re.sub(r'<source media="\(prefers-color-scheme: dark\)" srcset="[^"]+">', "", readme)
        text = re.sub(r"assets/([\w-]+)-light\.svg", lambda m: f"../../assets/{m.group(1)}-{theme}.svg", text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        blocks = [b.strip() for b in text.split("\n\n")]
        parts = [f"<p>{b}</p>" for b in blocks if b and not b.startswith(("<div", "</div"))]
        page = PAGE
        for k, v in PAGE_COLORS[theme].items():
            page = page.replace(k, v)
        words = {"AVATAR": f'../{SHOP["avatar"]}', "OWNER": SHOP["owner"], "LOGIN": LOGIN, "BIOTEXT": fill(CONFIG["github"]["bio"], tokens_from(d))}
        for k, v in words.items():
            page = page.replace(k, v)
        page = page.replace("CONTENT", '<div align="center">' + "\n".join(parts) + "</div>")
        path = PREVIEW / f"profile-{theme}.html"
        path.write_text(page, encoding="utf-8")
        pages.append(path)
        if browser:
            subprocess.run(
                [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                 "--force-prefers-reduced-motion", f"--window-size=1280,{tall + 400}", f"--screenshot={path.with_suffix('.png')}",
                 "--virtual-time-budget=8000", path.as_uri()],
                check=True, capture_output=True,
            )
    print("preview:", PREVIEW)
    if open_it:
        webbrowser.open(pages[0].as_uri())


def gh(*args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if out.returncode:
        raise SystemExit(out.stderr.strip())
    return out.stdout.strip()


def apply_github(d, yes):
    tokens = tokens_from(d)
    settings = fill(CONFIG["github"], tokens)
    bio = settings["bio"]
    if len(bio) > 160:
        raise SystemExit(f"bio is {len(bio)} characters. GitHub allows 160.")
    lint(bio, "bio")
    for repo, text in settings["descriptions"].items():
        if len(text) > 350:
            raise SystemExit(f"{repo} description is {len(text)} characters. GitHub allows 350.")
        lint(text, repo)
        if gh("api", f"repos/{LOGIN}/{repo}", "--jq", ".description") != text:
            print(f"{repo} -> {text}")
            if yes:
                gh("repo", "edit", f"{LOGIN}/{repo}", "--description", text)
    if gh("api", f"users/{LOGIN}", "--jq", ".bio") != bio:
        print(f"bio -> {bio}")
        if yes and subprocess.run(["gh", "api", "-X", "PATCH", "user", "-f", f"bio={bio}"], capture_output=True).returncode:
            raise SystemExit("Repo descriptions are done, but GitHub refused the bio. Run this once, then try again: gh auth refresh -h github.com -s user")
    print("applied" if yes else "nothing changed. Add --yes to apply what's listed.")


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO).returncode


def publish(yes):
    if not yes:
        print("Would push to", subprocess.run(["git", "remote", "get-url", "origin"], cwd=REPO, capture_output=True, text=True).stdout.strip())
        print("Changed since the last publish, not counting generated files:")
        git("status", "--short", "--", ".", ":(exclude)assets", ":(exclude)README.md")
        print("Check it with --preview, then add --yes.")
        return
    if git("fetch", "origin"):
        raise SystemExit("Couldn't reach GitHub. Nothing was changed.")
    git("checkout", "HEAD", "--", "README.md")
    git("checkout", "HEAD", "--", "assets")
    git("clean", "-fdq", "assets")
    if git("pull", "--rebase", "--autostash"):
        git("rebase", "--abort")
        raise SystemExit("Your changes clash with what's on GitHub. Nothing was published. Run --preview to rebuild, then sort out the clash in git.")
    if subprocess.run([sys.executable, str(HERE / "build.py"), "--strict"], cwd=REPO).returncode:
        raise SystemExit("Stopped by the message above. Nothing was committed.")
    git("add", "-A")
    if git("diff", "--cached", "--quiet") == 0:
        print("nothing to publish")
        return
    user_id = gh("api", f"users/{LOGIN}", "--jq", ".id")
    message = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    if git("-c", f'user.name={SHOP["owner"]}', "-c", f"user.email={user_id}+{LOGIN}@users.noreply.github.com", "commit", "-m", message):
        raise SystemExit("The commit failed. Nothing was published.")
    if git("push"):
        git("reset", "HEAD~1")
        raise SystemExit("The push failed. Your edits are still here, so run --publish --yes again.")
    print("published. If you changed the bio or a repo description, run --apply-github --yes too.")


def numbers(offline):
    if offline:
        if not NUMBERS.exists():
            raise SystemExit("no saved numbers yet. Run once without --offline.")
        d = json.loads(NUMBERS.read_text(encoding="utf-8"))
    else:
        d = fetch()
        PREVIEW.mkdir(exist_ok=True)
        NUMBERS.write_text(json.dumps(d), encoding="utf-8")
    d["_avatar"] = avatar_uri()
    return d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--apply-github", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args(argv)
    if args.publish:
        publish(args.yes)
    elif args.apply_github:
        apply_github(numbers(args.offline), args.yes)
    else:
        d = numbers(args.offline)
        build(d)
        if args.preview:
            preview(d, not args.no_open)
        if args.strict and warnings:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
