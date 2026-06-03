"""Parse the UW Bothell CSS course-descriptions text into a structured JSON snapshot.

Source: backend/data/catalog/css_descriptions.txt (a faithful transcription of the
public UW Bothell "Computing & Software Systems" course-descriptions page).

Output: backend/data/catalog/css_catalog.json

Run:
    cd backend && python -m app.catalog.parse_catalog
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent.parent / "data" / "catalog"
SRC_TXT = _DATA / "css_descriptions.txt"
OUT_JSON = _DATA / "css_catalog.json"

# A course header looks like:  "CSS 142 Computer Programming I (5) NSc, RSN"
# code = "CSS 142", title = "Computer Programming I", credits group = "5",
# trailing attributes = "NSc, RSN" (optional)
HEADER_RE = re.compile(
    r"^(?P<code>CSS\s+\d{3}[A-Z]?)\s+"
    r"(?P<title>.+?)\s+"
    r"\((?P<credits>[^)]*)\)"
    r"(?:\s+(?P<attrs>[A-Za-z/&,\s]+?))?\s*$"
)

MYPLAN_RE = re.compile(r"^View course details in MyPlan:\s*(CSS\s+\d{3}[A-Z]?)\s*$")

# Known UW gen-ed / writing attribute tokens so we don't mistake stray words for attrs.
KNOWN_ATTRS = {
    "RSN", "NSc", "SSc", "A&H", "DIV", "C", "W", "QSR", "VLPA", "I&S", "NW",
    "A&H/NSc", "NSc/RSN",
}


def _split_attrs(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",")]
    out = []
    for p in parts:
        if not p:
            continue
        # keep tokens that look like attribute codes (short, mostly caps/&/slash)
        if p in KNOWN_ATTRS or re.fullmatch(r"[A-Z][A-Za-z&/]{0,6}", p):
            out.append(p)
    return out


def _parse_credits(raw: str) -> Dict:
    """Return {raw, min, max, fixed} from a credits string like '5', '1-5, max. 6',
    '0-5, max. 10', 'variable'."""
    raw = raw.strip()
    info = {"raw": raw, "min": None, "max": None}
    # strip a "max. N" clause
    m = re.search(r"(\d+)\s*-\s*(\d+)", raw)
    if m:
        info["min"] = int(m.group(1))
        info["max"] = int(m.group(2))
        return info
    m = re.match(r"^(\d+)", raw)
    if m:
        info["min"] = info["max"] = int(m.group(1))
    return info


def _representative_credits(credits: Dict) -> int:
    """A single integer used for scheduling math. Prefer the typical 5-credit
    lecture value; fall back to the min of a range."""
    if credits["min"] is not None:
        # For ranges (independent study etc.), use the min; for fixed, that's the value.
        return credits["min"]
    return 0


PREREQ_RE = re.compile(r"Prerequisite:\s*(?P<txt>.+?)(?:\s*(?:Offered:|Recommended:|Co-requisite:)|$)", re.S)
OFFERED_RE = re.compile(r"Offered:\s*(?P<txt>[^.]+)\.?")
COREQ_RE = re.compile(r"Co-requisite:\s*(?P<txt>[^.]+)\.?")
OVERLAP_RE = re.compile(r"Course overlaps with:\s*(?P<txt>[^.]+)\.?")
COURSE_CODE_RE = re.compile(r"\b([A-Z]{1,5}(?:\s[A-Z]{1,4})?)\s?(\d{3})\b")


def _extract_prereq_codes(prereq_text: str) -> List[str]:
    """Best-effort list of course codes mentioned in the prerequisite sentence."""
    if not prereq_text:
        return []
    codes = []
    for m in COURSE_CODE_RE.finditer(prereq_text):
        prefix = m.group(1).strip()
        num = m.group(2)
        # skip grade-y numbers that aren't courses (handled by \d{3} already)
        code = f"{prefix} {num}"
        if code not in codes:
            codes.append(code)
    return codes


def parse_text(text: str) -> List[Dict]:
    # Normalize whitespace within blocks separated by blank lines
    blocks = re.split(r"\n\s*\n", text)
    courses: List[Dict] = []

    for block in blocks:
        lines = [ln.rstrip() for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        header = HEADER_RE.match(lines[0])
        if not header:
            continue  # skip preamble/header chrome

        code = re.sub(r"\s+", " ", header.group("code")).strip()
        title = header.group("title").strip()
        credits = _parse_credits(header.group("credits"))
        attrs = _split_attrs(header.group("attrs"))

        # Description = everything between header and the MyPlan line
        desc_lines = []
        for ln in lines[1:]:
            if MYPLAN_RE.match(ln):
                break
            desc_lines.append(ln)
        description = " ".join(desc_lines).strip()

        prereq_text = None
        pm = PREREQ_RE.search(description)
        if pm:
            prereq_text = pm.group("txt").strip().rstrip(".")

        offered = None
        om = OFFERED_RE.search(description)
        if om:
            offered = om.group("txt").strip()

        overlaps = None
        ov = OVERLAP_RE.search(description)
        if ov:
            overlaps = ov.group("txt").strip()

        courses.append({
            "code": code,
            "title": title,
            "credits": _representative_credits(credits),
            "credits_detail": credits,
            "attributes": attrs,
            "description": description,
            "prerequisite_text": prereq_text,
            "prerequisite_codes": _extract_prereq_codes(prereq_text or ""),
            "offered": offered,
            "overlaps_with": overlaps,
            "level": "graduate" if int(re.search(r"\d{3}", code).group()) >= 500 else "undergraduate",
        })

    return courses


def build_snapshot() -> List[Dict]:
    text = SRC_TXT.read_text(encoding="utf-8")
    courses = parse_text(text)
    OUT_JSON.write_text(json.dumps(courses, indent=2, ensure_ascii=False), encoding="utf-8")
    return courses


if __name__ == "__main__":
    parsed = build_snapshot()
    print(f"Parsed {len(parsed)} courses -> {OUT_JSON}")
    # Sanity sample
    for c in parsed[:3]:
        print(f"  {c['code']}: {c['title']} ({c['credits']} cr) attrs={c['attributes']} "
              f"prereqs={c['prerequisite_codes']}")
