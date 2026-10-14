import html
import os
import re
import subprocess
import sys
from urllib.parse import quote

site, resources = sys.argv[1], sys.argv[2]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp", ".ico"}


def read(name):
    with open(os.path.join(resources, name), encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def render(template, values):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), template)


def url(path):
    return "/".join(quote(part) for part in path.split("/"))


def list_branches():
    refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    excluded = {"origin", "origin/HEAD", "origin/main"}
    return sorted(ref[len("origin/"):] for ref in refs if ref not in excluded)


def branch_listing(branch):
    base = os.path.join(site, branch)
    files = []
    for directory, _, names in os.walk(base):
        for name in names:
            if os.path.splitext(name)[1].lower() not in IMAGE_EXTS:
                continue
            rel = os.path.relpath(os.path.join(directory, name), base).replace(os.sep, "/")
            files.append(rel)
    files.sort()
    if not files:
        return '<p class="empty">Sin imágenes</p>'
    figures = []
    for f in files:
        src = html.escape(url(f))
        name = html.escape(os.path.splitext(os.path.basename(f))[0])
        alt = html.escape(f)
        figures.append(
            f'<figure>\n'
            f'<figcaption>{name}</figcaption>\n'
            f'<img src="{src}" alt="{alt}" loading="lazy">\n'
            f'<pre class="code"><code>{src}</code>'
            f'<button type="button" class="copy">¡Cópiame!</button></pre>\n'
            f'</figure>'
        )
    return "\n".join(figures)


def build_tree(branches):
    tree = {}
    for branch in branches:
        node = tree
        parts = branch.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = branch
    return tree


def render_tree(node, level=2):
    leaves = [(k, v) for k, v in sorted(node.items()) if isinstance(v, str)]
    groups = [(k, v) for k, v in sorted(node.items()) if isinstance(v, dict)]
    parts = []
    if leaves:
        items = "\n".join(
            f'<li><a href="{html.escape(url(v))}/">{html.escape(k)}</a></li>' for k, v in leaves
        )
        parts.append(f'<ul class="links">\n{items}\n</ul>')
    for name, child in groups:
        h = min(level, 6)
        parts.append(
            f'<section class="group">\n<h{h}>{html.escape(name)}</h{h}>\n{render_tree(child, level + 1)}\n</section>'
        )
    return "\n".join(parts)


style = read("style.css")
branches = list_branches()

branch_template = read("branch-index.html")
for branch in branches:
    depth = len(branch.split("/"))
    content = render(
        branch_template,
        {
            "STYLE": style,
            "BRANCH": html.escape(branch),
            "ROOT": "../" * depth,
            "LISTING": branch_listing(branch),
        },
    )
    write(os.path.join(site, branch, "index.html"), content)

root_listing = render_tree(build_tree(branches)) if branches else '<p class="empty">No hay ramas</p>'
write(
    os.path.join(site, "index.html"),
    render(
        read("root-index.html"),
        {"STYLE": style, "ROOT": "./", "LISTING": root_listing},
    ),
)