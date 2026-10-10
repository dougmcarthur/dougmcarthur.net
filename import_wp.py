#!/usr/bin/env python3
"""One-time import: WordPress export XML -> content/*.md + download media library.

Run once from the site/ directory:  python3 import_wp.py
The repeatable Pages build is build.py (markdown -> public/ HTML).
"""
import xml.etree.ElementTree as ET
import re, os, html as htmlmod
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

XML_PATH = "/home/hatch/workspace/browser_downloads/sess-2421587949/browser-download-20261009T201101.599185225Z-0-dougmcarthurmusic.WordPress.2026-10-09.xml"
SITE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(SITE, "content")
MEDIA_DIR = os.path.join(SITE, "public", "assets", "media")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

def clean_divi(raw: str) -> str:
    if not raw:
        return ""
    s = raw
    s = s.replace("<!-- [et_pb_line_break_holder] -->", "")
    # strip Gutenberg block comments
    s = re.sub(r"<!--\s*/?wp:[^>]*-->", "", s)
    # strip Divi shortcodes (opening + closing), keep inner content
    s = re.sub(r"\[(?:et_pb_[a-z_0-9]+|/et_pb_[a-z_0-9]+)[^\]]*\]", "", s)
    # drop srcset/sizes (they point at remote resized images)
    s = re.sub(r'\s+srcset="[^"]*"', "", s)
    s = re.sub(r"\s+sizes=\"[^\"]*\"", "", s)
    # collapse runs of empty paragraphs/divs left behind
    s = re.sub(r"<p>(\s|&nbsp;)*</p>", "", s)
    return s.strip()

# Files too large for Cloudflare Pages (25 MB/file limit) — kept out of the deploy.
OVERSIZE_SKIP = {
    "Doug-McArthur-Magic-Mastered-48k24bit.wav",
    "LostWeekendsMaster4824.wav",
}

def download_one(url: str):
    base = url.split("/")[-1].split("?")[0]
    if base in OVERSIZE_SKIP:
        return ("skip", base)
    dest = os.path.join(MEDIA_DIR, base)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return ("ok", base)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = resp.read()
        if len(data) < 200:
            return ("tiny", base)
        with open(dest, "wb") as f:
            f.write(data)
        return ("ok", base)
    except Exception as e:
        return ("fail", f"{base}: {e}")

def main():
    os.makedirs(os.path.join(CONTENT, "posts"), exist_ok=True)
    os.makedirs(os.path.join(CONTENT, "pages"), exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    # ---- 1. media download ----
    urls = []
    for item in root.findall("channel/item"):
        if item.find("wp:post_type", NS).text == "attachment":
            u = item.find("wp:attachment_url", NS).text
            if u:
                urls.append(u)
    print(f"downloading {len(urls)} media files...")
    results = {"ok": 0, "fail": [], "tiny": [], "skip": []}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for status, info in ex.map(download_one, urls):
            if status == "ok":
                results["ok"] += 1
            elif status == "fail":
                results["fail"].append(info)
            elif status == "skip":
                results["skip"].append(info)
            else:
                results["tiny"].append(info)
    print(f"media: {results['ok']} ok, {len(results['fail'])} failed, {len(results['tiny'])} tiny, {len(results['skip'])} skipped (oversize)")
    for f in results["fail"][:20]:
        print("  FAIL:", f)

    downloaded = set(os.listdir(MEDIA_DIR))

    def local_media_url(url: str) -> str:
        base = url.split("/")[-1].split("?")[0]
        base = re.sub(r"-\d+x\d+(\.[a-zA-Z0-9]+)$", r"\1", base)  # foo-300x200.jpg -> foo.jpg
        if base in downloaded:
            return "/assets/media/" + base
        return url  # leave remote if we don't have it

    def rewrite_media(s: str) -> str:
        def repl(m):
            return local_media_url(m.group(0))
        return re.sub(r"https?://dougmcarthur\.net/wp-content/uploads/[^\s\"'<>]+", repl, s)

    # ---- 2. posts & pages -> markdown ----
    def write_md(kind, slug, title, date, body):
        title_q = title.replace('"', '\\"')
        fm = f'---\ntitle: "{title_q}"\ndate: {date}\nslug: {slug}\n---\n'
        path = os.path.join(CONTENT, kind, slug + ".md")
        with open(path, "w") as f:
            f.write(fm + body + "\n")

    n_post = n_page = 0
    for item in root.findall("channel/item"):
        ptype = item.find("wp:post_type", NS).text
        status = item.find("wp:status", NS).text
        if status != "publish" or ptype not in ("post", "page"):
            continue
        title = (item.find("title").text or "").strip()
        slug = (item.find("wp:post_name", NS).text or "").strip()
        pub = item.find("pubDate").text or ""
        try:
            date = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
        except Exception:
            m = re.search(r"\d{4}-\d{2}-\d{2}", pub)
            date = m.group(0) if m else "2000-01-01"
        body = clean_divi(item.find("content:encoded", NS).text or "")
        body = rewrite_media(body)
        if ptype == "post":
            write_md("posts", slug, title, date, body)
            n_post += 1
        else:
            write_md("pages", slug, title, date, body)
            n_page += 1

    print(f"wrote {n_post} posts, {n_page} pages to content/")
    # report any remote media references left behind
    leftover = set()
    for dirpath, _, files in os.walk(CONTENT):
        for fn in files:
            s = open(os.path.join(dirpath, fn)).read()
            for u in re.findall(r"https?://dougmcarthur\.net/wp-content/uploads/[^\s\"'<>]+", s):
                leftover.add(u.split("/")[-1].split("?")[0])
    print(f"content files still referencing remote media: {len(leftover)}")
    for u in sorted(leftover)[:15]:
        print("  ", u)

if __name__ == "__main__":
    main()
