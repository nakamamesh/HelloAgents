#!/usr/bin/env bash
# Rebuild VMP + NOW Cursor skills the OLD CRM way (clone ~/.cursor/skills/crm).
# Run ON the user's Mac (Darwin). Uses CRM enrich_websites.py with identifier renames.
#
# Classic CRM speed: DEPTH=2 RURAL_DEPTH=1 EMAIL_ENRICH_EVERY=25
#   STABLE_SEC=60 TIMEOUT_SEC=600 CONCURRENCY=8 DOCKER_MEM=3500m
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ABORT: this script must run on macOS (Darwin). Got: $(uname -s)" >&2
  exit 1
fi

HOME_DIR="${HOME:-/Users/$(id -un)}"
CRM_SKILL="$HOME_DIR/.cursor/skills/crm"
CRM_SCRIPTS="$CRM_SKILL/scripts"
CRM_ENRICH="$CRM_SCRIPTS/enrich_websites.py"

if [[ ! -f "$CRM_ENRICH" ]]; then
  echo "ABORT: missing CRM enrich at $CRM_ENRICH" >&2
  echo "Clone CRM skill first, then re-run." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
# curl|bash: BASH_SOURCE may be a temp path — fall back to repo-relative / raw fetch
RAW_BASE="${CRM_CLONE_RAW_BASE:-https://raw.githubusercontent.com/nakamamesh/HelloAgents/cursor/vmp-now-crm-clone-54c9/tools/crm-clone}"
TS="$(date +%Y%m%d%H%M%S)"
UID_NUM="$(id -u)"
GUI="gui/${UID_NUM}"

PEER_SCRAPER_REGEX='crm-scraper-|mvn-scraper-|ncu-scraper-|woi-scraper-|lams-scraper-|tred-scraper-|ared-scraper-|cred-scraper-|fred-scraper-|gred-scraper-|ncred-scraper-|scred-scraper-|vmp-scraper-|now-scraper-'

resolve_places() {
  local batch="$1"
  local name="places_${batch}.py"
  local dest="$2"
  if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/$name" ]]; then
    cp "$SCRIPT_DIR/$name" "$dest"
    return 0
  fi
  if [[ -f "$(pwd)/tools/crm-clone/$name" ]]; then
    cp "$(pwd)/tools/crm-clone/$name" "$dest"
    return 0
  fi
  if [[ -f "$(pwd)/$name" ]]; then
    cp "$(pwd)/$name" "$dest"
    return 0
  fi
  echo "Fetching $name from $RAW_BASE ..."
  curl -fsSL "$RAW_BASE/$name" -o "$dest"
}

write_skill_md() {
  local batch="$1"
  local skill="$2"
  local upper prefix states_table query_notes target combined state_csvs
  upper="$(echo "$batch" | tr '[:lower:]' '[:upper:]')"
  if [[ "$batch" == "vmp" ]]; then
    target=224
    combined="vmp.csv"
    state_csvs="virginia.csv / maryland.csv / pennsylvania.csv"
    states_table="| Virginia | 95 counties + 38 independent cities | 133 |
| Maryland | 23 counties + Baltimore City | 24 |
| Pennsylvania | 67 counties | 67 |"
    query_notes="- VA county: \`… {Name} County VA\`
- VA independent city: \`… {City} VA\` (no County)
- MD county: \`… {Name} County MD\`
- MD Baltimore City: \`… Baltimore MD\` (id \`MD:BaltimoreCity\`)
- PA: \`… {Name} County PA\`"
  else
    target=164
    combined="now.csv"
    state_csvs="new_jersey.csv / ohio.csv / west_virginia.csv"
    states_table="| New Jersey | counties | 21 |
| Ohio | counties | 88 |
| West Virginia | counties | 55 |"
    query_notes="- NJ: \`… {Name} County NJ\`
- OH: \`… {Name} County OH\`
- WV: \`… {Name} County WV\`"
  fi
  cat >"$skill/SKILL.md" <<EOF
---
name: ${batch}
description: >-
  Build and grow the ${upper} Real Estate Developers lead list — company,
  website, email, phone, contact — into SQLite and CSV via free county-batched
  Google Maps scraping and website enrichment. Use when the user mentions
  ${upper}, or scraping those states for developers/builders.
disable-model-invocation: true
---

# ${upper} — Real Estate Developers

Free pipeline: county/city Maps queries → dedupe/filter → website email crawl → SQLite + CSV.

## Paths

| What | Path |
|------|------|
| Skill | \`~/.cursor/skills/${batch}/\` |
| Data | \`~/.cursor/skills/${batch}/data/\` |
| Combined CSV | \`~/HelloAgents/${batch}/${combined}\` |
| State CSVs | \`${state_csvs}\` |
| DB | \`~/.cursor/skills/${batch}/data/${batch}.db\` |
| Resume | \`~/.cursor/skills/${batch}/data/places_done.txt\` |

Requires Docker image \`gosom/google-maps-scraper:latest\`.

## CSV columns

\`company,website,email,phone,contact_person,address,county,state,category,rating,reviews,source_query,lat,lon,scraped_at,notes\`

## Scope — ALL ${target} (no skips)

| State | Divisions | Count |
|-------|-----------|-------|
${states_table}

Order: metros first within each state, then remaining places.

## Query wording

${query_notes}

All places run 3 queries: real estate developer / land developer / home builder.

## Docker coexistence

One Maps container at a time. Wait on peer scrapers (\`vmp-scraper-\`, \`now-scraper-\`,
\`crm-scraper-\`, \`mvn-scraper-\`, …). Never kill peers. Shared lock
\`/tmp/helloagents-maps.lock.d\`. Default mem \`${upper}_DOCKER_MEM=3500m\`.

## Run all (resume-safe)

\`\`\`bash
DEPTH=2 CONCURRENCY=8 EMAIL_ENRICH_EVERY=25 \\
  python3 ~/.cursor/skills/${batch}/scripts/run_statewide.py

# or watchdog (LaunchAgent preferred)
nohup caffeinate -dims bash ~/.cursor/skills/${batch}/scripts/watchdog.sh \\
  >> ~/.cursor/skills/${batch}/data/watchdog.log 2>&1 &
\`\`\`

## Status / "update"

\`\`\`bash
python3 ~/.cursor/skills/${batch}/scripts/status.py
\`\`\`

## Speed settings (classic CRM)

- Docker: \`-c 8 -browser-pool-size 1 -pages-per-browser 4\`
- Metros: \`-depth 2\`; rural: \`-depth 1\` via \`RURAL_DEPTH=1\`
- \`EMAIL=0\` on Maps; enrich every ~25 + final
- \`STABLE_SEC=60\` \`TIMEOUT_SEC=600\` \`CONCURRENCY=8\`
- No \`-fast-mode\` without \`-geo\`
- Apple Silicon: \`--platform linux/amd64\`

## Rules

- Free only.
- No rural skips — all ${target}.
- Dedupe on phone + website domain + name + state.
- Drop realtor-only / title / PM noise unless also builder/developer.
- Do not freeze empty emails on enrich.
EOF
}

adapt_batch_scripts() {
  local batch="$1"
  local scripts_dir="$2"
  local upper target states_py state_csv_py
  upper="$(echo "$batch" | tr '[:lower:]' '[:upper:]')"
  if [[ "$batch" == "vmp" ]]; then
    target=224
    states_py='"VA", "MD", "PA"'
    state_csv_py='{"VA": "virginia.csv", "MD": "maryland.csv", "PA": "pennsylvania.csv"}'
  else
    target=164
    states_py='"NJ", "OH", "WV"'
    state_csv_py='{"NJ": "new_jersey.csv", "OH": "ohio.csv", "WV": "west_virginia.csv"}'
  fi

  python3 - "$scripts_dir" "$batch" "$upper" "$target" "$states_py" "$state_csv_py" "$PEER_SCRAPER_REGEX" <<'PY'
import re
import sys
from pathlib import Path

scripts_dir = Path(sys.argv[1])
batch = sys.argv[2]
upper = sys.argv[3]
target = sys.argv[4]
states_py = sys.argv[5]  # e.g. "VA", "MD", "PA"
state_csv_py = sys.argv[6]
peer_regex = sys.argv[7]

# Table renames only in these files (avoid mangling unrelated "crm" words elsewhere)
TABLE_FILES = {"normalize.py", "enrich_websites.py", "status.py"}

# Canonical peer awk/regex fragment used in run_scrape.sh / run_statewide.py
PEER_AWK = peer_regex

def rewrite_text(text: str, path: Path) -> str:
    name = path.name
    # This batch's container prefix (peer lists restored next)
    text = text.replace("crm-scraper-", f"{batch}-scraper-")

    # Env vars
    text = text.replace("CRM_CSV", f"{upper}_CSV")
    text = text.replace("CRM_DB", f"{upper}_DB")
    text = text.replace("CRM_DOCKER_MEM", f"{upper}_DOCKER_MEM")

    # Paths
    text = text.replace("HelloAgents/crm", f"HelloAgents/{batch}")
    text = text.replace(".cursor/skills/crm", f".cursor/skills/{batch}")
    text = text.replace("/skills/crm/", f"/skills/{batch}/")
    text = text.replace("skills/crm/", f"skills/{batch}/")

    # Combined csv / db filenames
    text = text.replace("crm.csv", f"{batch}.csv")
    text = text.replace("crm.db", f"{batch}.db")

    # TARGET
    text = re.sub(r"TARGET\s*=\s*27\b", f"TARGET = {target}", text)
    text = re.sub(r'TARGET",\s*"27"', f'TARGET", "{target}"', text)
    text = re.sub(r"TARGET:-27", f"TARGET:-{target}", text)

    # State tuples / lists CT RI MA → batch states
    text = re.sub(
        r'\(\s*"CT"\s*,\s*"RI"\s*,\s*"MA"\s*\)',
        f"({states_py})",
        text,
    )
    text = re.sub(
        r'\[\s*"CT"\s*,\s*"RI"\s*,\s*"MA"\s*\]',
        f"[{states_py}]",
        text,
    )
    text = re.sub(
        r'for st in \(\s*"CT"\s*,\s*"RI"\s*,\s*"MA"\s*\)',
        f"for st in ({states_py})",
        text,
    )
    text = re.sub(
        r'\{\s*"CT"\s*,\s*"RI"\s*,\s*"MA"\s*\}',
        "{" + states_py + "}",
        text,
    )
    text = re.sub(
        r"\{\s*'CT'\s*,\s*'RI'\s*,\s*'MA'\s*\}",
        "{" + states_py.replace('"', "'") + "}",
        text,
    )
    text = re.sub(
        r"CT\|RI\|MA",
        states_py.replace('"', "").replace(", ", "|"),
        text,
    )
    text = re.sub(r"\bCT/RI/MA\b", states_py.replace('"', "").replace(", ", "/"), text)
    text = re.sub(
        r'state_order = \(\s*"CT"\s*,\s*"RI"\s*,\s*"MA"\s*\)',
        f"state_order = ({states_py})",
        text,
    )

    # STATE_CSV mapping block (normalize / enrich)
    text = re.sub(
        r"STATE_CSV\s*=\s*\{[^}]*connecticut\.csv[^}]*\}",
        f"STATE_CSV = {state_csv_py}",
        text,
        flags=re.S,
    )
    # enrich STATE_CSV_BY_BATCH style
    text = re.sub(
        r'"crm"\s*:\s*\{[^}]*connecticut\.csv[^}]*\}',
        f'"{batch}": {state_csv_py}',
        text,
        flags=re.S,
    )

    # Peer wait lists: any X-scraper-|Y-scraper- chain → full peer regex
    # (restores crm-scraper- as a peer; adds vmp-scraper-|now-scraper-)
    peer_group = "|".join(
        p[: -len("-scraper-")] if p.endswith("-scraper-") else p.rstrip("|")
        for p in PEER_AWK.split("|")
        if p
    )
    text = re.sub(
        r"(?:[A-Za-z]+-scraper-\|)+[A-Za-z]+-scraper-",
        PEER_AWK,
        text,
    )
    text = re.sub(
        r"\((?:[a-z]+\|)+[a-z]+\)-scraper-",
        f"({peer_group})-scraper-",
        text,
    )

    # Branding / labels
    text = re.sub(r"\bCRM\b", upper, text)
    # Remaining path-ish lowercase crm → batch (careful: after CRM_ already done)
    text = text.replace("/crm/", f"/{batch}/")
    text = text.replace(f'"{batch}"', f'"{batch}"')  # no-op keep

    # SQLite table name only in designated files
    if path.name in TABLE_FILES:
        # CREATE TABLE / FROM / INTO / UPDATE / table_info
        text = re.sub(r"\bCREATE TABLE IF NOT EXISTS crm\b", f"CREATE TABLE IF NOT EXISTS {batch}", text)
        text = re.sub(r"\bCREATE TABLE crm\b", f"CREATE TABLE {batch}", text)
        text = re.sub(r"\bFROM crm\b", f"FROM {batch}", text)
        text = re.sub(r"\bINTO crm\b", f"INTO {batch}", text)
        text = re.sub(r"\bUPDATE crm\b", f"UPDATE {batch}", text)
        text = re.sub(r"\btable_info\(crm\)", f"table_info({batch})", text)
        text = re.sub(r"\bEXISTS crm\b", f"EXISTS {batch}", text)
        text = re.sub(r"'crm'", f"'{batch}'", text)
        text = re.sub(r'"crm"', f'"{batch}"', text)

    # Fix statewide_running pgrep path
    text = re.sub(
        r'pgrep -f "[^"]*crm/scripts/run_statewide',
        f'pgrep -f "{batch}/scripts/run_statewide',
        text,
    )
    text = re.sub(
        r"pgrep -f '[^']*crm/scripts/run_statewide",
        f"pgrep -f '{batch}/scripts/run_statewide",
        text,
    )

    # Labels in comments / docstrings already handled via CRM→UPPER

    # Depth defaults: keep classic CRM (2 / 60 / 600 / 25) — undo any depth-1 hacks
    text = re.sub(r'os\.environ\.get\("DEPTH",\s*"1"\)', 'os.environ.get("DEPTH", "2")', text)
    text = re.sub(r"DEPTH:-1\b", "DEPTH:-2", text)
    text = re.sub(r'DEPTH",\s*"1"', 'DEPTH", "2"', text)
    text = re.sub(r"STABLE_SEC:-45\b", "STABLE_SEC:-60", text)
    text = re.sub(r'TIMEOUT_SEC:-480\b', "TIMEOUT_SEC:-600", text)
    text = re.sub(r"EMAIL_ENRICH_EVERY:-5\b", "EMAIL_ENRICH_EVERY:-25", text)
    text = re.sub(r'EMAIL_ENRICH_EVERY",\s*"5"', 'EMAIL_ENRICH_EVERY", "25"', text)
    text = re.sub(r'STABLE_SEC",\s*"45"', 'STABLE_SEC", "60"', text)
    text = re.sub(r'TIMEOUT_SEC",\s*"480"', 'TIMEOUT_SEC", "600"', text)

    return text

for path in sorted(scripts_dir.iterdir()):
    if not path.is_file():
        continue
    if path.suffix not in {".py", ".sh", ".md", ".txt"} and path.name not in {
        "run_scrape.sh",
        "watchdog.sh",
        "keeper.sh",
    }:
        # still rewrite unknown text scripts
        pass
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        continue
    new = rewrite_text(raw, path)
    if new != raw:
        path.write_text(new, encoding="utf-8")
        print(f"  adapted {path.name}")

# Force peer list injection if still missing vmp/now after rewrite
for path in scripts_dir.glob("*"):
    if not path.is_file():
        continue
    try:
        t = path.read_text(encoding="utf-8")
    except Exception:
        continue
    if "scraper-" not in t:
        continue
    orig = t
    t = re.sub(
        r"(?:[A-Za-z]+-scraper-\|)+[A-Za-z]+-scraper-",
        peer_regex,
        t,
    )
    if t != orig:
        path.write_text(t, encoding="utf-8")
        print(f"  peer-injected {path.name}")

# Keep a single statewide_running() in watchdog.sh
wd = scripts_dir / "watchdog.sh"
if wd.exists():
    t = wd.read_text(encoding="utf-8")
    # collapse duplicate function definitions; keep last body rewritten to batch path
    fn = (
        "statewide_running() {\n"
        f'  pgrep -f "{batch}/scripts/run_statewide\\\\.py" >/dev/null 2>&1\n'
        "}\n"
    )
    t2 = re.sub(
        r"statewide_running\(\)\s*\{[^}]*\}",
        "__STATEWIDE_RUNNING_PLACEHOLDER__",
        t,
        flags=re.S,
    )
    # keep only the first placeholder, drop extras
    seen = False
    lines = []
    for line in t2.splitlines(True):
        if "__STATEWIDE_RUNNING_PLACEHOLDER__" in line:
            if seen:
                continue
            seen = True
            lines.append(fn)
            # if the placeholder was only part of the line, skip remainder of that line
            continue
        lines.append(line)
    t2 = "".join(lines)
    if t2 != t:
        wd.write_text(t2, encoding="utf-8")
        print("  watchdog statewide_running collapsed")
PY
}

write_plist() {
  local batch="$1"
  local kind="$2"  # watchdog | keeper
  local skill="$HOME_DIR/.cursor/skills/$batch"
  local upper
  upper="$(echo "$batch" | tr '[:lower:]' '[:upper:]')"
  local pl="$HOME_DIR/Library/LaunchAgents/com.helloagents.${batch}.${kind}.plist"
  local script throttle
  if [[ "$kind" == "watchdog" ]]; then
    script="$skill/scripts/watchdog.sh"
    throttle=15
  else
    script="$skill/scripts/keeper.sh"
    throttle=30
  fi
  mkdir -p "$HOME_DIR/Library/LaunchAgents"
  if [[ "$kind" == "watchdog" ]]; then
    cat >"$pl" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>EnvironmentVariables</key>
	<dict>
		<key>CONCURRENCY</key>
		<string>8</string>
		<key>COUNTY_TIMEOUT</key>
		<string>1100</string>
		<key>DEPTH</key>
		<string>2</string>
		<key>EMAIL_ENRICH_EVERY</key>
		<string>25</string>
		<key>HOME</key>
		<string>${HOME_DIR}</string>
		<key>PATH</key>
		<string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
		<key>${upper}_CSV</key>
		<string>${HOME_DIR}/HelloAgents/${batch}/${batch}.csv</string>
		<key>${upper}_DB</key>
		<string>${HOME_DIR}/.cursor/skills/${batch}/data/${batch}.db</string>
		<key>${upper}_DOCKER_MEM</key>
		<string>3500m</string>
		<key>INACTIVITY</key>
		<string>60s</string>
		<key>ORPHAN_AGE_SEC</key>
		<string>600</string>
		<key>RURAL_DEPTH</key>
		<string>1</string>
		<key>STABLE_SEC</key>
		<string>60</string>
		<key>TIMEOUT_SEC</key>
		<string>600</string>
	</dict>
	<key>KeepAlive</key>
	<true/>
	<key>Label</key>
	<string>com.helloagents.${batch}.${kind}</string>
	<key>ProgramArguments</key>
	<array>
		<string>/usr/bin/caffeinate</string>
		<string>-dims</string>
		<string>/bin/bash</string>
		<string>${script}</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>StandardErrorPath</key>
	<string>${skill}/data/launchd.${kind}.err.log</string>
	<key>StandardOutPath</key>
	<string>${skill}/data/launchd.${kind}.out.log</string>
	<key>ThrottleInterval</key>
	<integer>${throttle}</integer>
	<key>WorkingDirectory</key>
	<string>${skill}</string>
</dict>
</plist>
EOF
  else
    cat >"$pl" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>EnvironmentVariables</key>
	<dict>
		<key>HOME</key>
		<string>${HOME_DIR}</string>
		<key>PATH</key>
		<string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
		<key>${upper}_CSV</key>
		<string>${HOME_DIR}/HelloAgents/${batch}/${batch}.csv</string>
		<key>${upper}_DB</key>
		<string>${HOME_DIR}/.cursor/skills/${batch}/data/${batch}.db</string>
		<key>${upper}_DOCKER_MEM</key>
		<string>3500m</string>
	</dict>
	<key>KeepAlive</key>
	<true/>
	<key>Label</key>
	<string>com.helloagents.${batch}.${kind}</string>
	<key>ProgramArguments</key>
	<array>
		<string>/usr/bin/caffeinate</string>
		<string>-dims</string>
		<string>/bin/bash</string>
		<string>${script}</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>StandardErrorPath</key>
	<string>${skill}/data/launchd.${kind}.err.log</string>
	<key>StandardOutPath</key>
	<string>${skill}/data/launchd.${kind}.out.log</string>
	<key>ThrottleInterval</key>
	<integer>${throttle}</integer>
	<key>WorkingDirectory</key>
	<string>${skill}</string>
</dict>
</plist>
EOF
  fi
  echo "wrote $pl"
}

patch_existing_peer_skills() {
  # Minimal: ensure other skills wait on vmp/now scrapers
  local skill scripts f
  for skill in crm mvn ncu woi lams tred ared cred fred gred ncred scred; do
    scripts="$HOME_DIR/.cursor/skills/$skill/scripts"
    [[ -d "$scripts" ]] || continue
    for f in "$scripts/run_scrape.sh" "$scripts/run_statewide.py" "$scripts/watchdog.sh"; do
      [[ -f "$f" ]] || continue
      if grep -q 'scraper-' "$f" 2>/dev/null; then
        if ! grep -q 'vmp-scraper-' "$f" 2>/dev/null; then
          perl -i -pe 's/(crm-scraper-\|)/vmp-scraper-|now-scraper-|$1/g; s/(crm\|mvn)/vmp|now|$1/g' "$f" || true
          echo "  peer-patched $f"
        elif ! grep -q 'now-scraper-' "$f" 2>/dev/null; then
          perl -i -pe 's/vmp-scraper-/vmp-scraper-|now-scraper-/g' "$f" || true
          echo "  peer-patched now into $f"
        fi
      fi
    done
  done
}

fresh_start_data() {
  local batch="$1"
  local skill="$HOME_DIR/.cursor/skills/$batch"
  local data="$skill/data"
  local csv_dir="$HOME_DIR/HelloAgents/$batch"
  mkdir -p "$data" "$csv_dir"

  : >"$data/places_done.txt"
  rm -f "$data/enrich_done.txt" "$data/places_empty.txt"

  if [[ -f "$data/${batch}.db" ]]; then
    cp "$data/${batch}.db" "$data/${batch}.db.bak.$TS"
    rm -f "$data/${batch}.db"
    echo "  backed up+removed ${batch}.db"
  fi
  if [[ -f "$csv_dir/${batch}.csv" ]]; then
    cp "$csv_dir/${batch}.csv" "$csv_dir/${batch}.csv.bak.$TS"
    rm -f "$csv_dir/${batch}.csv"
    echo "  backed up+removed ${batch}.csv"
  fi
  # optional per-state csvs — leave if present but combined is gone for clean rescan
}

build_batch() {
  local batch="$1"
  local skill="$HOME_DIR/.cursor/skills/$batch"
  local upper
  upper="$(echo "$batch" | tr '[:lower:]' '[:upper:]')"

  echo
  echo "======== building ${upper} ========"

  if [[ -d "$skill" ]]; then
    local bak="$HOME_DIR/.cursor/skills/${batch}.bak.${TS}"
    echo "Backing up existing skill → $bak"
    rm -rf "$bak"
    cp -R "$skill" "$bak"
  fi

  mkdir -p "$skill/scripts" "$skill/data" "$HOME_DIR/HelloAgents/$batch"

  echo "Copying ALL CRM scripts → $skill/scripts/"
  # Do not copy CRM places.py — we install batch places separately
  local f
  for f in "$CRM_SCRIPTS"/*; do
    [[ -e "$f" ]] || continue
    local base
    base="$(basename "$f")"
    if [[ "$base" == "places.py" ]]; then
      continue
    fi
    cp "$f" "$skill/scripts/$base"
  done

  echo "Adapting identifiers for $batch ..."
  adapt_batch_scripts "$batch" "$skill/scripts"

  echo "Installing places.py for $batch ..."
  resolve_places "$batch" "$skill/scripts/places.py"

  write_skill_md "$batch" "$skill"

  chmod +x "$skill/scripts/"*.sh 2>/dev/null || true
  chmod +x "$skill/scripts/"*.py 2>/dev/null || true

  echo "Verifying places.py ..."
  python3 "$skill/scripts/places.py"
  python3 -c "import py_compile; py_compile.compile(r'$skill/scripts/places.py', doraise=True)"

  echo "Checking table/path renames ..."
  local leftover
  leftover="$(grep -E 'table_info\(crm\)|FROM crm|UPDATE crm|INTO crm|CREATE TABLE IF NOT EXISTS crm' \
    "$skill/scripts/normalize.py" "$skill/scripts/enrich_websites.py" "$skill/scripts/status.py" 2>/dev/null || true)"
  if [[ -n "$leftover" ]]; then
    echo "WARN: leftover CRM table refs:" >&2
    echo "$leftover" >&2
  fi
  if ! grep -q "vmp-scraper-" "$skill/scripts/run_statewide.py" 2>/dev/null \
     || ! grep -q "now-scraper-" "$skill/scripts/run_statewide.py" 2>/dev/null; then
    echo "WARN: run_statewide.py missing vmp/now peer scraper tokens" >&2
  fi

  fresh_start_data "$batch"

  write_plist "$batch" "watchdog"
  write_plist "$batch" "keeper"
}

reload_launchagent() {
  local batch="$1"
  local kind="$2"
  local label="com.helloagents.${batch}.${kind}"
  local pl="$HOME_DIR/Library/LaunchAgents/${label}.plist"
  echo "Reloading $label ..."
  launchctl bootout "${GUI}/${label}" 2>/dev/null || true
  # legacy load path
  launchctl unload "$pl" 2>/dev/null || true
  if [[ -f "$pl" ]]; then
    launchctl bootstrap "$GUI" "$pl" 2>/dev/null || launchctl load -w "$pl"
    launchctl enable "${GUI}/${label}" 2>/dev/null || true
    launchctl kickstart -k "${GUI}/${label}" 2>/dev/null || true
  fi
}

# ---- main ----
echo "CRM source: $CRM_SCRIPTS"
echo "Peer regex: $PEER_SCRAPER_REGEX"

# Order: now, then vmp (per requirements)
for batch in now vmp; do
  build_batch "$batch"
done

echo
echo "======== patching peer skills to wait on vmp/now ========"
patch_existing_peer_skills

echo
echo "======== bootout / bootstrap LaunchAgents ========"
for batch in now vmp; do
  reload_launchagent "$batch" "watchdog"
  reload_launchagent "$batch" "keeper"
done

echo
echo "======== status ========"
python3 "$HOME_DIR/.cursor/skills/now/scripts/status.py" || true
echo
python3 "$HOME_DIR/.cursor/skills/vmp/scripts/status.py" || true

echo
echo "DONE. Classic CRM speed (DEPTH=2, EMAIL_ENRICH_EVERY=25, STABLE_SEC=60)."
echo "Watchdogs will alternate Docker with peers. Do not kill peer scrapers."
echo "  tail -f ~/.cursor/skills/now/data/watchdog.log"
echo "  tail -f ~/.cursor/skills/vmp/data/watchdog.log"
