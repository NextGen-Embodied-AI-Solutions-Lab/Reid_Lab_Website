#!/usr/bin/env python3
"""Rebuild the Graduate students and Alumni lists in people.html from the data folder.

Usage (from the project folder):  python3 tools/update_people.py
Reads data/members.json and data/alumni.json, and rewrites everything between the
BEGIN/END MEMBERS and BEGIN/END ALUMNI markers in people.html.

Each person is an object with "name", "program", "about" (up to 3 lines), "email" and
"website" (their name links there). Alumni also have "year". An optional "photo"
(e.g. "assets/people/jane-doe.jpg") replaces the initials.
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "people.html"
MEMBERS = ROOT / "data" / "members.json"
ALUMNI = ROOT / "data" / "alumni.json"


def load(path):
    return json.loads(path.read_text()) if path.exists() else []


def save(path, people):
    path.write_text(json.dumps(people, indent=2, ensure_ascii=False) + "\n")


def initials(name):
    words = name.split()
    if len(words) == 1:
        words = name.split("-")  # e.g. "Chu-Lin"
    return (words[0][:1] + (words[-1][:1] if len(words) > 1 else "")).upper()


def card(p, alumni):
    e = html.escape
    name = e(p["name"])
    if p.get("website"):
        name = f'<a href="{e(p["website"])}">{name}</a>'
    role = p.get("program", "")
    if alumni and p.get("year"):
        role = f'{role}, {p["year"]}' if role else str(p["year"])
    if p.get("photo"):
        avatar = f'<img class="avatar" src="{e(p["photo"])}" alt="">'
    else:
        avatar = f'<span class="avatar" aria-hidden="true">{e(initials(p["name"]))}</span>'
    out = ['          <li class="member">', f"            {avatar}", "            <div>", f"              <h3>{name}</h3>"]
    if role:
        out.append(f'              <p class="member-role">{e(role)}</p>')
    if p.get("about"):
        out.append(f'              <p class="member-bio">{e(p["about"])}</p>')
    if p.get("email"):
        out.append(f'              <p class="member-email"><a href="mailto:{e(p["email"])}">{e(p["email"])}</a></p>')
    out += ["            </div>", "          </li>"]
    return "\n".join(out)


def listing(people, alumni):
    if not people:
        return '        <p class="muted">No one listed yet.</p>'
    return "\n".join(['        <ul class="members">'] + [card(p, alumni) for p in people] + ["        </ul>"])


def replace_between(page, tag, body):
    pattern = re.compile(rf"(<!-- BEGIN {tag}[^>]*-->\n)(?:.*?\n)?([ \t]*<!-- END {tag} -->)", re.S)
    page, count = pattern.subn(lambda m: m.group(1) + body + "\n" + m.group(2), page)
    if count != 1:
        raise SystemExit(f"{PAGE.name}: expected one BEGIN/END {tag} pair")
    return page


def rebuild():
    page = PAGE.read_text()
    page = replace_between(page, "MEMBERS", listing(load(MEMBERS), alumni=False))
    page = replace_between(page, "ALUMNI", listing(load(ALUMNI), alumni=True))
    PAGE.write_text(page)


if __name__ == "__main__":
    rebuild()
    print(f"Wrote {len(load(MEMBERS))} members and {len(load(ALUMNI))} alumni to {PAGE.name}")
