#!/usr/bin/env python3
"""Derive the hosted-artifact build from index.html.

The artifact host wraps the file in its own <!doctype>/<head>/<body>, and a
strict CSP blocks any request to a companion file, so this strips the document
shell plus the manifest, icon, and service-worker hooks that only make sense
when the folder is served as a whole.
"""
import re
import sys
from pathlib import Path

src = Path(__file__).parent / "index.html"
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "artifact.html"
html = src.read_text()

def one(pattern, what):
    m = re.search(pattern, html, re.S)
    if not m:
        sys.exit(f"could not find {what} in {src}")
    return m.group(1)

style = one(r"<style>(.*?)</style>", "the stylesheet")
body = one(r"<body>(.*?)</body>", "the body")
script = one(r'<script>\n?(.*?)</script>', "the script")

# Nothing to register against on the artifact host; drop it rather than
# relying on the catch.
script = re.sub(
    r'\n// Only meaningful when the folder is served.*?\n}\n',
    "\n",
    script,
    flags=re.S,
)
if "serviceWorker" in script:
    sys.exit("service worker registration was not stripped")

body = re.sub(r"\s*<script>.*?</script>", "", body, flags=re.S).strip()

out.write_text(
    "<title>Night Match</title>\n"
    f"<style>{style}</style>\n\n"
    f"{body}\n\n"
    f"<script>\n{script}</script>\n"
)
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
