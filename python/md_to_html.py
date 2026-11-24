"""Convert the project's Markdown documents to standalone HTML for index.htm.

Run from the repo root:  python python/md_to_html.py

Writes <name>.html next to every converted <name>.md, so relative links inside
the documents keep working.  Links to another converted .md are rewritten to
its .html.  Standard library only: it handles the subset of Markdown these
documents use (headings, paragraphs, nested lists, tables, code fences,
blockquotes, rules, **bold**, *italic*, `code`, [links](url), YAML front matter).
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["README.md", "product/README.md", "skills/return-distribution-check/SKILL.md",
           *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").glob("*.md"))]

CJK = re.compile(r"[⺀-鿿豈-﫿＀-￯]")

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#5c5c5c;--line:#e3e3e3;--soft:#f6f6f4;--accent:#c86400}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#e8e8e8;--muted:#a0a0a0;--line:#2e2e2e;--soft:#1d1d1d;--accent:#ff9a3c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 "Noto Sans TC","Microsoft JhengHei","PingFang TC",system-ui,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:0 16px 48px}
.top{border-bottom:1px solid var(--line);padding:14px 0;margin-bottom:8px;font-size:14px;color:var(--muted);display:flex;gap:12px;flex-wrap:wrap}
a{color:var(--accent)}
h1{font-size:28px;line-height:1.35;margin:24px 0 12px}
h2{font-size:22px;margin:32px 0 10px;padding-bottom:4px;border-bottom:1px solid var(--line)}
h3{font-size:18px;margin:24px 0 8px}
h4,h5,h6{font-size:16px;margin:18px 0 6px}
p{margin:0 0 12px}
ul,ol{padding-left:24px;margin:0 0 12px}
li{margin-bottom:4px}
code{background:var(--soft);padding:1px 5px;border-radius:3px;font-size:14px;font-family:Consolas,"Courier New",monospace}
pre{background:var(--soft);padding:12px 14px;border-radius:4px;overflow-x:auto}
pre code{padding:0;background:none}
blockquote{margin:0 0 12px;padding:8px 14px;border-left:4px solid var(--accent);background:var(--soft);color:var(--muted)}
blockquote p:last-child{margin-bottom:0}
.tbl{overflow-x:auto;margin:0 0 14px}
table{border-collapse:collapse;font-size:15px;width:100%}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--soft)}
hr{border:0;border-top:1px solid var(--line);margin:24px 0}
.meta{font-size:14px;color:var(--muted)}
"""


def inline(text: str, link_map) -> str:
    codes = []

    def keep_code(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", keep_code, text)
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", t)

    def link(m):
        label, url = m.group(1), m.group(2)
        return f'<a href="{html.escape(link_map(url))}">{label}</a>'

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))])}</code>", t)


def join_lines(lines):
    out = ""
    for ln in lines:
        ln = ln.strip()
        if out and not (CJK.search(out[-1]) and CJK.search(ln[:1])):
            out += " "
        out += ln
    return out


LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def render_list(lines, il):
    """lines: raw lines of one list block (items, nested items, continuations)."""
    items = []  # (indent, ordered, [text lines], [child raw lines])
    base = None
    for ln in lines:
        m = LIST_RE.match(ln)
        ind = len(ln) - len(ln.lstrip(" "))
        if m and (base is None or ind <= base):
            base = ind if base is None else base
            items.append([m.group(2)[0].isdigit(), [m.group(3)], []])
        elif m:
            items[-1][2].append(ln)
        elif items[-1][2]:
            items[-1][2].append(ln)
        else:
            items[-1][1].append(ln)
    ordered = items[0][0]
    tag = "ol" if ordered else "ul"
    start = ""
    if ordered:
        n = int(re.match(r"\s*(\d+)", lines[0]).group(1))
        start = f' start="{n}"' if n != 1 else ""
    out = [f"<{tag}{start}>"]
    for _, text, child in items:
        body = il(join_lines(text))
        if child:
            body += render_list(child, il)
        out.append(f"<li>{body}</li>")
    out.append(f"</{tag}>")
    return "".join(out)


def split_row(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    cells, cur, in_code = [], "", False
    for ch in row:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
    cells.append(cur.strip())
    return cells


def convert(md: str, link_map):
    il = lambda s: inline(s, link_map)  # noqa: E731
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, front = [], 0, None
    if lines and lines[0].strip() == "---":
        j = lines.index("---", 1)
        front = [ln.split(":", 1) for ln in lines[1:j] if ":" in ln]
        i = j + 1
    if front:
        out.append('<div class="tbl"><table>' + "".join(
            f"<tr><th>{html.escape(k.strip())}</th><td>{html.escape(v.strip())}</td></tr>" for k, v in front)
            + "</table></div>")
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            n = len(m.group(1))
            out.append(f"<h{n}>{il(m.group(2).rstrip('#').strip())}</h{n}>")
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            out.append("<hr>")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            head = split_row(s)
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            t = "<thead><tr>" + "".join(f"<th>{il(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{il(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody>"
            out.append(f'<div class="tbl"><table>{t}</table></div>')
            i = j
            continue
        if s.startswith(">"):
            j = i
            block = []
            while j < len(lines) and lines[j].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[j]))
                j += 1
            out.append("<blockquote>" + convert("\n".join(block), link_map) + "</blockquote>")
            i = j
            continue
        if LIST_RE.match(ln):
            j = i + 1
            while j < len(lines) and lines[j].strip() and (
                    LIST_RE.match(lines[j]) or lines[j].startswith(" ")):
                j += 1
            out.append(render_list(lines[i:j], il))
            i = j
            continue
        j = i
        para = []
        while j < len(lines) and lines[j].strip() and not re.match(r"^(#{1,6}\s|```|\||>)", lines[j].strip()) \
                and not (j > i and LIST_RE.match(lines[j])):
            para.append(lines[j])
            j += 1
        out.append(f"<p>{il(join_lines(para))}</p>")
        i = j
    return "\n".join(out)


def main():
    converted = {Path(s).as_posix() for s in SOURCES}
    for src in SOURCES:
        path = ROOT / src
        here = path.parent

        def link_map(url, here=here):
            if re.match(r"^[a-z]+:", url) or url.startswith("#"):
                return url
            target, _, frag = url.partition("#")
            try:
                rel = (here / target).resolve().relative_to(ROOT).as_posix()
            except ValueError:
                return url
            if rel in converted:
                target = target[:-3] + ".html"
            return target + (("#" + frag) if frag else "")

        md = path.read_text(encoding="utf-8")
        body = convert(md, link_map)
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = re.sub(r"[`*]", "", m.group(1)) if m else path.stem
        home = Path(*[".."] * len(Path(src).parent.parts), "index.htm").as_posix()
        page = (f'<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
                f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
                f'<div class="wrap">\n<div class="top"><a href="{home}">&larr; 回專題首頁</a>'
                f'<span>原始檔：<a href="{path.name}">{html.escape(src)}</a></span></div>\n'
                f"{body}\n</div>\n</body>\n</html>\n")
        out = path.with_suffix(".html")
        out.write_text(page, encoding="utf-8", newline="\n")
        print("wrote", out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
