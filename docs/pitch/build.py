"""Assemble docs/pitch/index.html from deck.json and slides/*.html (stdlib only).

  python3 docs/pitch/build.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The claude.ai copy of the deck serves the diagram as an uploaded asset;
# the offline page points at the repo file instead.
ASSETS = {"/_blob/c40c21b89f211adb32e5ac281eaf5e47": "assets/diagram.png"}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{fonts}">
<style>
  * {{ margin: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; background: #0B1222; overflow: hidden; }}
  #stage {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 0; }}
  section {{ position: absolute !important; inset: 0; width: 1920px; height: 1080px; }}
  section:not(.on) {{ display: none !important; }}
  h1, h2, h3, p {{ font-weight: inherit; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 0.35em 0.6em; border-bottom: 1px solid #DAD7CC; text-align: left; }}
  th {{ font-weight: 600; }}
  aside {{ display: none; }}
  body.notes aside {{ display: block; position: absolute; left: 0; right: 0; bottom: 0;
    padding: 24px 128px; font: 26px/1.4 'IBM Plex Sans', Arial, sans-serif;
    background: rgba(11, 18, 34, 0.92); color: #F7F6F1; }}
  #count {{ position: fixed; right: 16px; bottom: 12px; font: 14px monospace; color: #8E9BB5; }}
  @page {{ size: 1920px 1080px; margin: 0; }}
  @media print {{
    html, body {{ height: auto; overflow: visible; background: none; }}
    #stage {{ position: static; transform: none !important; width: 1920px; height: auto; }}
    section {{ position: relative !important; display: flex !important; break-after: page; overflow: hidden; }}
    section:not(.on) {{ display: flex !important; }}
    aside, #count, body.notes aside {{ display: none !important; }}
    * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
<div id="stage">
{slides}
</div>
<div id="count"></div>
<script>
  const slides = [...document.querySelectorAll('section')];
  const stage = document.getElementById('stage');
  let i = Math.max(0, slides.findIndex(s => '#' + s.id === location.hash));
  function show(n) {{
    i = Math.min(slides.length - 1, Math.max(0, n));
    slides.forEach((s, k) => s.classList.toggle('on', k === i));
    history.replaceState(null, '', '#' + slides[i].id);
    document.getElementById('count').textContent = (i + 1) + ' / ' + slides.length + '  ·  N notes';
  }}
  function fit() {{
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `translate(${{(innerWidth - 1920 * s) / 2}}px, ${{(innerHeight - 1080 * s) / 2}}px) scale(${{s}})`;
  }}
  addEventListener('keydown', e => {{
    if (['ArrowRight', 'PageDown', ' '].includes(e.key)) show(i + 1);
    else if (['ArrowLeft', 'PageUp'].includes(e.key)) show(i - 1);
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(slides.length - 1);
    else if (e.key.toLowerCase() === 'n') document.body.classList.toggle('notes');
    else if (e.key.toLowerCase() === 'f') document.documentElement.requestFullscreen?.();
  }});
  addEventListener('click', e => show(i + (e.clientX > innerWidth / 3 ? 1 : -1)));
  addEventListener('resize', fit);
  fit(); show(i);
</script>
</body>
</html>
"""


def build() -> str:
    deck = json.loads((HERE / "deck.json").read_text(encoding="utf-8"))
    faces = deck.get("faces", {})
    fonts = next((f["href"] for f in faces.values() if "href" in f), "")
    parts = []
    for slide_id in deck["order"]:
        html = (HERE / "slides" / f"{slide_id}.html").read_text(encoding="utf-8").strip()
        for blob, path in ASSETS.items():
            html = html.replace(blob, path)
        parts.append(html)
    return PAGE.format(title=deck["title"], fonts=fonts, slides="\n".join(parts))


if __name__ == "__main__":
    out = HERE / "index.html"
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out.relative_to(HERE.parent.parent)}")
