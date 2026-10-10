#!/usr/bin/env python3
"""Checks for wiki-content/: links, banned words, stale labels, Mermaid parity and rendering.

Run from the repository root:  python3 docs/wiki-diagrams/check-wiki.py
Exit code 1 if any check fails. Needs mmdc for the render check (skipped with --no-render).
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WIKI = os.path.join(ROOT, "wiki-content")
DIAG = os.path.join(ROOT, "docs", "wiki-diagrams")
BANNED = r"\b(delve|tapestry|multifaceted|paradigm|foster|cutting-edge|holistic|synergy|resonate|pivotal|game-changer|transformative|embark|unravel|beacon)\b"
STALE = r"\b(V3\.7|V3\.8|V4\.0\.5|V4\.1\.\d+)\b"
problems = []

pages = sorted(f for f in os.listdir(WIKI) if f.endswith(".md"))
names = {f[:-3] for f in pages}
images = set(os.listdir(os.path.join(WIKI, "images"))) if os.path.isdir(os.path.join(WIKI, "images")) else set()

def add(page, msg):
    problems.append(f"{page}: {msg}")

for page in pages:
    text = open(os.path.join(WIKI, page), encoding="utf-8").read()
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    for m in re.finditer(r"\]\(([^)\s]+)\)", body):
        u = m.group(1)
        if u.startswith(("http://", "https://", "mailto:", "#")):
            continue
        t = u.split("#")[0]
        if t.startswith("images/"):
            if t[7:] not in images:
                add(page, f"missing image {t}")
        elif t and t not in names and not os.path.exists(os.path.join(WIKI, t)):
            add(page, f"broken link ({u})")
    for m in re.finditer(r"\[\[([^\]|]+)", body):
        n = m.group(1).strip().replace(" ", "-")
        if n not in names:
            add(page, f"broken wiki link [[{m.group(1)}]]")
    for m in re.finditer(r'src="(images/[^"]+)"', text):
        if m.group(1)[7:] not in images:
            add(page, f"missing image {m.group(1)}")
    for m in re.finditer(BANNED, body, re.I):
        add(page, f"banned word '{m.group(0)}'")
    if page not in ("Home.md",) and re.match(r"^# .*(V3|V4\.|3\.7)", text):
        add(page, "stale release label in title")
    for m in re.finditer(STALE, body):
        add(page, f"stale label '{m.group(0)}' (check it is historical)")
    for m in re.finditer(r"/Users/(?!yourusername|Shared)[A-Za-z0-9_.-]+", text):
        add(page, f"real home path {m.group(0)}")

# Mermaid blocks must equal a .mmd source (ignoring the title-less definition) and must render.
src = {f[:-4]: open(os.path.join(DIAG, f), encoding="utf-8").read().strip()
       for f in os.listdir(DIAG) if f.endswith(".mmd")}
used = set()
for page in pages:
    text = open(os.path.join(WIKI, page), encoding="utf-8").read()
    for m in re.finditer(r"```mermaid\n(.*?)```", text, re.S):
        block = m.group(1).strip()
        hit = [k for k, v in src.items() if v == block]
        if hit:
            used.add(hit[0])
        else:
            add(page, "mermaid block does not match any docs/wiki-diagrams/*.mmd source")
for k in sorted(set(src) - used):
    problems.append(f"diagram {k}.mmd is not embedded in any page")
for k in src:
    if f"{k}.png" not in images:
        problems.append(f"diagram {k}.mmd has no rendered PNG in wiki-content/images")

if "--no-render" not in sys.argv:
    for k, v in src.items():
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.svg")
            r = subprocess.run(["mmdc", "-q", "-i", os.path.join(DIAG, k + ".mmd"), "-o", out,
                                "-c", os.path.join(DIAG, "mermaid.config.json")], capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(out):
                problems.append(f"diagram {k}.mmd failed to render: {r.stderr.strip()[:200]}")

print(f"{len(pages)} pages, {len(src)} diagrams checked")
for p in problems:
    print("PROBLEM", p)
sys.exit(1 if problems else 0)
