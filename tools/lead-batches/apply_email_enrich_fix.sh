#!/usr/bin/env bash
# Apply email-enrich fix for NOW + VMP on the Mac (skills under ~/.cursor/skills).
# Safe while Maps scrapers run — enrich is separate from Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/enrich_websites.py"
HOME_DIR="${HOME:-/Users/$(id -un)}"
RAW_BASE="${LEAD_BATCH_RAW_BASE:-https://raw.githubusercontent.com/nakamamesh/HelloAgents/cursor/fix-vmp-now-email-enrich-54c9/tools/lead-batches}"

if [[ ! -f "$SRC" ]]; then
  # curl|bash or tempfile: fetch enrich next to this script or into /tmp
  TMPDIR_ENRICH="$(mktemp -d)"
  SRC="$TMPDIR_ENRICH/enrich_websites.py"
  echo "fetching enrich_websites.py from $RAW_BASE"
  curl -fsSL "$RAW_BASE/enrich_websites.py" -o "$SRC"
fi

fix_batch() {
  local batch="$1"
  local skill="$HOME_DIR/.cursor/skills/$batch"
  local csv="$HOME_DIR/HelloAgents/$batch/$batch.csv"
  local db="$skill/data/$batch.db"
  local env_prefix
  env_prefix="$(echo "$batch" | tr '[:lower:]' '[:upper:]')"

  if [[ ! -d "$skill/scripts" ]]; then
    echo "SKIP $batch — no skill at $skill"
    return 0
  fi

  mkdir -p "$skill/data" "$HOME_DIR/HelloAgents/$batch"
  cp "$skill/scripts/enrich_websites.py" "$skill/scripts/enrich_websites.py.bak.$(date +%s)" 2>/dev/null || true
  cp "$SRC" "$skill/scripts/enrich_websites.py"
  chmod +x "$skill/scripts/enrich_websites.py"

  # Patch cadence: enrich every 5 places (was 25 → never fired)
  for f in "$skill/scripts/run_statewide.py" "$skill/scripts/watchdog.sh" "$skill/scripts/keeper.sh"; do
    [[ -f "$f" ]] || continue
    perl -i -pe 's/EMAIL_ENRICH_EVERY", "25"/EMAIL_ENRICH_EVERY", "5"/g; s/EMAIL_ENRICH_EVERY:-25/EMAIL_ENRICH_EVERY:-5/g; s/EMAIL_ENRICH_EVERY=25/EMAIL_ENRICH_EVERY=5/g' "$f" || true
  done

  # LaunchAgent plists
  for pl in \
    "$HOME_DIR/Library/LaunchAgents/com.helloagents.${batch}.watchdog.plist" \
    "$HOME_DIR/Library/LaunchAgents/com.helloagents.${batch}.keeper.plist"; do
    [[ -f "$pl" ]] || continue
    perl -i -pe 's#<string>25</string>#<string>5</string># if $. && $prev_enrich; $prev_enrich = (/EMAIL_ENRICH_EVERY/ ? 1 : 0)' "$pl" 2>/dev/null || true
    # simpler replace of key block via python
    python3 - <<PY
from pathlib import Path
p = Path("$pl")
t = p.read_text()
import re
t2 = re.sub(
    r'(<key>EMAIL_ENRICH_EVERY</key>\s*<string>)\d+(</string>)',
    r'\g<1>5\g<2>',
    t,
)
if t2 != t:
    p.write_text(t2)
    print("patched plist", p)
else:
    # insert env if missing
    if "EMAIL_ENRICH_EVERY" not in t and "<key>EnvironmentVariables</key>" in t:
        t = t.replace(
            "<key>EnvironmentVariables</key>\n\t<dict>\n",
            "<key>EnvironmentVariables</key>\n\t<dict>\n\t\t<key>EMAIL_ENRICH_EVERY</key>\n\t\t<string>5</string>\n",
        )
        p.write_text(t)
        print("inserted EMAIL_ENRICH_EVERY in", p)
PY
  done

  # Verify no crm table leftovers in enrich
  if grep -E 'table_info\(crm\)|FROM crm|UPDATE crm|CREATE TABLE IF NOT EXISTS crm' "$skill/scripts/enrich_websites.py" >/dev/null 2>&1; then
    echo "WARN: enrich still mentions crm table — forcing batch=$batch rewrite" >&2
  fi

  if [[ ! -f "$csv" ]]; then
    echo "No CSV yet at $csv — enrich will run when data exists"
    return 0
  fi

  echo "=== enrich $batch NOW (websites→emails) ==="
  export LEAD_BATCH="$batch"
  export "${env_prefix}_DB=$db"
  export "${env_prefix}_CSV=$csv"
  nohup python3 "$skill/scripts/enrich_websites.py" "$csv" "$csv" \
    --workers 12 --db "$db" --batch "$batch" \
    >>"$skill/data/enrich_console.log" 2>&1 &
  echo "spawned enrich pid=$! log=$skill/data/enrich_console.log"
}

fix_batch now
fix_batch vmp

echo
echo "Watch:"
echo "  tail -f ~/.cursor/skills/now/data/enrich_console.log"
echo "  python3 ~/.cursor/skills/now/scripts/status.py"
echo "  python3 ~/.cursor/skills/vmp/scripts/status.py"


# Hourly enrich keeper (fills emails while Maps scrapes places)
install_hourly() {
  local pl="$HOME_DIR/Library/LaunchAgents/com.helloagents.lead-enrich.plist"
  mkdir -p "$HOME_DIR/Library/LaunchAgents"
  cat >"$pl" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.helloagents.lead-enrich</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$HOME_DIR/.cursor/skills/now/scripts/hourly_enrich.sh</string>
  </array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME_DIR/.cursor/skills/now/data/hourly_enrich.out.log</string>
  <key>StandardErrorPath</key><string>$HOME_DIR/.cursor/skills/now/data/hourly_enrich.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key><string>$HOME_DIR</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
PLIST
  mkdir -p "$HOME_DIR/.cursor/skills/now/scripts" "$HOME_DIR/.cursor/skills/now/data"
  cat >"$HOME_DIR/.cursor/skills/now/scripts/hourly_enrich.sh" <<'H'
#!/usr/bin/env bash
set -u
for batch in now vmp; do
  skill="$HOME/.cursor/skills/$batch"
  csv="$HOME/HelloAgents/$batch/$batch.csv"
  db="$skill/data/$batch.db"
  [[ -f "$skill/scripts/enrich_websites.py" && -f "$csv" ]] || continue
  python3 "$skill/scripts/enrich_websites.py" "$csv" "$csv" --workers 12 --db "$db" --batch "$batch" \
    >>"$skill/data/enrich_console.log" 2>&1 || true
done
H
  chmod +x "$HOME_DIR/.cursor/skills/now/scripts/hourly_enrich.sh"
  launchctl bootout "gui/$(id -u)/com.helloagents.lead-enrich" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$pl" 2>/dev/null || launchctl load -w "$pl" 2>/dev/null || true
  echo "installed hourly enrich LaunchAgent"
}
install_hourly

