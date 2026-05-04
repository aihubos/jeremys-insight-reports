#!/usr/bin/env python3
"""Render an Obsidian report Markdown file to GitHub Pages HTML without rewriting content.

Invariant: the GitHub Pages report body must be a structural HTML rendering of the
Obsidian Markdown body. Do not summarize, delete, or paraphrase report text here.
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
ASSETS = DOCS / "assets"
REPORTS = DOCS / "reports"


def strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\n.*?\n---\n\n?", "", text, flags=re.S)


def frontmatter_value(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\n\"']+)[\"']?\s*$", text, re.M)
    return m.group(1).strip() if m else None


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # Plain URLs
    s = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', s)
    return s


def render_markdown_body(md_body: str) -> tuple[str, list[str], str]:
    lines = md_body.splitlines()
    out: list[str] = []
    assets: list[str] = []
    title = "Report"
    i = 0
    in_key_takeaway = False
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("# "):
            title = line[2:].strip()
            out.append(f"<h1>{inline(title)}</h1>")
            i += 1
            continue
        if line.startswith("## "):
            heading = line[3:].strip()
            in_key_takeaway = heading == "핵심 결론"
            cls = ' class="key-heading"' if in_key_takeaway else ""
            out.append(f"<h2{cls}>{inline(heading)}</h2>")
            i += 1
            continue
        if line.startswith("### "):
            in_key_takeaway = False
            out.append(f"<h3>{inline(line[4:].strip())}</h3>")
            i += 1
            continue
        m = re.match(r"!\[\[(?:300_Resources/390_Assets|assets)/(.+?)\]\]", line.strip())
        if m:
            name = m.group(1)
            assets.append(name)
            out.append(f'<img class="hero" src="../../assets/{html.escape(name)}" alt="report infographic">')
            i += 1
            continue
        if line.startswith("|"):
            table: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                table.append(lines[i])
                i += 1
            rows: list[list[str]] = []
            for r in table:
                cells = [c.strip() for c in r.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    continue
                rows.append(cells)
            if rows:
                out.append("<table>")
                for idx, cells in enumerate(rows):
                    tag = "th" if idx == 0 else "td"
                    out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
                out.append("</table>")
            continue
        if line.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:].strip())
                i += 1
            cls = ' class="key-takeaways"' if in_key_takeaway else ""
            out.append(f"<ul{cls}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s+", line):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i]).strip())
                i += 1
            cls = ' class="key-takeaways"' if in_key_takeaway else ""
            out.append(f"<ol{cls}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue
        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue

        ps: list[str] = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith(("#", "|", "- ", "![["))
            and lines[i].strip() != "---"
        ):
            ps.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(ps))}</p>")
    return "\n".join(out), assets, title


CSS = """
body{margin:0;background:linear-gradient(180deg,#07111f,#102543 24%,#f7f9fc 24%);color:#1d1d1f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.75}
.wrap{max-width:1080px;margin:0 auto;padding:64px 24px 80px}
main{background:#fff;border-radius:28px;padding:42px 34px 48px;box-shadow:0 18px 60px rgba(15,39,80,.10)}
h1{font-size:42px;letter-spacing:-.04em;line-height:1.15;margin:0 0 16px;color:#111827}
main h1:first-child{color:#fff;background:#102543;margin:-42px -34px 24px;padding:42px 34px 12px;border-radius:28px 28px 0 0}
h2{font-size:25px;margin:46px 0 14px;color:#1455a6}h3{font-size:21px;margin:30px 0 10px;color:#1f3f7a}
.hero{width:100%;border-radius:28px;box-shadow:0 24px 70px rgba(0,20,60,.28);margin:28px 0 24px}
table{width:100%;border-collapse:separate;border-spacing:0;border:1px solid #dfe7f2;border-radius:18px;overflow:hidden;background:white;margin:18px 0}
th{background:#edf5ff;color:#0b3d91;text-align:left}td,th{padding:13px 15px;border-bottom:1px solid #edf1f7;vertical-align:top}tr:last-child td{border-bottom:0}
ul,ol{background:#fff;border:1px solid #dfe7f2;border-radius:18px;padding:18px 24px 18px 42px}li{margin:8px 0}
.key-heading{font-size:31px;color:#0b3d91}.key-takeaways{background:#edf5ff;border:2px solid #bfd7ff;box-shadow:0 14px 36px rgba(15,39,80,.10);font-size:22px;font-weight:800;line-height:1.65}.key-takeaways li{margin:12px 0}
hr{border:0;border-top:1px solid #dfe7f2;margin:42px 0 20px}a{color:#0b63ce;font-weight:700}code{background:#edf5ff;padding:2px 6px;border-radius:6px}
""".strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("md_path", type=Path)
    ap.add_argument("--slug", help="Report slug. Defaults to slug inferred from published_url frontmatter.")
    ap.add_argument("--obsidian-root", type=Path, default=Path("/Users/openclaw_bot/Obsidian/Jeremy's Vault"))
    args = ap.parse_args()

    raw = args.md_path.read_text(encoding="utf-8")
    url = frontmatter_value(raw, "published_url")
    slug = args.slug
    if not slug and url:
        m = re.search(r"/reports/([^/]+)/?", url)
        if m:
            slug = m.group(1)
    if not slug:
        raise SystemExit("--slug is required when published_url is absent")

    body_md = strip_frontmatter(raw)
    content, asset_names, title = render_markdown_body(body_md)

    ASSETS.mkdir(parents=True, exist_ok=True)
    for name in asset_names:
        candidates = [
            args.obsidian_root / "300_Resources" / "390_Assets" / name,
            args.obsidian_root / "000_Inbox" / "assets" / name,
            args.obsidian_root / "assets" / name,
        ]
        for src in candidates:
            if src.exists():
                (ASSETS / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, ASSETS / name)
                break

    out_dir = REPORTS / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="wrap"><main>{content}</main></div></body></html>'
    (out_dir / "index.html").write_text(doc, encoding="utf-8")
    print(out_dir / "index.html")


if __name__ == "__main__":
    main()
