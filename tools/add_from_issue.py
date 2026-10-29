#!/usr/bin/env python3
"""Apply an "Add to the website" GitHub issue form to the site.

Run by .github/workflows/site-forms.yml with the issue text in $ISSUE_BODY. Works out which
form was used (new member, alumni, or publication), checks the answers, saves the entry in
data/, and rebuilds people.html or publications.html. Issues that aren't one of the forms
are left alone.

To try it locally:  ISSUE_BODY="$(cat issue.md)" python3 tools/add_from_issue.py

If an answer needs fixing, it exits with an error and writes the message to $FORM_ERROR_FILE,
which the workflow posts on the issue. The form field labels below must match the labels in
.github/ISSUE_TEMPLATE/, because that's how GitHub writes the answers into the issue.
"""
import json, os, re, sys
from pathlib import Path

import update_people
import update_publications

ROOT = Path(__file__).resolve().parent.parent
PUBLICATIONS = ROOT / "data" / "publications.json"
ABOUT_MAX = 170  # about three lines on a People card
KINDS = ["Journal", "Conference", "Chapter", "Book", "Article", "Patent"]


class FormError(Exception):
    pass


def parse(body):
    """GitHub writes each answer under a '### <field label>' heading."""
    fields = {}
    for m in re.finditer(r"^### (.+?)[ \t]*\n(.*?)(?=^### |\Z)", body.replace("\r\n", "\n"), re.S | re.M):
        value = m.group(2).strip()
        fields[m.group(1).strip()] = "" if value == "_No response_" else value
    return fields


def one_line(fields, label, errors, required=False, limit=120):
    value = " ".join(fields.get(label, "").split())
    if required and not value:
        errors.append(f"**{label}** is required.")
    elif len(value) > limit:
        errors.append(f"**{label}** is {len(value)} characters; please keep it under {limit}.")
    return value


def about(fields, errors):
    value = " ".join(fields.get("About you", "").split())
    if len(value) > ABOUT_MAX:
        errors.append(f"**About you** is {len(value)} characters. Cards fit about three lines, so please keep it under {ABOUT_MAX}.")
    return value


def email(fields, errors):
    value = one_line(fields, "Email", errors)
    if value and not re.fullmatch(r"[^@\s<>\"']+@[^@\s<>\"']+\.[A-Za-z]{2,}", value):
        errors.append("**Email** doesn't look like an email address.")
    return value


def link(fields, label, errors):
    value = one_line(fields, label, errors, limit=300)
    if re.fullmatch(r"10\.\d{4,9}/\S+", value):  # a bare DOI
        value = "https://doi.org/" + value
    if value and not re.fullmatch(r"https?://[^\s<>\"']+", value):
        errors.append(f"**{label}** should be a full link starting with https://")
    return value


def year(fields, label, errors, required=False):
    value = one_line(fields, label, errors, required=required)
    if value and not (re.fullmatch(r"\d{4}", value) and 1980 <= int(value) <= 2100):
        errors.append(f"**{label}** should be a four-digit year.")
    return int(value) if value and not errors else value


def same_name(a, b):
    return " ".join(a.lower().split()) == " ".join(b.lower().split())


def upsert(people, person, front=False):
    """Replace the entry with this name, or add it (to the end, or the front for alumni)."""
    for i, p in enumerate(people):
        if same_name(p["name"], person["name"]):
            people[i] = dict(p, **person)
            return
    people.insert(0 if front else len(people), person)


def add_member(fields):
    errors = []
    person = {
        "name": one_line(fields, "Full name", errors, required=True, limit=80),
        "program": one_line(fields, "Program", errors, required=True, limit=80),
        "about": about(fields, errors),
        "email": email(fields, errors),
        "website": link(fields, "Website or LinkedIn", errors),
    }
    if errors:
        raise FormError(errors)
    members = update_people.load(update_people.MEMBERS)
    upsert(members, person)
    update_people.save(update_people.MEMBERS, members)
    update_people.rebuild()
    return person["name"]


def add_alumni(fields):
    errors = []
    person = {
        "name": one_line(fields, "Full name", errors, required=True, limit=80),
        "program": one_line(fields, "Degree and program", errors, limit=80),
        "year": year(fields, "Year graduated", errors),
        "about": about(fields, errors),
        "email": email(fields, errors),
        "website": link(fields, "Website or LinkedIn", errors),
    }
    if errors:
        raise FormError(errors)
    alumni = update_people.load(update_people.ALUMNI)
    upsert(alumni, person, front=True)
    update_people.save(update_people.ALUMNI, alumni)
    # Someone who graduates moves from Graduate students to Alumni.
    members = update_people.load(update_people.MEMBERS)
    update_people.save(update_people.MEMBERS, [p for p in members if not same_name(p["name"], person["name"])])
    update_people.rebuild()
    return person["name"]


def add_publication(fields):
    errors = []
    kind = fields.get("Type", "").strip()
    authors = [a.strip() for a in re.split(r",|;|\band\b", one_line(fields, "Authors", errors, required=True, limit=600)) if a.strip()]
    paper = {
        "year": year(fields, "Year", errors, required=True),
        "kind": kind,
        "title": one_line(fields, "Title", errors, required=True, limit=300).rstrip("."),
        "authors": authors,
        "venue": one_line(fields, "Venue", errors, required=True, limit=200),
        "url": link(fields, "Link", errors),
    }
    if kind not in KINDS:
        errors.append(f"**Type** should be one of: {', '.join(KINDS)}.")
    if errors:
        raise FormError(errors)
    extra = json.loads(PUBLICATIONS.read_text()) if PUBLICATIONS.exists() else []
    key = update_publications.title_key(paper["title"])
    extra = [p for p in extra if update_publications.title_key(p["title"]) != key] + [paper]
    PUBLICATIONS.write_text(json.dumps(extra, indent=2, ensure_ascii=False) + "\n")
    update_publications.rebuild(offline=True)
    return paper["title"][:80]


FORMS = [  # (kind, a field label only that form has, handler)
    ("alumni", "Year graduated", add_alumni),
    ("member", "Program", add_member),
    ("publication", "Authors", add_publication),
]


def main():
    fields = parse(os.environ.get("ISSUE_BODY", ""))
    form = next((f for f in FORMS if f[1] in fields), None)
    if not form:
        print("Not a website form; nothing to do.")
        return
    kind, _, handler = form
    try:
        label = handler(fields)
    except FormError as err:
        message = "Thanks! A few answers need fixing before this can be added to the website:\n\n"
        message += "\n".join(f"- {e}" for e in err.args[0])
        message += "\n\nEdit the issue to fix them, and the site update will be prepared again."
        if os.environ.get("FORM_ERROR_FILE"):
            Path(os.environ["FORM_ERROR_FILE"]).write_text(message + "\n")
        sys.exit(message)
    print(f"Added {kind}: {label}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"kind={kind}\nlabel={label}\n")


if __name__ == "__main__":
    main()
