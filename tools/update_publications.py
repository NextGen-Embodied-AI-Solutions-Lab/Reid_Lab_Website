#!/usr/bin/env python3
"""Refresh the list in publications.html from Dr. Reid's public ORCID record.

Usage (from the project folder):
  python3 tools/update_publications.py            fetch ORCID, then rebuild the page
  python3 tools/update_publications.py --offline  rebuild from the saved copy, without fetching
Needs only the Python standard library (and an internet connection, unless --offline).

The ORCID list is saved to data/orcid-works.json. Papers added through the website's GitHub
form live in data/publications.json and are merged in. Rewrites everything between the
BEGIN/END PUBLICATIONS markers in publications.html.
"""
import html, json, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

ORCID = "0000-0001-5286-8555"
ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "publications.html"
CACHE = ROOT / "data" / "orcid-works.json"
EXTRA = ROOT / "data" / "publications.json"
SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "with", "via", "from", "using", "towards"}
KIND = {"journal-article": "Journal", "conference-paper": "Conference", "book": "Book", "book-chapter": "Chapter", "patent": "Patent"}
SPECIAL = {"mas francisco rovira": "F. Rovira-Más", "rovira-mas francisco": "F. Rovira-Más"}
SHOW_PAPERS, SHOW_PATENTS = 10, 5  # shown before "Show more"; the rest are collapsed


def get(path):
    url = f"https://pub.orcid.org/v3.0/{ORCID}/{path}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.URLError:
        # python.org builds on macOS often lack CA certificates; the system curl has them.
        return json.loads(subprocess.run(["curl", "-sfL", "-H", "Accept: application/json", url],
                                         check=True, capture_output=True).stdout)


def fix_title(t):
    t = t.strip().rstrip(".").replace("sprectral", "spectral")
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8:  # ALL-CAPS patent titles
        words = t.lower().split()
        t = " ".join(w if (i and w in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))
        t = re.sub(r"\b(3d|gps|gnss|uav|ai)\b", lambda m: m.group(1).upper(), t, flags=re.I)
        t = re.sub(r"-(\w)", lambda m: "-" + m.group(1).upper(), t)
    return re.sub(r"\bgps\b", "GPS", t)


def cap(w):
    w = "-".join(p[:1].upper() + p[1:].lower() if p.isupper() or p.islower() else p for p in w.split("-"))
    return re.sub(r"O'b", "O'B", w)


def fmt_author(n, patent=False):
    n = n.strip().rstrip(",")
    if n.lower() in SPECIAL:
        return SPECIAL[n.lower()]
    if patent and "," not in n:  # patent records use "Last First Middle"
        parts = n.split()
        return " ".join(p[0].upper() + "." for p in parts[1:]) + " " + cap(parts[0])
    if "," in n:
        last, first = [p.strip() for p in n.split(",", 1)]
    else:
        parts = n.split()
        last, first = parts[-1], " ".join(parts[:-1])
    inits = " ".join(p[0].upper() + "." for p in re.split(r"[\s.\-]+", first) if p)
    return f"{inits} {cap(last)}".strip()


def fetch():
    codes = [str(g["work-summary"][0]["put-code"]) for g in get("works")["group"]]
    works = []
    for i in range(0, len(codes), 50):  # ORCID allows up to 100 works per bulk request
        works += [x["work"] for x in get("works/" + ",".join(codes[i:i + 50]))["bulk"] if "work" in x]

    seen = {}
    for w in works:
        pd = w.get("publication-date") or {}
        year = int(pd["year"]["value"]) if pd.get("year") else None
        if w["type"] == "dissertation-thesis" or (year and year < 1980):
            continue  # the pre-1980 record is a patent by a different John Reid
        title = fix_title(w["title"]["title"]["value"])
        ids = {e["external-id-type"]: e["external-id-value"] for e in ((w.get("external-ids") or {}).get("external-id") or [])}
        authors = []
        for c in ((w.get("contributors") or {}).get("contributor")) or []:
            if not c.get("credit-name"):
                continue
            a = fmt_author(c["credit-name"]["value"], w["type"] == "patent")
            a = {"J. Reid": "J. F. Reid", "F. Rovira-Mas": "F. Rovira-Más"}.get(a, a)
            if a not in authors:
                authors.append(a)
        venue = (w.get("journal-title") or {}).get("value") or ""
        venue = {"NAE PRESS": "The Bridge, National Academy of Engineering",
                 "Springer Handbooks": "Springer Handbook of Robotics"}.get(venue, venue)
        if w["type"] == "patent":
            venue = ids.get("pat", "Patent")
        url = "https://doi.org/" + ids["doi"] if ids.get("doi") else (w.get("url") or {}).get("value", "")
        if "scopus.com" in url:
            url = ""
        kind = KIND.get(w["type"], "Article")
        item = {"year": year, "patent": w["type"] == "patent", "kind": kind, "title": title, "authors": authors, "venue": venue, "url": url}
        # ORCID sometimes lists one work twice; keep the version with a link, preferring journals.
        key = re.sub(r"[^a-z0-9]", "", title.lower())
        score = (bool(url), w["type"] == "journal-article")
        if key not in seen or score > seen[key][0]:
            seen[key] = (score, item)
    items = [item for _, item in seen.values()]
    items.sort(key=lambda i: (-(i["year"] or 0), i["title"]))
    return items


def title_key(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def merge(orcid, extra):
    """ORCID works plus lab-added ones. A paper in both keeps the ORCID version unless only the other has a link."""
    seen = {}
    for p in orcid + [dict(p, patent=p["kind"] == "Patent") for p in extra]:
        key = title_key(p["title"])
        score = (bool(p["url"]), p["kind"] == "Journal")
        if key not in seen or score > seen[key][0]:
            seen[key] = (score, p)
    items = [p for _, p in seen.values()]
    items.sort(key=lambda i: (-(i["year"] or 0), i["title"]))
    return items


def load(offline):
    if offline:
        orcid = json.loads(CACHE.read_text())
    else:
        orcid = fetch()
        CACHE.write_text(json.dumps(orcid, indent=1, ensure_ascii=False) + "\n")
    extra = json.loads(EXTRA.read_text()) if EXTRA.exists() else []
    return merge(orcid, extra), len(extra)


def entry(p, indent):
    e = html.escape
    pad = " " * indent
    authors = ", ".join(f"<strong>{e(a)}</strong>" if a.endswith(" Reid") else e(a) for a in p["authors"])
    title = f'<a class="pub-title" href="{e(p["url"])}">{e(p["title"])}</a>' if p["url"] else f'<span class="pub-title">{e(p["title"])}</span>'
    venue = e(p["venue"]) if p["patent"] else (f"<em>{e(p['venue'])}</em>" if p["venue"] else "")
    venue = f"{venue}, {p['year']}" if venue else str(p["year"])
    return "\n".join([
        f'{pad}<li class="pub">',
        f'{pad}  <span class="pub-type">{p["kind"]}</span>',
        f'{pad}  <div>',
        f'{pad}    {title}',
        f'{pad}    <div class="pub-authors">{authors}</div>',
        f'{pad}    <div class="pub-venue">{venue}</div>',
        f'{pad}  </div>',
        f'{pad}</li>',
    ])


def listing(works, shown, noun):
    """The newest `shown` works, then the rest inside a "Show more" toggle."""
    out = ['      <ol class="pub-list">'] + [entry(p, 8) for p in works[:shown]] + ["      </ol>"]
    rest = works[shown:]
    if rest:
        out += [
            '      <details class="pub-more">',
            f'        <summary><span class="when-closed">Show {len(rest)} more {noun}</span><span class="when-open">Show fewer {noun}</span></summary>',
            '        <ol class="pub-list">',
        ]
        out += [entry(p, 10) for p in rest]
        out += ["        </ol>", "      </details>"]
    return out


def render(items, added=0):
    papers = [p for p in items if not p["patent"]]
    patents = [p for p in items if p["patent"]]
    lo = min(p["year"] for p in items)
    hi = max(p["year"] for p in items)
    source = f'Dr. Reid\'s public <a href="https://orcid.org/{ORCID}">ORCID record</a>'
    if added:
        source += " and papers added by lab members"
    out = [
        f'      <p class="pub-summary">{len(papers)} papers and <a href="#patents">{len(patents)} patents</a>, {lo}–{hi}. '
        f'Source: {source}.</p>',
        "",
        '      <h2 id="papers">Papers</h2>',
    ]
    out += listing(papers, SHOW_PAPERS, "papers")
    out += ["", '      <h2 id="patents">Patents</h2>']
    out += listing(patents, SHOW_PATENTS, "patents")
    return "\n".join(out)


def rebuild(offline=True):
    items, added = load(offline)
    page = PAGE.read_text()
    begin = re.search(r"<!-- BEGIN PUBLICATIONS[^>]*-->\n", page)
    end = page.index("<!-- END PUBLICATIONS -->")
    end = page.rindex("\n", 0, end) + 1
    PAGE.write_text(page[:begin.end()] + render(items, added) + "\n" + page[end:])
    return items


if __name__ == "__main__":
    items = rebuild(offline="--offline" in sys.argv[1:])
    print(f"Wrote {len(items)} entries to {PAGE.name}")
