# Pitch deck

Four slides for Kevin's confirmed **2-minute** demo-day slot: Cover, Architecture,
Incident as data, Results. Timing and spoken text: `docs/process/PITCH_SCRIPT.md`.
Other slide sources remain available, but are not in the presentation order.
No account is needed. Slides work without network access using fallback fonts;
the preferred fonts load from Google Fonts when connected.

## Present

Open `index.html` in a browser (double-click, or serve the repo root so the diagram loads:
`python3 -m http.server 8000` then http://127.0.0.1:8000/docs/pitch/).

| Key | Does |
|---|---|
| → / Space / click right | Next slide |
| ← / click left | Previous slide |
| N | Show or hide speaker notes |
| F | Full screen |

The URL hash keeps the current slide (`index.html#results`).

## Edit

1. Edit a slide in `slides/<id>.html`. Each file is one `<section>` with inline styles only.
2. Change slide order or the title in `deck.json` (`order`, `title`).
3. Run `python3 docs/pitch/build.py` to regenerate `index.html`. Do not edit `index.html` by hand.

`assets/diagram.png` is a byte-identical copy of the frozen `site/diagram.png`, so the deck works on GitHub Pages. `rubrica-pitch.pdf` is printed from `index.html` with headless Chrome (one slide per 1920×1080 page).

## Before presenting

- The Results slide shows **run #2: 91/100, median 510 ms**, confirmed by Kevin on
  `/evento/resultados` and recorded in the main checkout's `docs/process/WORKFLOW.md`.
  This is the last confirmed validation, not the final post-20:00 evaluation.
  After run #3, update the slide and both scripts only when its ledger row exists.
- Keep claims consistent with `SPEC.md` and `docs/process/INCIDENT.md`: the lockout is *probable*.
- Use the **main checkout** for current facts. This worktree's SPEC, code and ledger
  are older snapshots. SPEC/log upload remains blocked until Pi reports the freeze
  and the main verifier passes with a matching log line count.

## Other copies

The same slides are published as a private claude.ai Slides deck, which can export .pptx and
PDF. The files here are the copy that needs no account. In `slides/architecture.html` the image
`src` is the claude.ai asset URL; `build.py` rewrites it to `assets/diagram.png`.
