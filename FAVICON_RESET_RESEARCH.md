# Safari Favicon Reset Tool — Research Summary

## Problem
Safari caches favicons separately from HTTP cache. Clearing site data, cache, and hard reloads have no effect. This is particularly painful during local development (e.g., `localhost:5173`).

## Storage Architecture

### File Locations
```
~/Library/Safari/Favicon Cache/
├── favicons.db          # SQLite database (with WAL files)
├── favicons.db-shm
├── favicons.db-wal
├── favicons.db-lock
└── favicons/            # Raw ICO/PNG files (~1396 files)
    ├── 000809DD...
    ├── 002FE9D3...
    └── ...
```

**Permission requirement**: Full Disk Access needed to modify this folder.

### Database Schema

```sql
-- Maps page URLs to a favicon UUID
CREATE TABLE page_url (
  url  TEXT NOT NULL UNIQUE,
  uuid TEXT NOT NULL
);

-- Maps UUID to favicon metadata
CREATE TABLE icon_info (
  uuid                        TEXT PRIMARY KEY NOT NULL,
  url                         TEXT NOT NULL,
  timestamp                   INTEGER,
  width                       INTEGER DEFAULT 0,
  height                      INTEGER DEFAULT 0,
  has_generated_representations INTEGER DEFAULT 0
);

-- Blocklist of rejected favicons
CREATE TABLE rejected_resources (
  page_url  TEXT NOT NULL,
  icon_url  TEXT NOT NULL,
  timestamp INTEGER,
  UNIQUE(page_url, icon_url)
);

CREATE TABLE database_info (
  key   TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
);
```

## Critical Insight
**Deleting DB records alone is insufficient.** Safari falls back to reading favicon files directly from `favicons/` even when DB entries are missing.

**Both must be deleted:**
1. DB rows in `page_url` and `icon_info`
2. The corresponding file in `favicons/`

## File Naming — SOLVED ✅ (2026-06-14)
**`favicon filename = UPPERCASE( MD5( icon_info.uuid ) )`**

Cracked by `crack_hash.sh`: tested 14 hypotheses against 300 live (uuid,url)→file
pairs. `md5(uuid string)` scored **300/300**; every other hypothesis scored 0.
The uuid is hashed exactly as stored (uppercase, with dashes, e.g.
`3DD517DE-BAC0-4D89-A118-B039A399DB4F`); md5 is lowercase, filenames are uppercase.

Consequences:
- Legitimate file set = `{ MD5(uuid) : uuid in icon_info }`.
- **Orphan = any file in `favicons/` not in that set** → safe to delete
  (see `find_orphans.sh`).
- VERIFIED: 1392 expected vs 1393 on disk = exactly **1 orphan**, the user's
  `0A3927AB…`. CORRECTION: this orphan was NOT a Safari leak — it was created by
  OUR `reset_full.sh` (DB-only delete removed the `icon_info` row but left the
  file). Safari's own counts were otherwise clean. ⇒ The DB-only reset is exactly
  what leaks orphans; the per-site tool MUST delete `MD5(uuid)` files too.
- **Per-site file deletion**: for the target's uuids (from `page_url`), compute
  `MD5(uuid)` and delete those files BEFORE deleting the rows.

(Original framing below kept for history.)

### (historical) File Naming — Open Problem
Files in `favicons/` are named by an unknown hash algorithm:
- Not named by UUID
- No DB column links UUID → filename
- ~1396 files in folder; ~1395 DB records (strong 1:1 mapping)
- **Unknown algorithm**: candidates are hash of favicon URL, page URL, or image data itself

### Next Step to Reverse-Engineer
1. Find a known favicon URL (e.g., `http://localhost:5173/favicon.png`)
2. Locate its file in `favicons/` visually (Finder, sort by date)
3. Test common hashes (MD5, SHA1, SHA256) against the URL string
4. Identify which produces the filename

### Hash — Ruled Out (2026-06-14)
Known sample: file `0A3927ABF217E238FFAC4482E90FA01D` (32 hex = 128-bit) is an old
localhost favicon-dark.ico image (user renamed to .ico, confirmed visually).
Filenames are 32-hex UPPERCASE, no extension; also valid UUID shape (8-4-4-4-12).

Tested against this filename — NONE matched:
- md5 / sha1[:32] / sha256[:32] of the icon URL (incl. `?v=` variants, no-query, host-only)
- md5 / sha1 / sha256 of the UUID strings we had
- md5(content)=`757894d7…` / sha1 / sha256 of FILE BYTES → so NOT content-addressed

Still untested (now in `crack_hash.sh`, run against ~300 live rows): UTF-16LE/BE/BOM
encodings of the URL (Apple hashes NSString/CFString as UTF-16 — prime suspect),
+ uuid-as-filename across many rows. The cracker scores each hypothesis by how many
live (url→file) pairs it reproduces; correct algo ≈ 100%.

NOTE: (superseded) this file became an orphan because OUR DB-only `reset_full.sh`
deleted its `icon_info` row but not the file — self-inflicted, not a Safari leak.
See the SOLVED section above. Reinforces that per-site reset must delete the file.

## Working Manual Fix
Quit Safari fully, then:

```bash
# Find entries for a domain
sqlite3 ~/Library/Safari/Favicon\ Cache/favicons.db "
SELECT p.url, i.url, i.uuid
FROM page_url p
JOIN icon_info i ON p.uuid = i.uuid
WHERE p.url LIKE 'http://localhost:5173%';
"

# Delete DB entries
sqlite3 ~/Library/Safari/Favicon\ Cache/favicons.db "
DELETE FROM page_url WHERE url LIKE 'http://localhost:5173%';
DELETE FROM icon_info WHERE uuid NOT IN (SELECT uuid FROM page_url);
"

# Delete corresponding files in favicons/ (algorithm TBD)
```

## Project Goals
- Open-source tool (MIT license)
- Developers can reset favicons without using Terminal
- Target: macOS, Safari 14+

## Implementation Constraints
- Safari must be fully quit before modifying `favicons.db` (WAL mode — concurrent writes unsafe)
- OR use SQLite WAL-safe transaction (`BEGIN EXCLUSIVE`) but risky
- Full Disk Access required from user (one-time grant)

## WebKit Icon Update Logic (from source)
Source: legacy `WebCore::IconDatabase` / `IconLoader` (modern `favicons.db` is a rewrite
but very likely shares the timestamp-driven model — schema still has `icon_info.timestamp`).

### The freshness decision — `synchronousLoadDecisionForIconURL()`
On **every page load**, WebKit runs exactly one check:
```cpp
return currentTime() - icon->getTimestamp() > iconExpirationTime
       ? IconLoadYes : IconLoadNo;
static const int iconExpirationTime = 60*60*24*4;  // 4 DAYS
```
- `now - timestamp <= 4 days` → `IconLoadNo` (use cache, never hits network)
- `now - timestamp >  4 days` → `IconLoadYes` (fetch)
- import not done → `IconLoadUnknown`

No ETag check, no content hashing, no `<link rel=icon>` change detection at this layer.
**The entire freshness rule is a 4-day timer keyed on `icon_info.timestamp`.**

### The second gate — HTTP cache
Even on `IconLoadYes`, `IconLoader::startLoading()` issues a normal `CachedResourceRequest`
with **no cache override** (no `ReloadIgnoringCacheData`). So the re-fetch still goes through
the standard HTTP cache — a `304` or fresh `max-age` means bytes don't change.
Commits only on HTTP **200–299** and **non-PDF** (sniffs magic numbers, rejects PDFs).

### Why dev favicons appear stuck
1. 4-day timer → WebKit usually doesn't even try for up to 4 days.
2. Even past 4 days → dev server caching headers can serve the old image.
Hard reload doesn't help: favicon path is governed by the IconDatabase timer, not the
page reload cache policy.

### Implication: two possible reset strategies
- **Delete** the row (+ file) → forces `IconLoadYes` next visit. Needs filename-hash solved
  for surgical per-site mode; whole-folder nuke avoids the hash entirely.
- **`timestamp = 0` trick** (UNVERIFIED on modern Safari): set `icon_info.timestamp = 0`
  for the target row → forces expiry → re-fetch, WITHOUT solving the filename hash.
  Cleaner surgical mode IF modern Safari still honors the timestamp like legacy. VERIFY.

Sources:
- https://github.com/nickdiego/webkitnix/blob/master/Source/WebCore/loader/icon/IconDatabase.cpp
- https://github.com/nickdiego/webkitnix/blob/master/Source/WebCore/loader/icon/IconLoader.cpp

## EXPERIMENT RESULTS (2026-06-14) — key correction

### Exp #1: `timestamp = 0` trick → FAILED
Set `icon_info.timestamp = 0` for all rows mapped to localhost:5173. Relaunched
Safari: icon did NOT update, and **no favicon network request fired at all**.

### Why it failed — the real mechanism
The cached entries pointed at `/favicon-dark.ico?v=...`, but the app currently
served at :5173 (a *different* app, "Domic") serves entirely different favicon
URLs: `/favicon.ico`, `/favicon.svg`, `/favicon-32x32.png`, etc. It never
references `favicon-dark.ico`.

**Safari serves a page's favicon via the `page_url` mapping (page URL → icon
UUID). While that mapping exists, Safari uses the mapped icon and does NOT
re-read the page's `<link rel=icon>` tags — so it never requests the new
favicon.** That is why no network request fired.

The 4-day `timestamp` expiry is therefore NOT the lever for this case: expiry
only forces a re-fetch if the page still requests that icon URL. The real lever
is the **`page_url` mapping** — it must be deleted so Safari re-evaluates the
page and fetches the current favicon.

### Exp #2: delete page_url + orphaned icon_info → PARTIAL
After deleting the `page_url` mapping + orphaned `icon_info` for the target:
- Old icon NO longer shown (mapping deletion worked)
- BUT new favicon did NOT load
- Safari showed a generated "L" letter placeholder (`has_generated_representations`)

### Exp #2 diagnosis: `rejected_resources` is the real blocker ⭐
Inspecting the DB revealed the target's current favicon URLs
sit in the **`rejected_resources` table** — Safari's favicon BLOCKLIST / negative
cache. The whole favicon lineage of the app was there, each iteration rejected:
`favicon.png?v=1`, `favicon-v1.png`, `favicon.png`, `vite.svg`, and most recently
`http://localhost:5173 → http://localhost:5173/favicon.ico`.

**Once an icon URL is in `rejected_resources`, Safari STOPS RETRYING IT — even
after the server serves it correctly (curl confirmed /favicon.ico returns a valid
200 image/x-icon right now).** The blocklist is sticky. This — not the file cache
in `favicons/` — is the dev-hell mechanism.

This CORRECTS the earlier "critical insight": the immediate blocker is NOT the
file fallback; it is `rejected_resources`. Deleting page_url + icon_info alone
leaves the blocklist intact, so Safari renders a generated letter placeholder.

### The reset recipe = THREE tables (no file deletion, no hash needed)
Delete the target's rows from:
1. `page_url`           — page → icon mapping
2. `rejected_resources` — negative cache / blocklist  ⬅ the missing piece
3. `icon_info`          — orphaned metadata

If the current favicon loads after this, the entire tool is just these DELETEs —
the unknown filename-hash problem may never need solving.

### Exp #3: full three-table reset → ✅ VERIFIED WORKING (2026-06-14)
Ran `reset_full.sh` (clear page_url + rejected_resources + orphaned icon_info),
relaunched Safari, opened localhost:5173 in a fresh tab: **the current favicon
loaded correctly.**

## CONCLUSION — the tool is three DELETEs
A per-site Safari favicon reset requires ONLY:
```sql
DELETE FROM page_url           WHERE url      LIKE '<target>%';
DELETE FROM rejected_resources WHERE page_url LIKE '<target>%';
DELETE FROM icon_info          WHERE uuid NOT IN (SELECT uuid FROM page_url);
```
Preconditions: Safari fully quit; process has Full Disk Access; back up first.

### Problems from the original plan that turned out to be MOOT
- ❌ **Filename-hash reverse-engineering** (favicon URL → file in `favicons/`):
  NOT NEEDED. We never delete files; Safari re-fetches on next load.
- ❌ **"Safari falls back to reading files from `favicons/`"**: did not occur in
  practice. The blocker was `rejected_resources`, not the file cache.
- ❌ **Native messaging / Swift host / Safari extension**: not required for the
  core fix. A plain CLI with Full Disk Access does the whole job.

### What actually matters for the CLI
1. Guard: refuse to run while Safari is running (WAL safety).
2. Full Disk Access setup/UX (one-time grant to the terminal or the CLI binary).
3. Back up favicons.db before writing.
4. The three DELETEs, parameterized by target URL prefix.
5. Optional `--all` nuke mode (delete whole folder) as a bulletproof fallback.

## SOFT MODE experiment (2026-06-14) — works for updates, WORSENS orphans ⭐
Isolated test: zeroed `icon_info.timestamp` for localhost:5173 (current favicon
cached, mapping intact), relaunched Safari, loaded the page, quit, re-checked.

Result — Safari DID re-fetch (soft expiry works for updates), BUT:
| stage        | uuid        | timestamp |
| BEFORE set   | 5C277CD4…   | 803173457 |
| AFTER set    | 5C277CD4…   | 0         |
| after reload | 28F6A44A…   | 803175619 (fresh) |

Safari minted a **NEW uuid** (28F6A44A), wrote a new icon_info row + new file, and
re-pointed page_url to it.

### CORRECTED by `gc_audit.sh` — Safari SELF-CLEANS (no orphan!)
Audit of the old uuid `5C277CD4`: `icon_info=0, page_url=0, file=no`. Safari
**deleted the old row AND the old file** when it re-fetched. And **row-orphans = 0
of 1392** total — the DB has ZERO stale/unreferenced icons.

(An earlier draft here claimed soft mode "worsens orphans / is the root cause of
bloat." That was WRONG — refuted by this audit. Kept only as a note.)

### Corrected implications
- ✅ Expiring `timestamp = 0` is a reliable, NON-DESTRUCTIVE re-fetch trigger for a
  still-referenced favicon. Caveat: HTTP cache still gates whether bytes change.
- ✅ Safari handles the lifecycle correctly: on re-fetch it deletes the superseded
  row+file. Soft mode leaves NO orphan. It is the CLEANEST per-site approach.
- ✅ The cache is NOT bloated with orphans. ~1392 files ≈ 1392 live icons; every
  file maps to a referenced row. Normal, not cruft.
- ⚠️ The ONLY orphan we ever found (`0A3927AB`) was created by OUR hard-delete
  (`reset_full.sh` removed rows but not the file). i.e. the DELETE path is what
  risks orphans; SOFT mode does not.

### Revised tool design — prefer SOFT, delete as fallback
- `refaver --site <url>` (default = soft): set `icon_info.timestamp = 0` for the
  target's uuids AND clear `rejected_resources` for the target (to unblock a
  renamed/blocklisted favicon). Then Safari, on next load, re-fetches the current
  favicon and self-cleans the old row+file. No MD5/file math needed in this path.
- `--hard` fallback: the full 3-table delete + `MD5(uuid)` file delete, for when
  soft doesn't take (e.g., if expiry is ever ignored).
- `--gc`: orphan sweep (file-orphans via `find_orphans.sh`; row-orphans via
  `gc_audit.sh`). Mostly needed to clean up messes left by OTHER hard-delete tools,
  since Safari itself keeps the store tidy.

### Soft vs the hard case — VERIFIED ✅ (2026-06-14)
Staged the stuck state (`stage_hard.sh`: cleared mapping + blocklisted all of the
page's candidate favicon URLs). Safari showed the "L" placeholder (genuine stuck).
Then `recover_soft.sh` — clearing `rejected_resources` + expiring timestamps, with
**NO page_url/icon_info/file deletion** — and Safari loaded the real favicon.
⇒ Clearing the blocklist is the operative fix; soft mode covers the rename/blocklist
case too. User-confirmed visually: "L stuck, then fixed."

### Safari GARBAGE-COLLECTS orphans on launch — VERIFIED ✅
After staging orphaned `28F6A44A`'s file (row deleted, file left) and with the old
`0A3927AB` orphan still present, a later Safari launch left the store at a perfect
1392 rows ↔ 1392 files, **0 orphans** — user confirmed they did NOT delete the files
manually. So Safari sweeps favicon files with no DB row on launch. CAVEAT: timing is
unpredictable — `0A3927AB` survived several earlier launches before this sweep, so
GC is eventual, not immediate. (Revises the earlier "Safari leaves orphans" note.)

## FINAL DESIGN — soft-first, validated end to end
- **`refaver --site <url>` (default, SOFT, non-destructive):**
  ```sql
  DELETE FROM rejected_resources WHERE page_url LIKE '<url>%';
  UPDATE icon_info SET timestamp = 0
    WHERE uuid IN (SELECT uuid FROM page_url WHERE url LIKE '<url>%');
  ```
  Safari then re-fetches the current favicon on next load and self-cleans the old
  row+file. No MD5/file math in this path. Covers every case we hit.
- **`--hard` fallback:** full 3-table delete + delete `MD5(uuid)` files. Rarely
  needed; use if soft ever fails to take.
- **`--gc` (optional safety net):** sweep file-orphans (`find_orphans.sh`) and
  row-orphans (`gc_audit.sh`). Mostly redundant since Safari GCs eventually, but
  useful to force-clean immediately or after other tools' hard deletes.
- **`--all` (nuke):** delete the whole `Favicon Cache/` folder; Safari rebuilds.
- Always: require Safari QUIT, need Full Disk Access, back up `favicons.db` first.

Filename algorithm `UPPERCASE(MD5(uuid))` is only needed for `--hard`/`--gc`, not
the default soft path.

RESEARCH COMPLETE. Implemented as the Python `refaver` CLI in `cli/`.

## Is quitting Safari necessary? — TESTED (2026-06-15)
Ran the soft-reset SQL against the REAL db WHILE Safari was running
(mirroring the tool: BEGIN EXCLUSIVE + busy_timeout=5000):
- Write SUCCEEDED (`write-ok`), `PRAGMA integrity_check` = `ok` → no lock, no
  corruption. SQLite WAL + exclusive txn handles concurrent access as designed.
- Reloading the tab (without quitting Safari) re-fetched the favicons → the change
  takes effect live.

⇒ **Quitting Safari is NOT necessary for the soft reset** — neither for safety nor
effectiveness. The tool now relaxes the guard: `reset` (soft) runs with Safari open
and prints "reload the tab to see it". FILE-deleting ops (`--hard`, `gc`, `nuke`)
were NOT tested with Safari live, so they conservatively still require a quit.

## FDA is MANDATORY — verified (2026-06-14)
Tested db access from a process WITHOUT Full Disk Access (Claude.app shell):
- `ls` the folder → `Operation not permitted`
- `ls -l` the db file by exact path → WORKS (can stat: size/perms/date)
- `sqlite3 <db> "SELECT ..."` → `Error: unable to open database: authorization denied`

⇒ macOS TCC blocks file-CONTENT access (open/read/write), not merely directory
listing. Exact path + world-readable Unix perms do NOT help. SQLite cannot connect
without FDA. So even the soft reset REQUIRES Full Disk Access — no way around it.
Deployment implication: either (a) CLI + instruct user to grant Terminal FDA, or
(b) ship a notarized .app that owns its own FDA grant.

## Environment Blockers Observed (2026-06-14)
- The shell running the CLI does NOT have Full Disk Access by default:
  `ls "~/Library/Safari/Favicon Cache/"` → **"Operation not permitted"** (macOS TCC).
  The terminal app (or the CLI binary itself) must be added to
  System Settings → Privacy & Security → Full Disk Access.
- Safari must be fully quit before touching the DB.
