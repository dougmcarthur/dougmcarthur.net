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

# Bump this whenever assets/css/style.css changes so browsers fetch the new
# file instead of a stale cached copy.
CSS_VERSION = "20261018h"

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
<meta property="og:url" content="{canon}">
<meta property="og:image" content="https://dougmcarthur.net/assets/media/og-card.jpg">
<meta name="twitter:card" content="summary_large_image">"""
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
<link rel="stylesheet" href="/assets/css/style.css?v={CSS_VERSION}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500..700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
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
    <p class="social">
      <a href="https://dougmcarthur.bandcamp.com" aria-label="Bandcamp"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M0 18.75l7.437-13.5H24l-7.438 13.5H0z"/></svg></a>
      <a href="https://open.spotify.com/artist/4E4haw1H8JcjoW0LvXpGSD" aria-label="Spotify"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg></a>
      <a href="https://www.youtube.com/@dougmcarthur" aria-label="YouTube"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg></a>
      <a href="https://www.instagram.com/dougmcarthur" aria-label="Instagram"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077"/></svg></a>
      <a href="https://www.facebook.com/dougmcarthurmusic" aria-label="Facebook"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/></svg></a>
      <a href="https://www.tiktok.com/@DougMcArthurMusic" aria-label="TikTok"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg></a>
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
