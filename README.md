# Bote sa Bote: capstone progress in a bottle

A ship-in-a-bottle progress tracker for a BSIT capstone team (STI College Lipa, 3rd year). Every milestone is a sail. Every finished task raises the sea. You paste one view link into the Messenger group chat once, and it stays current for everyone. Nobody installs an app.

## What works now

- **Launch a bottle**: thesis title, team, members, and milestones (a chapter template is prefilled). You get a private **captain link** for editing and a public **view link** for sharing.
- **Exact progress**: percent = Σ(weight × done tasks) / Σ(weight × all tasks), floored to 0.1%. The raw fraction is always shown next to it (e.g. "weighted 4/11"), so nobody has to trust a rounded number. Covered by unit tests.
- **Live sync**: every open page checks a version number every 4 s (only while the tab is visible) and redraws when anything changes. Verified with two browser sessions: an edit in one showed up in the other without a reload.
- **Messenger-ready sharing**:
  - The view link carries Open Graph tags plus a generated 600×315 PNG card (bottle, sea level, sails, percent), so the link unfurls with a preview.
  - "Copy progress text" gives a plain-text summary (bar, per-milestone and per-member counts, timestamp, link) to paste into the chat.
  - "Share to group chat" uses the phone's native share sheet when the browser supports it.
- **Crew stats**: done / doing / assigned for each member.
- **Ship's log**: the last 15 changes.
- **Access**: edits require the captain key (only its SHA-256 hash is stored, compared in constant time). Viewers are read-only.
- **Accessibility**: tested at 390 px and 1440 px, light and dark; no sideways scroll; touch targets ≥ 44 px; one h1; reduced-motion respected.

## Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Launch page |
| GET | `/p/:slug` | Bottle page (view; add `#key=…` once to unlock editing on that device) |
| GET | `/og/:slug.png` | Share-preview image |
| POST | `/api/projects` | Create a project → `{slug, editKey, viewUrl, editUrl}` |
| GET | `/api/projects/:slug` | Full state + computed progress |
| GET | `/api/projects/:slug/version` | Version number (polling) |
| GET | `/api/projects/:slug/summary` | Plain-text summary for the chat |
| POST | `/api/projects/:slug/verify` | Check a captain key |
| POST, DELETE | `/api/projects/:slug/members[/:id]` | Crew (needs `x-edit-key`) |
| POST, PATCH, DELETE | `/api/projects/:slug/milestones[/:id]` | Milestones (needs `x-edit-key`) |
| POST, PATCH, DELETE | `/api/projects/:slug/tasks[/:id]` | Tasks (needs `x-edit-key`) |

## Data

Cloudflare D1 (SQLite). Tables: `projects`, `members`, `milestones`, `tasks`, `activity` (see `migrations/0001_initial.sql`). Limits: 12 members, 20 milestones, 400 tasks per project.

## Limits, stated plainly

- **"Inside Messenger"**: Meta's official Messenger Platform supports page-to-user conversations only, not bots in group chats (Meta developer forum, read 2026-10-23: https://developers.facebook.com/community/threads/361517551165694/). The chat side therefore runs through [Heisenbot](https://github.com/Tiredicey/Heisenbot), which uses a second Facebook account in a real browser. That's unofficial automation: Facebook may ask that account for a security check (Heisenbot alerts you and gives you a remote login), and it could restrict the account. Use a burner account, never your main one.
- **"100% accurate"**: the math is exact and tested, but the bottle only knows what the team marks done. It cannot verify the work itself.
- **"Realtime"**: about 4 s polling, not push. That fits Cloudflare's request model without a WebSocket server.
- **Messenger preview caching**: Meta may cache the unfurl image for a while after the first share. The `?v=` version number on the image URL helps; the page itself is always live.

## Setup guide: what you do (about 15 minutes, once)

Everything else is automatic. These are the only steps that need you, because each one needs your own account or a password.

**1. Put the bottle online (your own Cloudflare account, free).**
1. Sign up at dash.cloudflare.com (free plan, no card).
2. My Profile → API Tokens → Create Token → **Create Custom Token** with two permissions: *Account · Cloudflare Pages · Edit* and *Account · D1 · Edit*.
3. Paste the token in this Genspark project's **Deploy** panel and say "deploy". Or run it yourself: `CLOUDFLARE_API_TOKEN=… npm run deploy`.

`deploy/cloudflare.sh` creates the D1 database, applies the migration, creates the Pages project `bote-sa-bote` and deploys. You get `https://bote-sa-bote.pages.dev`, or a `-2` suffix if that name is taken. It's safe to re-run.

**2. Tell Walter where the bottle lives.** Open the Heisenbot dashboard → **Capstone bottle** → paste the address from step 1 → **Save** → **Test**. Test creates your bottle and shows the summary.

**3. Turn Walter live.** In the dashboard, switch off **Dry run** and press **Start**. Walter posts the bottle link in the group chat once. From then on, members just type `!done …`, `!task …`, `!bottle`, `!teaser`.

That's it. There's no app to install, no account for members, and nobody has to paste the link.

## Where the MP4s are

They're too large for git, so they're attached to the GitHub Release **film-v1** (permanent public links):

| File | Use it for | Size |
|---|---|---|
| [bote_sa_bote_master.mp4](https://github.com/Tiredicey/ITCAPSTONE/releases/download/film-v1/bote_sa_bote_master.mp4) | 16:9: defense presentation, YouTube, projector | 133 MB |
| [bote_sa_bote_9x16.mp4](https://github.com/Tiredicey/ITCAPSTONE/releases/download/film-v1/bote_sa_bote_9x16.mp4) | 9:16: Facebook Reels, TikTok, Stories | 112 MB |
| [bote_sa_bote_messenger.mp4](https://github.com/Tiredicey/ITCAPSTONE/releases/download/film-v1/bote_sa_bote_messenger.mp4) | Messenger: under the 25 MB in-chat limit; Walter sends this one on `!teaser` | 18 MB |

MD5 checksums are in `SHA_MD5.txt` on the same release. Don't commit MP4s into this repo: they bloat every clone forever.

The 25 MB Messenger figure comes from user reports, which conflict (a 2025 article says Messenger raised the limit to 100 MB). At 18 MB the Messenger cut is under both, so it works either way.

## Run locally

```bash
npm install
npm run build
npx wrangler d1 migrations apply bote-sa-bote-production --local
pm2 start ecosystem.config.cjs     # serves on :3000
npm test                           # 8 unit tests
```

## Deploy

**Live:** https://bote-sa-bote.pages.dev (Cloudflare Pages + D1 `bote-sa-bote-production`, on your own account; deployed 2026-10-23).

If your token can't read account details, set `CLOUDFLARE_ACCOUNT_ID` too.

`npm run deploy` (needs `CLOUDFLARE_API_TOKEN`) runs `deploy/cloudflare.sh`. On first run it writes the real `database_id` into `wrangler.jsonc`; commit that change afterward. Redeploys reuse the same database, so the data stays.

---

# The film: `video/`

A 44.57 s, 1280×720, 30 fps teaser plus a 1080×1920 vertical cut. Everything is drawn in code. No generated footage, no stock, no copyrighted stills.

| Bars (140 BPM) | Scene | Brief item |
|---|---|---|
| 0–3 | Ink-drawn magic circle activates, quill tracing it, heartbeat only | ink magic-circle activation |
| 3–6 | Free-fall down an abandoned orbital station (real 3D perspective, depth fog, motion blur, three camera cuts) | free-fall, 3D |
| 6–9 | Kinetic geometric array: 3D rings and hexagram, milestones light on the beat | geometric magic array reveal |
| 9–12 | 3D bottle with crosshatched sea rising to the sample percent | the product |
| 12–15 | Messenger-style chat with the share card and Filipino slang | group chat, memes |
| 15–18 | Apprentice turnaround: front, 3/4, side, back (original character) | robe and pointed hat turnaround sheet |
| 18–21 | Climax: fall + array at double speed, 62% → 100% | payoff |
| 21–22 | Plunge into the circle, one silent beat | smash cut |
| 22–26 | Gold-leaf title framed by a floral etched border | title typography, floral etching |

**Look**: gold leaf (#E2BA68 / #B08434 / #7A581E) on ink #2B1E12 and night #18110A, with a paper-and-sepia post pass and seeded grain. Shading is line crosshatching (a Shirahama-style etching reference; not her art). Type: IM Fell English SC + Atkinson Hyperlegible (both OFL, `video/fonts/OFL.txt`).

**Rebuild**: `cd video && ./build.sh` (needs Python with numpy, scipy, skia-python, librosa, and ffmpeg). Frames are a pure function of t; the determinism probe (`python3 render.py --probe`) gave identical hashes on repeat renders.

**Score** (`score.py`): synthesized from oscillators, FM, and filtered noise. No samples. 140 BPM, D minor (Dm–B♭–F–C, then A to pull back to Dm). The tempo was chosen to match your "pulse at 140" brief. `cue_sheet.json` lists all 134 hits. Mastered with a two-pass linear loudnorm (`master.py`).

The score is its own composition and does not reproduce any track from your playlist.

## Audio recommendation (from `Chill.csv`, 307 tracks)

Your playlist's median tempo is 119.3 BPM; 51 tracks sit between 132 and 148 BPM. Top genres are OPM, harana, pinoy indie, and R&B. Spotify's "tempo" field is an estimate; values below are copied from your CSV.

1. **Use the included original score.** It's the only option that is cut-synced, cleared for any upload, and actually at 140.
2. **If you want a playlist track instead, use Tycho, "A Walk"**: 139.95 BPM, instrumentalness 0.911, energy 0.717. It's the only track in your list that is near 140 and nearly vocal-free, so it won't fight the on-screen text. Re-time the cuts to its measured beat grid.
3. Near-140 alternatives with vocals: Toro y Moi "So Many Details" (143.99), Coldplay "Viva La Vida" (138.02), ADÉLA "Ain't In LA" (138.99).

Any commercial track needs a licence (or a platform's built-in music library) before you post it. The included score has no such issue.

**About "pulse races at 140"**: music cannot be shown to drive a viewer's heart to a target rate. A systematic review in Trends in Cardiovascular Medicine (Kulinski et al., 2022, https://www.sciencedirect.com/science/article/pii/S1050173821000700) notes that an earlier 2015 review found no evidence for heart-rate entrainment to tempo. The film uses 140 BPM as the tempo for the felt rush; it promises no physiological effect.

## M1 teardown: reference vs. this film (same script, `video/teardown.py`)

| Metric | Witch Hat Atelier trailer (your upload) | Bote sa Bote master |
|---|---|---|
| Duration | 121.3 s | 44.6 s |
| Resolution / fps | 1920×1080 / 23.976 | 1280×720 / 30 |
| Scene cuts (ffmpeg scene > 0.3) | 124 (61.3 / min) | 5 (6.7 / min) |
| Median shot | 0.63 s | 5.15 s |
| Cuts landing within 83 ms of a beat | 35.5% | 100% |
| Near-still frame share | 29.1% | 46.4% |
| Max flashes in any 1 s | 2 | 1 (WCAG 2.3.1 limit: 3) |
| Integrated loudness | −9.8 LUFS | −13.9 LUFS |
| Sample peak | +1.6 dBFS (clipping) | −3.5 dBFS (no clipping) |
| Detected tempo (librosa) | 123.0 BPM | 143.6 BPM (true grid 140; librosa estimate) |

**Where the film wins**: every detected cut is on the beat (100% vs 35.5%), there's no clipping (−3.5 dBFS vs +1.6), it has fewer flashes (1 vs 2 in any second), and loudness sits at the −14 web target. **Where it loses**: the detector finds only 6.7 cuts/min vs 61.3, and 46.4% of frames are near-still vs 29.1%. The per-bar camera changes happen on thin gold lines over a dark background, which fall under the 0.3 scene threshold, and the title holds for about 7 s. Next fix: more hard cuts per bar and a shorter title hold.

The reference was only measured. None of its frames or audio are used. Witch Hat Atelier premiered April 6, 2026, animated by BUG FILMS (Crunchyroll guide, 2026-04-04).

## Memes used, dated and sourced

- **lodi, petmalu, werpa**: syllable-flipped slang listed in Rappler's "16 popular words, phrases loved by Filipinos on social media" (2017-12-20): https://www.rappler.com/technology/social-media/187842-popular-words-social-media-philippines-2017/
- **paqod c acoe**: same Rappler list, which cites a tweet dated 2017-05-31.

## Could not confirm (and where I looked)

- **Your draft image**: measured as a still only (837×427, 56.8% near-black pixels, mean relative luminance 0.045). It has no time axis, so cut, tempo, and loudness rows can't apply to it.
- **The YouTube copy of the trailer**: blocked by a sign-in wall in the sandbox, so I measured the MP4 you uploaded instead.
- **Studio palette and art notes**: not published as data, so the gold, sepia, and crosshatch look is my own design choice, not a measured match.
- **Who reviews this for high stakes**: not named. Tell me who signs off (your adviser or a groupmate). I won't invent one.
