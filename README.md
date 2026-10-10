# dougmcarthur.net — static rebuild for Cloudflare Pages

Static HTML/CSS replacement for the WordPress site, ready to deploy on Cloudflare Pages (free).

## What's built

- **23 blog posts** → `/<slug>/`, listed newest-first on `/news/`
- **10 pages** → `/music/`, `/press-appearances/`, `/mailing-list/`, `/contact/`, `/privacy-policy/`, `/secret-songs/`, `/sneakpeeks/`, `/the-light-june-16-2025-demo/` (+ hand-built `/` and `/news/`)
- **326 media files** in `public/assets/media/` (images, mp3s, pdfs) — all post/page image URLs rewritten to local paths
- **Home page**: hero, latest releases (Bandcamp/Spotify), press quotes, Bandsintown upcoming-shows widget + Play My City, 4 YouTube videos, full discography (Soapbox + Broken Halo), career highlights, newsletter signup
- **Newsletter**: Buttondown signup form → Pages Function `functions/api/subscribe.js` (API key stays server-side)
- **Blog workflow**: Decap CMS at `/admin/` — edit posts/pages in a friendly editor, changes commit to GitHub, Pages rebuilds
- **Contact form**: self-coded Pages Function (`functions/api/contact.js`) + Resend for email delivery (free tier)

## 3 setup items Doug must do

### 1. Buttondown (newsletter)
1. Create a free account at https://buttondown.com (free up to 100 subscribers — you have 17).
2. In WordPress: MailPoet → Subscribers → Export, then import the CSV into Buttondown (Subscribers → Add → Import).
3. In Buttondown: Settings → API → create an API key.
4. In Cloudflare Pages: your project → Settings → Environment variables → add `BUTTONDOWN_API_KEY` = the key (both Production and Preview).

### 2. GitHub repo (for Decap CMS) — DONE
Repo `dougmcarthur/dougmcarthur.net` is connected in `public/admin/config.yml`. Push this `site/` folder as the repo root, then in GitHub authorize Decap CMS on first login at `/admin/`. New blog posts: write, publish — Pages rebuilds automatically.

### 3. Resend (contact form email delivery)
1. Create a free account at https://resend.com, verify the dougmcarthur.net domain (DNS TXT records), create an API key.
2. In the Cloudflare Pages project: Settings > Environment variables — set `RESEND_API_KEY`, `TURNSTILE_SECRET_KEY` (from the existing Turnstile widget in the Cloudflare dashboard), and optionally `CONTACT_TO` (to override the default doug@dougmcarthur.net) and `TURNSTILE_HOSTNAMES` (comma-separated allowed hostnames, e.g. `dougmcarthur.net,www.dougmcarthur.net`; leave unset to skip the hostname check).

## Deploying on Cloudflare Pages

1. Pages → Create → Connect your GitHub repo.
2. Build settings: **Build command** `python3 build.py` · **Build output directory** `public/` · **Root directory** `/` (repo root = this `site/` folder).
3. Add the `BUTTONDOWN_API_KEY` env var (see above).
4. Deploy — you get a `*.pages.dev` URL to preview.

## DNS cutover (when ready to go live)

1. In Cloudflare dashboard → Pages → your project → Custom domains → add `dougmcarthur.net` (and `www`).
2. Cloudflare auto-creates the DNS records (your DNS is already on Cloudflare).
3. Wait for SSL to activate, verify the site, then cancel Bluehost hosting. Keep the Hover domain registration.
4. Optional: set up a redirect for `/wp-content/uploads/*` → new `/assets/media/*` if old links exist in the wild (filenames are unchanged).

## Notes / dropped items

- **Comments**: 18 approved WordPress comments were not migrated (no free static-native equivalent configured). The export XML still has them if ever needed.
- **2 oversize audio files** (`_oversize-media/`: two WAV masters, 63–76 MB each) exceed Cloudflare's 25 MB/file limit and were left out of the deploy. They weren't linked from any page. Convert to MP3 or host on Bandcamp/SoundCloud if you want them public.
- **Draft page** "Songwriting Retreat Fall 2025" was not migrated (it was a draft).
- **links.dougmcarthur.net** subscribe endpoint (custom WP plugin) is not replicated — the Buttondown form replaces it.
- **The Events Calendar** plugin is not replicated — Bandsintown is now the single source of show listings.
- `import_wp.py` is the one-time WordPress importer (already run). `build.py` is the repeatable build — safe to run anytime; it never touches `public/index.html` (hand-built home page).
