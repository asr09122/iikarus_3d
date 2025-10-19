# app/normalize.py
import re, html
from typing import Dict, List, Tuple, Optional

def normalize_listing(
    title: Optional[str],
    raw_description: str,
    raw_creative: Optional[str] = None
) -> Dict:
    """
    Clean marketplace text into display-ready fields.
    Returns a dict:
      {
        "title": str,
        "description": str,        # readable prose (+ inline bullets)
        "creative": str|None,      # polished blurb
        "features": [str, ...],    # synthesized bullets (size, backing, care, etc.)
        "dimensions": {            # parsed dims if found
          "width_in": "...", "length_in": "...",
          "width_cm": "...", "length_cm": "...",
          "thickness_in": "..."
        }
      }
    """

    _RE_MULTI_SPACE = re.compile(r"[ \t\u00A0]{2,}")
    _RE_WS = re.compile(r"\s+")
    _RE_CONTROL = re.compile(r"[\u0000-\u001F\u007F]")
    _RE_TRAIL_SEPS = re.compile(r"([,;/|\-])\s*([,;/|\-])+")
    _RE_DIM_INCH = re.compile(r'''(?ix)(?P<w>\d+(?:\.\d+)?)\s*["”]?\s*(?:\(w\))?\s*[x×]\s*(?P<l>\d+(?:\.\d+)?)\s*["”]?\s*(?:\(l\))?''')
    _RE_DIM_CM   = re.compile(r'''(?ix)(?P<w>\d+(?:\.\d+)?)\s*cm\s*[x×]\s*(?P<l>\d+(?:\.\d+)?)\s*cm''')
    _RE_THICK    = re.compile(r'''(?ix)(?:thickness[:\s]*)?(?P<t>\d+(?:\.\d+)?)\s*(?:inch|in|")''')
    _RE_BAD_TOKS = str.maketrans({
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "’": "'", "‘": "'", "‚": "'", "‛": "'",
        "×": "x", "–": "-", "—": "-", "‒": "-",
        "•": " ", "★": " ", "☆": " ", "【": " ", "】": " ", "、": ", "
    })
    _DROP = [
        r"customer service",
        r"0\s*risk purchase",
        r"perfect shopping experience",
        r"contact us.*?purchase",
        r"we will do our best.*?satisfied",
    ]

    def _strip_controls(s: str) -> str:
        s = _RE_CONTROL.sub(" ", s)
        s = s.translate(_RE_BAD_TOKS)
        s = html.unescape(s)
        s = _RE_TRAIL_SEPS.sub(r"\1 ", s)
        s = _RE_MULTI_SPACE.sub(" ", s)
        s = _RE_WS.sub(" ", s)
        return s.strip()

    def _normalize_delims(s: str) -> str:
        s = re.sub(r"\s*[|/]\s*", ", ", s)
        s = re.sub(r"\s*,\s*,+\s*", ", ", s)
        return s

    def _drop_boiler(s: str) -> str:
        for p in _DROP:
            s = re.sub(p, " ", s, flags=re.I)
        return s

    def _sentenceize(s: str) -> str:
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|(?<=\")\s+(?=[A-Z0-9])", s.strip())
        out: List[str] = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if not re.match(r"[A-Z0-9\"]", p):
                p = p[:1].upper() + p[1:]
            out.append(p.rstrip(",;"))
        return " ".join(out)

    def _normalize_dimensions(text: str) -> Tuple[str, Dict[str, str]]:
        dims: Dict[str, str] = {}
        out = text
        m = _RE_DIM_INCH.search(out)
        if m:
            w, l = m.group("w"), m.group("l")
            dims["width_in"], dims["length_in"] = w, l
            out = _RE_DIM_INCH.sub(f'{w}" × {l}"', out, count=1)
        m2 = _RE_DIM_CM.search(out)
        if m2:
            wcm, lcm = m2.group("w"), m2.group("l")
            dims["width_cm"], dims["length_cm"] = wcm, lcm
            out = _RE_DIM_CM.sub(f"{wcm} × {lcm} cm", out, count=1)
        mt = _RE_THICK.search(out)
        if mt:
            t = mt.group("t")
            dims["thickness_in"] = t
            out = _RE_THICK.sub(f'{t}" thickness', out, count=1)
        return out, dims

    def _synthesize_bullets(clean_text: str, dims: Dict[str, str]) -> List[str]:
        bullets: List[str] = []
        if dims.get("width_in") and dims.get("length_in"):
            inch = f'{dims["width_in"]}" × {dims["length_in"]}"'
            if dims.get("width_cm") and dims.get("length_cm"):
                cm = f'{dims["width_cm"]} × {dims["length_cm"]} cm'
                bullets.append(f"Size: {inch} ({cm})")
            else:
                bullets.append(f"Size: {inch}")
        elif dims.get("width_cm") and dims.get("length_cm"):
            bullets.append(f'Size: {dims["width_cm"]} × {dims["length_cm"]} cm')
        if dims.get("thickness_in"):
            bullets.append(f'Thickness: {dims["thickness_in"]}" (low profile)')
        if re.search(r"\banti[- ]?slip|non[- ]?slip\b", clean_text, re.I):
            bullets.append("Backing: Anti-slip rubber")
        if re.search(r"\bpolyester\b", clean_text, re.I):
            bullets.append("Surface: Non-woven polyester")
        if re.search(r"\b(machine washable|washable)\b", clean_text, re.I):
            bullets.append("Care: Machine washable")
        if re.search(r"\b(hardwood|wood floor)\b", clean_text, re.I):
            bullets.append("Floor Safety: Suitable for hardwood")
        seen, dedup = set(), []
        for b in bullets:
            if b not in seen:
                seen.add(b); dedup.append(b)
        return dedup

    def _clean_title(t: Optional[str]) -> str:
        if not t:
            return "Doormat, Low-Profile, Anti-Slip"
        t = _strip_controls(_normalize_delims(t))
        t = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", t, flags=re.I)
        return _sentenceize(t)

    # description
    s = raw_description or ""
    s = _drop_boiler(s)
    s = _normalize_delims(s)
    s = _strip_controls(s)
    s, dims = _normalize_dimensions(s)
    s = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", s, flags=re.I)
    s = re.sub(r"\s*[★☆]+", " ", s)
    s = re.sub(r"\s*,\s*\.", ".", s)
    s = re.sub(r"\s*,\s*,", ", ", s)
    clean_desc = _sentenceize(s)

    # features
    features = _synthesize_bullets(clean_desc, dims)

    # creative
    creative = (raw_creative or "").strip()
    creative = _strip_controls(creative)
    creative = re.sub(r"\s*(?:[^\w\s]|_){2,}\s*$", "", creative)
    creative = _sentenceize(creative)

    # title
    nice_title = _clean_title(title)

    if features:
        clean_desc = clean_desc.rstrip(".") + ". " + " ".join(f"• {b}." for b in features)

    return {
        "title": nice_title,
        "description": clean_desc,
        "creative": creative or None,
        "features": features,
        "dimensions": dims
    }
