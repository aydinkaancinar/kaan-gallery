"""Render this project's security notes as standalone HTML (standard library only).

This intentionally supports the Markdown constructs used in the source document,
not the entire Markdown specification. Run from any working directory.
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs' / 'SECURITY_IMPLEMENTATION.md'
OUTPUT = SOURCE.with_suffix('.html')


def inline(text):
    # Escape first; source text cannot inject HTML or attributes.
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def render(source):
    lines = source.splitlines()
    output, navigation = [], []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith('```'):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                code.append(lines[index])
                index += 1
            output.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
            index += 1
            continue
        heading = re.match(r'^(#{1,3}) (.+)$', line)
        if heading:
            level, title = len(heading[1]), heading[2]
            anchor = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            output.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
            if level == 2:
                navigation.append(f'<a href="#{anchor}">{escape(title)}</a>')
            index += 1
            continue
        if line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].startswith('|'):
                cells = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                    rows.append(cells)
                index += 1
            header = ''.join(f'<th scope="col">{inline(c)}</th>' for c in rows[0])
            body = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in row) + '</tr>' for row in rows[1:])
            output.append(f'<div class="table-wrap" tabindex="0" role="region" aria-label="Security policy table"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        if re.match(r'^(?:- |\d+\. )', line):
            ordered = bool(re.match(r'^\d+\. ', line))
            tag = 'ol' if ordered else 'ul'
            pattern = r'^\d+\. ' if ordered else r'^- '
            items = []
            while index < len(lines) and re.match(pattern, lines[index]):
                items.append('<li>' + inline(re.sub(pattern, '', lines[index])) + '</li>')
                index += 1
            output.append(f'<{tag}>' + ''.join(items) + f'</{tag}>')
            continue
        paragraph = []
        while index < len(lines) and lines[index].strip():
            paragraph.append(lines[index])
            index += 1
        output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
    return '\n'.join(output), '\n'.join(navigation)


body, navigation = render(SOURCE.read_text())
page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="referrer" content="no-referrer">
<title>Kaan Gallery · Security implementation</title>
<style>
:root{--ink:#202c31;--muted:#586970;--accent:#20675d;--line:#dce4df;--paper:#fff;--canvas:#f4f6f2}
*{box-sizing:border-box}html{scroll-padding-top:2rem}body{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.75 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--accent);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}a:focus-visible,.table-wrap:focus-visible{outline:3px solid var(--accent);outline-offset:4px}.skip{position:absolute;left:1rem;top:-5rem;background:white;padding:.5rem 1rem}.skip:focus{top:1rem;z-index:5}
header{padding:2.5rem max(1.5rem,calc((100vw - 1240px)/2));border-bottom:1px solid var(--line);background:var(--paper)}.brand{font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700}header p{margin:.5rem 0 1rem;max-width:60ch;color:var(--muted)}.badge{display:inline-block;font-size:.8rem;background:#fff1d5;color:#77540e;border:1px solid #e8d3a4;border-radius:30px;padding:.2rem .75rem}.layout{max-width:1288px;margin:auto;display:grid;grid-template-columns:270px minmax(0,1fr);gap:3rem;padding:2.5rem 1.5rem 4rem}nav{position:sticky;top:2rem;align-self:start;font-size:.85rem;max-height:90vh;overflow:auto}nav strong{display:block;margin-bottom:.8rem}nav a{display:block;text-decoration:none;color:var(--muted);padding:.35rem 0}nav a:hover{color:var(--accent)}article{min-width:0;background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:2.5rem}h1,h2,h3{line-height:1.25;letter-spacing:-.025em}h1{font-size:2.3rem;margin:0 0 1.5rem}h2{font-size:1.4rem;margin:2.7rem 0 1rem;padding-top:1.3rem;border-top:1px solid var(--line)}p{margin:0 0 1rem}li{margin:.45rem 0}code{font: .88em/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;background:#eef3ef;border-radius:4px;padding:.12rem .3rem;overflow-wrap:anywhere}pre{padding:1.2rem;background:#172d2b;color:#e3f0e9;overflow:auto;border-radius:10px}pre code{background:none;padding:0;color:inherit;white-space:pre;overflow-wrap:normal}.table-wrap{overflow:auto;margin:1.5rem 0}table{border-collapse:collapse;font-size:.88rem;width:100%;min-width:560px}th,td{text-align:left;vertical-align:top;padding:.8rem;border-bottom:1px solid var(--line)}th{background:#edf3ed;font-weight:650}footer{color:var(--muted);max-width:1240px;margin:0 auto;padding:0 1.5rem 3rem;font-size:.85rem}
@media(max-width:900px){.layout{grid-template-columns:1fr;gap:1.5rem}nav{position:static;max-height:none}nav a{display:inline-block;margin-right:1rem}article{padding:1.5rem}h1{font-size:1.9rem}}
@media print{body{background:white;font-size:10pt}header{padding:0 0 1rem}.layout{display:block;padding:0}nav,.skip{display:none}article{border:0;padding:0}pre{white-space:pre-wrap;background:#eee;color:black}h2{break-after:avoid}.table-wrap{overflow:visible}table{min-width:0}footer{padding:1rem 0}a{color:inherit}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to documentation</a>
<header><div class="brand">Kaan Gallery / Engineering notes</div><p>A source-linked explanation of the gallery's security controls, evidence, and unfinished work.</p><span class="badge">Development · Not production-ready</span> <a href="SECURITY_IMPLEMENTATION.md">Markdown source</a></header>
<div class="layout"><nav aria-label="Document sections"><strong>On this page</strong>__NAV__</nav><article id="main">__BODY__</article></div>
<footer>Generated from SECURITY_IMPLEMENTATION.md. Rebuild with <code>python scripts/build_security_page.py</code>. Source-file links open locally; static hosting may download source files rather than render them.</footer>
</body></html>
'''.replace('__NAV__', navigation).replace('__BODY__', body)
OUTPUT.write_text(page)
print(f'Created {OUTPUT}')
