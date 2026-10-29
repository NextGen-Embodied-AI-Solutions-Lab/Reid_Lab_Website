# Reid Lab website

A static website made of plain HTML pages and one stylesheet, with no JavaScript, so it can be hosted anywhere. The People and Publications lists are built from data files by small Python scripts (standard library only), and GitHub forms let lab members add themselves, alumni, and papers.

## View it

Double-click `index.html`, or serve the folder:

```sh
python3 -m http.server 8000
# then open http://localhost:8000
```

## Pages

| File | Content |
| --- | --- |
| `index.html` | Photo banner, about, latest news, selected publications, prospective students |
| `research.html` | Six research areas, each with a short description and selected papers |
| `projects.html` | Student projects (BlueBoat, Amiga, CERL) and a link to the lab's GitHub |
| `people.html` | PI profile (titles, email, links, current course), graduate students, and alumni (lists generated, see below) |
| `publications.html` | Papers and patents (generated, see below) |
| `news.html` | All news items |
| `contact.html` | Office, phone, email, map |
| `credits.html` | Photo credits and licenses |
| `css/style.css` | All styling. Colors and fonts are variables at the top. |
| `data/` | Graduate students, alumni, and publications, as JSON |
| `tools/` | Scripts that rebuild the generated lists |
| `.github/` | The website forms and the workflow that applies them |

Every page repeats the same header and footer. If you add a page or rename a menu item, update the header on every page.

## Website forms

Lab members add things to the site by filling in a form on GitHub: **New issue** in the site's repository, then one of:

- **Add yourself to the website:** a new member's card under Graduate students (name, program, up to 3 lines about them, email, and a website or LinkedIn link for their name).
- **Add an alumnus:** a card under Alumni. If the person is listed under Graduate students, the card moves.
- **Add a publication:** a paper or patent that isn't on Dr. Reid's ORCID record.

Submitting a form runs `.github/workflows/site-forms.yml`. It checks the answers, adds the entry to `data/`, rebuilds the page, and opens a pull request. **A site maintainer reviews and merges the pull request, and the site updates.** If an answer needs fixing (a description longer than 3 lines, or a broken link or email), the workflow comments on the issue instead, and editing the issue tries again. Submitting the member form again with the same name updates that card.

The review step matters because anyone with a GitHub account can open an issue on a public repository.

### One-time setup

The site lives in [NextGen-Embodied-AI-Solutions-Lab/Reid_Lab_Website](https://github.com/NextGen-Embodied-AI-Solutions-Lab/Reid_Lab_Website).

1. In the repository, open *Settings → Actions → General* and check that, under *Workflow permissions*, **Allow GitHub Actions to create and approve pull requests** is ticked.
2. On GitHub's free plan, Pages only works for public repositories. If the repository is private, make it public under *Settings → General → Danger Zone → Change visibility*.
3. Turn on GitHub Pages under *Settings → Pages*: *Deploy from a branch*, branch `main`, folder `/ (root)`. The site appears at https://nextgen-embodied-ai-solutions-lab.github.io/Reid_Lab_Website/ within a few minutes, and merged pull requests go live a minute or two after merging.
4. Optionally, add a "Lab members: add yourself" link to the People page pointing to https://github.com/NextGen-Embodied-AI-Solutions-Lab/Reid_Lab_Website/issues/new/choose.

The form questions are in `.github/ISSUE_TEMPLATE/`. If you rename a question, update the matching label in `tools/add_from_issue.py`, because that's how the script finds each answer.

## Editing by hand

- **People:** edit `data/members.json` or `data/alumni.json`, then run `python3 tools/update_people.py`. Don't edit the lists in `people.html` directly; they're rebuilt from the data files. For a photo, put it in `assets/people/` and add `"photo": "assets/people/name.jpg"` to the person's entry.
- **News:** add an `<li>` at the top of the list in `news.html`, and in the News section of `index.html` (the home page shows the latest four).
- **Research text:** edit `research.html`.
- **Student projects:** add an `<article class="project">` in `projects.html`. The descriptions summarize each project's README in the [lab's GitHub organization](https://github.com/NextGen-Embodied-AI-Solutions-Lab). Those repositories are private, so the page doesn't link to them.
- **Teaching:** the course and syllabus links under Dr. Reid's profile in `people.html` point to Fall 2026. Update them each semester.
- **Prospective students:** the text is in the `#join` section near the bottom of `index.html`. It's a draft for Dr. Reid to review.
- **Banner photo:** replace `assets/images/home-cornfield.jpg`, then update the caption on the home page and `credits.html`.

## Publications

The list combines Dr. Reid's public ORCID record (0000-0001-5286-8555) with papers added through the form (`data/publications.json`). To pull the latest from ORCID:

```sh
python3 tools/update_publications.py            # fetch ORCID, save it to data/orcid-works.json, rebuild
python3 tools/update_publications.py --offline  # rebuild from the saved copy (what the form workflow does)
```

This rewrites the part of `publications.html` between the `BEGIN PUBLICATIONS` and `END PUBLICATIONS` comments, so don't hand-edit inside it. The script tidies titles and author names, labels each entry by type, removes duplicates (including a paper that's both on ORCID and added by hand), and skips one record that ORCID wrongly attributes to Dr. Reid (a 1920 patent by a different John Reid).

The page shows the 10 newest papers and the 5 newest patents, with the rest behind a "Show more" button. To change those numbers, edit `SHOW_PAPERS` and `SHOW_PATENTS` at the top of the script.

## Photos and fonts

Fonts are Source Serif 4 (headings) and Source Sans 3 (text), loaded from Google Fonts.

Dr. Reid's headshot (`assets/people/john-reid.jpg`) is the public one from the AIFARMS team page. Check that Dr. Reid is happy with it, or swap in a preferred photo.

The home-page banner photo comes from Wikimedia Commons under a Creative Commons license, which allows reuse with credit. It's credited on `credits.html` and in its caption, so keep both if you keep the photo. Photos of the lab's own robots, field trials, and team will make the site feel more real, so swap them in as you take them.

## Publish it

- **GitHub Pages:** see *One-time setup* above.
- **Netlify or Cloudflare Pages:** connect the GitHub repository (a private one works too) and leave the build command empty. The site then redeploys whenever `main` changes, so the forms keep working.
- **A custom domain:** all of these support one.

## Sources

Facts about Dr. Reid come from public pages: Dr. Reid's [Center for Autonomy profile](https://autonomy.illinois.edu/people/John-Reid), the [Center for Digital Agriculture announcement](https://www.newswise.com/articles/new-leadership-to-take-illinois-center-for-digital-agriculture-into-the-future), the [ASABE 2026 Gold Medal announcement](https://asabe.org/news-detail/three-honored-with-asabe-gold-medal-awards), the [Virginia Tech alumni profile](https://eng.vt.edu/about/distinguished-alumni/academy-of-engineering-excellence/john-f-reid.html), and [ORCID](https://orcid.org/0000-0001-5286-8555). The alumni list and Amey Gavale's program come from the lab's earlier website. The "About the lab" text and the research descriptions are drafts based on Dr. Reid's stated interests, so Dr. Reid should review them.
