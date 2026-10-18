#!/usr/bin/env python3
"""Cloudflare Pages build: content/*.md -> public/ HTML. Pure stdlib, no deps.

Usage (also the Pages build command):  python3 build.py
Run from the site/ directory. Publish directory: public/
"""
import os
import shutil, re, html as htmlmod
from datetime import datetime

def esc_title(t):
    """Escape a frontmatter title without double-encoding existing entities."""
    return htmlmod.escape(htmlmod.unescape(t or ""))

SITE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(SITE, "content")
PUBLIC = os.path.join(SITE, "public")

# Canonical production origin. All canonical/OG/sitemap URLs use this so the
# staging *.pages.dev domain never becomes the indexed copy.
CANONICAL = "https://dougmcarthur.net"

NAV = [
    ("Home", "/"),
    ("News", "/news/"),
    ("Music", "/music/"),
    ("Press & Appearances", "/press-appearances/"),
    ("Contact", "/contact/"),
]

# ---------------------------------------------------------------- frontmatter
def parse_md(path):
    text = open(path, encoding="utf-8").read()
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = text[end + 4 :].lstrip("\n")
    return meta, body

# ------------------------------------------------------- tiny markdown render
def md_inline(s):
    s = htmlmod.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" loading="lazy">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s

def md_render(body):
    """Markdown with full HTML passthrough: any block starting with '<' is kept raw."""
    if "<" in body and re.search(r"<(p|div|h[1-6]|ul|ol|li|iframe|img|a|blockquote|figure)[\s>]", body):
        # already HTML (imported WP content) — trust it as-is
        return body
    out, para, in_list = [], [], None
    def flush_para():
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()
    for line in body.splitlines():
        s = line.strip()
        if not s:
            flush_para()
            if in_list:
                out.append(f"</{in_list}>"); in_list = None
            continue
        if s.startswith("<"):  # raw HTML block
            flush_para()
            if in_list:
                out.append(f"</{in_list}>"); in_list = None
            out.append(line)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            flush_para()
            out.append(f"<h{len(m.group(1))}>{md_inline(m.group(2))}</h{len(m.group(1))}>")
            continue
        if re.match(r"^---+$", s):
            flush_para(); out.append("<hr>"); continue
        m = re.match(r"^>\s?(.*)", s)
        if m:
            flush_para(); out.append(f"<blockquote><p>{md_inline(m.group(1))}</p></blockquote>"); continue
        m = re.match(r"^([-*])\s+(.*)", s)
        if m:
            flush_para()
            if in_list != "ul":
                if in_list: out.append(f"</{in_list}>")
                out.append("<ul>"); in_list = "ul"
            out.append(f"<li>{md_inline(m.group(2))}</li>"); continue
        m = re.match(r"^(\d+)[.)]\s+(.*)", s)
        if m:
            flush_para()
            if in_list != "ol":
                if in_list: out.append(f"</{in_list}>")
                out.append("<ol>"); in_list = "ol"
            out.append(f"<li>{md_inline(m.group(2))}</li>"); continue
        para.append(s)
    flush_para()
    if in_list:
        out.append(f"</{in_list}>")
    return "\n".join(out)

# ------------------------------------------------------------------ templates
def nav_html(active):
    items = []
    for label, href in NAV:
        cls = ' class="active"' if href == active else ""
        items.append(f'<li><a href="{href}"{cls}>{label}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"

def base(title, body_html, active="/", desc="", path="/", og_type="website"):
    desc_tag = f'<meta name="description" content="{htmlmod.escape(desc[:160], quote=True)}">' if desc else ""
    canon = CANONICAL + path
    t_esc = htmlmod.escape(esc_title(title) + " | Doug McArthur", quote=True)
    d_esc = htmlmod.escape(desc[:200], quote=True) if desc else ""
    seo_tags = f"""<link rel="canonical" href="{canon}">
<meta property="og:site_name" content="Doug McArthur">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{t_esc}">
<meta property="og:url" content="{canon}">"""
    if d_esc:
        seo_tags += f'\n<meta property="og:description" content="{d_esc}">'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc_title(title)} | Doug McArthur</title>
{desc_tag}
{seo_tags}
<link rel="stylesheet" href="/assets/css/style.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="icon" href="/assets/media/favicon.svg" type="image/svg+xml">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/"><img class="brand-logo" src="/assets/media/logo.svg" alt="Doug McArthur"></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="main-nav" aria-label="Menu">☰</button>
    <nav class="main-nav" id="main-nav">{nav_html(active)}</nav>
  </div>
</header>
<main class="wrap" id="main">
{body_html}
</main>
<footer class="site-footer">
  <div class="wrap footer-inner">
    <p class="footer-blurb">Singin songs n' stuff.</p>
    <p class="social">
      <a href="https://dougmcarthur.bandcamp.com">Bandcamp</a>
      <a href="https://open.spotify.com/artist/4E4haw1H8JcjoW0LvXpGSD">Spotify</a>
      <a href="https://www.youtube.com/@dougmcarthur">YouTube</a>
      <a href="https://www.instagram.com/dougmcarthur">Instagram</a>
      <a href="https://www.facebook.com/dougmcarthurmusic">Facebook</a>
      <a href="https://www.tiktok.com/@DougMcArthurMusic">TikTok</a>
    </p>
    <p class="copy">© {datetime.now().year} Doug McArthur · Winnipeg, Manitoba, Canada</p>
  </div>
</footer>
<script src="/assets/js/main.js" defer></script>
</body>
</html>"""

def excerpt_of(html_text, n=180):
    t = re.sub(r"<[^>]+>", " ", html_text)
    t = htmlmod.unescape(re.sub(r"\s+", " ", t)).strip()
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0]  # break at a word boundary, not mid-word
    return cut + "…"

def fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        return d

# ------------------------------------------------- seo: sitemap, robots, redirects
def write_seo_files(urls):
    """urls: list of site paths like '/' or '/news/'. Writes sitemap.xml,
    robots.txt, _redirects (301s for dead WordPress URL shapes + www->apex),
    and a plain 404 page into PUBLIC."""
    today = datetime.now().strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{CANONICAL}{u}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    open(os.path.join(PUBLIC, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm))

    open(os.path.join(PUBLIC, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\nSitemap: {CANONICAL}/sitemap.xml\n")

    redirects = [
        # one canonical host: www -> apex
        "https://www.dougmcarthur.net/* https://dougmcarthur.net/:splat 301",
        # dead WordPress URL shapes -> closest live equivalent
        "/category/* /news/ 301",
        "/tag/* /news/ 301",
        "/author/* / 301",
        "/feed /news/ 301",
        "/feed/* /news/ 301",
        "/*/feed /news/ 301",
        "/*/feed/* /news/ 301",
    ]
    for year in range(2008, 2027):
        redirects.append(f"/{year}/* /news/ 301")   # date archives
    open(os.path.join(PUBLIC, "_redirects"), "w", encoding="utf-8").write(
        "\n".join(redirects) + "\n")

    notfound = base("Page not found",
                    '<article class="page"><h1>Page not found</h1>'
                    '<p>That link doesn\'t exist anymore. Try the '
                    '<a href="/">homepage</a> or the <a href="/news/">news archive</a>.</p>'
                    "</article>", path="/404.html")
    open(os.path.join(PUBLIC, "404.html"), "w", encoding="utf-8").write(notfound)
def build():
    posts, pages = [], []
    shutil.copytree("assets", PUBLIC + "/assets", dirs_exist_ok=True)
    shutil.copytree("admin_src", PUBLIC + "/admin", dirs_exist_ok=True)
    shutil.copyfile("home.html", PUBLIC + "/index.html")  # hand-built homepage template
    for fn in sorted(os.listdir(os.path.join(CONTENT, "posts"))):
        if fn.endswith(".md"):
            meta, body = parse_md(os.path.join(CONTENT, "posts", fn))
            posts.append((meta, body))
    for fn in sorted(os.listdir(os.path.join(CONTENT, "pages"))):
        if fn.endswith(".md"):
            meta, body = parse_md(os.path.join(CONTENT, "pages", fn))
            if meta.get("slug") in ("new-home", "news"):
                continue  # home is hand-built; news is generated
            pages.append((meta, body))
    posts.sort(key=lambda p: p[0].get("date", ""), reverse=True)

    # post pages
    for meta, body in posts:
        slug = meta["slug"]
        d = os.path.join(PUBLIC, slug)
        os.makedirs(d, exist_ok=True)
        inner = f"""<article class="post">
  <p class="post-date">{fmt_date(meta.get('date',''))}</p>
  <h1>{esc_title(meta.get('title',''))}</h1>
  <div class="entry">{md_render(body)}</div>
  <p class="back"><a href="/news/">← All news</a></p>
</article>"""
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            base(meta.get("title", ""), inner, active="/news/", desc=excerpt_of(body),
                 path=f"/{slug}/", og_type="article"))

    # news index
    items = []
    for meta, body in posts:
        items.append(f"""<article class="news-item">
  <p class="post-date">{fmt_date(meta.get('date',''))}</p>
  <h2><a href="/{meta['slug']}/">{esc_title(meta.get('title',''))}</a></h2>
  <p>{htmlmod.escape(excerpt_of(body))}</p>
</article>""")
    news_inner = "<h1>News</h1>\n" + "\n".join(items)
    os.makedirs(os.path.join(PUBLIC, "news"), exist_ok=True)
    open(os.path.join(PUBLIC, "news", "index.html"), "w", encoding="utf-8").write(
        base("News", news_inner, active="/news/", path="/news/"))

    # pages
    for meta, body in pages:
        slug = meta["slug"]
        d = os.path.join(PUBLIC, slug)
        os.makedirs(d, exist_ok=True)
        inner = f"""<article class="page">
  <h1>{esc_title(meta.get('title',''))}</h1>
  <div class="entry">{md_render(body)}</div>
</article>"""
        active = f"/{slug}/" if any(h == f"/{slug}/" for _, h in NAV) else "/"
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            base(meta.get("title", ""), inner, active=active, desc=excerpt_of(body),
                 path=f"/{slug}/"))

    print(f"built {len(posts)} posts, {len(pages)} pages, news index")

    # seo files: every public URL (home is hand-built but always present)
    urls = ["/", "/news/"]
    urls += [f"/{m['slug']}/" for m, _ in posts]
    urls += [f"/{m['slug']}/" for m, _ in pages]
    write_seo_files(urls)

if __name__ == "__main__":
    build()
