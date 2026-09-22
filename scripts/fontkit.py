"""Embed subset webfonts inside SVGs, and measure real text widths.

An <img>-loaded SVG can't fetch external fonts, but a base64 @font-face in its
own <style> renders fine. Subsetting to the glyphs each file actually uses keeps
a face to a few KB. Both faces are SIL OFL 1.1 — see scripts/fonts/.
"""
import base64
import html
import io
import os
import re
from functools import lru_cache

from fontTools import subset
from fontTools.ttLib import TTFont

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# family name as written in the SVGs -> [(weight, file)]
FACES = {
    "JetBrains Mono": [(400, "JetBrainsMono-Regular.ttf"), (700, "JetBrainsMono-Bold.ttf")],
    "Anybody": [(800, "Anybody-ExpandedExtraBold.ttf")],
}


def _face(family, weight):
    return os.path.join(FONTS, min(FACES[family], key=lambda wf: abs(wf[0] - weight))[1])


@lru_cache(None)
def _font(path):
    return TTFont(path)


def text_width(family, weight, text, size, tracking=0.0):
    """Advance width in px, from the font's own hmtx table."""
    f = _font(_face(family, weight))
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    total = 0
    for ch in text:
        g = cmap.get(ord(ch))
        assert g is not None, f"{family} has no glyph for {ch!r}"
        total += hmtx[g][0]
    return total / upm * size + tracking * size * max(len(text) - 1, 0)


def fit_size(family, weight, text, max_w, max_size, tracking=0.0):
    return min(max_size, max_w / text_width(family, weight, text, 1.0, tracking))


def cap_height(family, weight, size):
    f = _font(_face(family, weight))
    return f["OS/2"].sCapHeight / f["head"].unitsPerEm * size


def _subset_b64(path, chars):
    f = TTFont(path)
    s = subset.Subsetter()
    s.populate(text=chars)
    s.subset(f)
    f.flavor = "woff2"
    buf = io.BytesIO()
    f.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def embed(svg):
    """Inject @font-face rules for every family the SVG references."""
    chars = html.unescape(re.sub(r"<[^>]+>", " ", svg))
    chars = "".join(sorted(set(chars + " ")))
    rules = []
    for fam, faces in FACES.items():
        if fam not in svg:
            continue
        for weight, name in faces:
            b = _subset_b64(os.path.join(FONTS, name), chars)
            rules.append(f"@font-face{{font-family:'{fam}';font-weight:{weight};"
                         f"src:url(data:font/woff2;base64,{b}) format('woff2')}}")
    if not rules:
        return svg
    return re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1) + "<style>" + "".join(rules) + "</style>", svg, count=1)
