#!/usr/bin/env python3
"""Website email/contact enrich for developer-lead batches (NOW/VMP/CRM-style).

Hardened free crawl: mailto, regex, Cloudflare cfemail, JSON-LD, contact/about paths.
Does NOT freeze empty emails — rows with a website and no email are always eligible.

Usage:
  python3 enrich_websites.py IN.csv OUT.csv --workers 12 --db PATH.db
  BATCH=now|vmp|crm  (auto from --db path / env / cwd if omitted)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

FIELDS = [
    "company",
    "website",
    "email",
    "phone",
    "contact_person",
    "address",
    "county",
    "state",
    "category",
    "rating",
    "reviews",
    "source_query",
    "lat",
    "lon",
    "scraped_at",
    "notes",
]

STATE_CSV_BY_BATCH = {
    "crm": {"CT": "connecticut.csv", "RI": "rhode_island.csv", "MA": "massachusetts.csv"},
    "vmp": {"VA": "virginia.csv", "MD": "maryland.csv", "PA": "pennsylvania.csv"},
    "now": {"NJ": "new_jersey.csv", "OH": "ohio.csv", "WV": "west_virginia.csv"},
}

EMAIL_RE = re.compile(
    r"(?i)\b([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})\b"
)
MAILTO_RE = re.compile(r'(?i)mailto:([^"\'?\s>]+)')
CF_REEMAIL = re.compile(r'data-cfemail=["\']([0-9a-fA-F]+)["\']')
JSONLD_EMAIL_RE = re.compile(
    r'(?i)"email"\s*:\s*"([^"]+@[^"]+)"'
)
JSONLD_PERSON_RE = re.compile(
    r'(?i)"@type"\s*:\s*"Person"[^}]{0,400}?"name"\s*:\s*"([^"]{2,80})"',
    re.S,
)
CONTACT_NAME_RE = re.compile(
    r'(?i)(?:contact|owner|principal|founder|president|ceo)\s*[:\-–]\s*'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})'
)

BAD_EMAIL_FRAG = re.compile(
    r"(?i)(example\.com|sentry\.io|wixpress|schema\.org|godaddy|wordpress|jquery|"
    r"cloudflare|googleapis|gstatic|w3\.org|yourdomain|email\.com|domain\.com|"
    r"noreply@|no\-reply@|donotreply|mailer\-daemon|png|jpg|gif|webp|svg)"
)

CONTACT_PATHS = [
    "",
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/aboutus",
    "/team",
    "/our-team",
    "/company",
    "/connect",
    "/get-in-touch",
]

UA = (
    "Mozilla/5.0 (compatible; HelloAgentsLeadBot/1.0; +https://helloagents.dev; "
    "research; free-enrich)"
)


def detect_batch(db: Path | None, explicit: str) -> str:
    if explicit:
        return explicit.lower()
    env = (
        os.environ.get("LEAD_BATCH")
        or os.environ.get("BATCH")
        or ""
    ).strip().lower()
    if env in STATE_CSV_BY_BATCH:
        return env
    if db:
        s = str(db).lower()
        for b in ("now", "vmp", "crm"):
            if f"/{b}/" in s or s.endswith(f"/{b}.db") or f"{b}.db" in s:
                return b
    cwd = str(Path.cwd()).lower()
    for b in ("now", "vmp", "crm"):
        if f"/{b}" in cwd or f"skills/{b}" in cwd:
            return b
    return "now"


def decode_cfemail(hexstr: str) -> str:
    try:
        data = bytes.fromhex(hexstr)
    except ValueError:
        return ""
    if not data:
        return ""
    key = data[0]
    out = bytes(b ^ key for b in data[1:])
    try:
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def norm_email(e: str) -> str:
    e = unescape((e or "").strip().strip(".,;:<>()[]{}\"'"))
    e = e.split("?")[0].split("#")[0].strip()
    if e.startswith("mailto:"):
        e = e[7:]
    e = e.lower()
    if not EMAIL_RE.fullmatch(e):
        return ""
    if BAD_EMAIL_FRAG.search(e):
        return ""
    return e


def pick_best_email(emails: list[str]) -> str:
    scored: list[tuple[int, str]] = []
    for e in emails:
        n = norm_email(e)
        if not n:
            continue
        score = 0
        local = n.split("@", 1)[0]
        if any(x in local for x in ("info", "contact", "hello", "office", "sales", "admin")):
            score += 2
        if any(x in local for x in ("build", "develop", "homes", "realty")):
            score += 1
        scored.append((score, n))
    if not scored:
        return ""
    scored.sort(key=lambda t: (-t[0], len(t[1])))
    return scored[0][1]


def pick_contact(names: list[str], company: str) -> str:
    comp = re.sub(r"[^a-z0-9]+", " ", (company or "").lower()).strip()
    for n in names:
        n = re.sub(r"\s+", " ", (n or "").strip())
        if len(n.split()) < 2:
            continue
        if re.search(r"\b(llc|inc|ltd|corp|homes|builders?|developers?|construction)\b", n, re.I):
            continue
        if re.sub(r"[^a-z0-9]+", " ", n.lower()).strip() == comp:
            continue
        return n
    return ""


def fetch(url: str, timeout: float = 12.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(900_000)
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and "text" not in ctype and "xml" not in ctype:
                # still try decode
                pass
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    return raw.decode(enc, errors="ignore")
                except Exception:
                    continue
            return ""
    except Exception:
        return ""


def extract_from_html(html: str) -> tuple[list[str], list[str]]:
    emails: list[str] = []
    names: list[str] = []
    if not html:
        return emails, names

    for m in MAILTO_RE.finditer(html):
        emails.append(m.group(1))
    for m in CF_REEMAIL.finditer(html):
        emails.append(decode_cfemail(m.group(1)))
    for m in JSONLD_EMAIL_RE.finditer(html):
        emails.append(m.group(1))
    for m in EMAIL_RE.finditer(html):
        emails.append(m.group(1))

    for m in JSONLD_PERSON_RE.finditer(html):
        names.append(m.group(1))
    for m in CONTACT_NAME_RE.finditer(html):
        names.append(m.group(1))

    # JSON-LD blocks
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        blob = m.group(1).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                em = node.get("email")
                if isinstance(em, str):
                    emails.append(em)
                elif isinstance(em, list):
                    emails.extend(str(x) for x in em)
                nm = node.get("name")
                if node.get("@type") in ("Person", ["Person"]) or (
                    isinstance(node.get("@type"), list) and "Person" in node.get("@type")
                ):
                    if isinstance(nm, str):
                        names.append(nm)
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)

    return emails, names


def absolute_website(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not re.match(r"(?i)^https?://", u):
        u = "https://" + u
    try:
        p = urlparse(u)
        if not p.netloc:
            return ""
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return ""


def enrich_one(website: str, company: str) -> tuple[str, str]:
    base = absolute_website(website)
    if not base:
        return "", ""
    all_emails: list[str] = []
    all_names: list[str] = []
    for path in CONTACT_PATHS:
        html = fetch(urljoin(base + "/", path.lstrip("/")) if path else base)
        if not html:
            # try http fallback once on home
            if not path and base.startswith("https://"):
                html = fetch("http://" + base[len("https://") :])
        ems, nms = extract_from_html(html)
        all_emails.extend(ems)
        all_names.extend(nms)
        if pick_best_email(all_emails) and pick_contact(all_names, company):
            break
        time.sleep(0.05 + random.random() * 0.05)
    return pick_best_email(all_emails), pick_contact(all_names, company)


def load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") or "" for k in FIELDS})


def ensure_table(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY,
            company TEXT NOT NULL,
            website TEXT,
            email TEXT,
            phone TEXT,
            contact_person TEXT,
            address TEXT,
            county TEXT,
            state TEXT,
            category TEXT,
            rating TEXT,
            reviews TEXT,
            source_query TEXT,
            lat TEXT,
            lon TEXT,
            scraped_at TEXT,
            notes TEXT,
            name_key TEXT,
            domain_key TEXT,
            phone_key TEXT,
            UNIQUE(name_key, phone_key, domain_key, state)
        )
        """
    )


def update_db(
    conn: sqlite3.Connection,
    table: str,
    company: str,
    website: str,
    state: str,
    email: str,
    contact: str,
) -> int:
    if not email and not contact:
        return 0
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if "email" not in cols:
        return 0
    # Prefer matching website; never freeze blanks — fill empty emails only / upgrade contact
    cur = conn.execute(
        f"""
        UPDATE {table}
        SET email = CASE
              WHEN IFNULL(email,'') = '' AND ? != '' THEN ?
              WHEN IFNULL(email,'') != '' THEN email
              ELSE email
            END,
            contact_person = COALESCE(NULLIF(contact_person,''), NULLIF(?, ''))
        WHERE IFNULL(website,'') != ''
          AND (
            lower(replace(replace(website,'https://',''),'http://',''))
              LIKE '%' || lower(?) || '%'
            OR lower(company) = lower(?)
          )
          AND (IFNULL(state,'') = ? OR ? = '')
        """,
        (
            email,
            email,
            contact,
            re.sub(r"(?i)^https?://(www\.)?", "", website or "")[:80],
            company,
            state,
            state,
        ),
    )
    return cur.rowcount


def export_from_db(conn: sqlite3.Connection, table: str, out_csv: Path, state_csv: dict[str, str]) -> None:
    rows = conn.execute(
        f"SELECT {', '.join(FIELDS)} FROM {table} ORDER BY state, county, company"
    ).fetchall()
    dicts = [dict(zip(FIELDS, r)) for r in rows]
    write_csv(out_csv, dicts)
    out_dir = out_csv.parent
    by_state: dict[str, list[dict]] = {}
    for d in dicts:
        st = (d.get("state") or "").upper()
        by_state.setdefault(st, []).append(d)
    for st, name in state_csv.items():
        write_csv(out_dir / name, by_state.get(st, []))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("infile", type=Path)
    ap.add_argument("outfile", type=Path)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--batch", default="", help="now|vmp|crm")
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max rows to attempt (0=all missing-email with website)",
    )
    ap.add_argument(
        "--lock",
        type=Path,
        default=None,
        help="mkdir lock path (default: <db-dir>/enrich.lock or /tmp/…)",
    )
    args = ap.parse_args()

    batch = detect_batch(args.db, args.batch)
    table = batch  # crm|vmp|now
    state_csv = STATE_CSV_BY_BATCH[batch]

    db = args.db
    if db is None:
        db = Path(
            os.environ.get(f"{batch.upper()}_DB")
            or Path.home() / f".cursor/skills/{batch}/data/{batch}.db"
        )

    lock = args.lock or (db.parent / "enrich.lock")
    lock_dir = Path(str(lock) + ".d") if not str(lock).endswith(".d") else lock
    # mkdir lock (macOS-friendly; no flock)
    try:
        lock_dir.mkdir(parents=True, exist_ok=False)
        (lock_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")
    except FileExistsError:
        old = ""
        try:
            old = (lock_dir / "pid").read_text(encoding="utf-8").strip()
        except Exception:
            old = ""
        alive = False
        if old.isdigit():
            try:
                os.kill(int(old), 0)
                alive = True
            except OSError:
                alive = False
        if alive:
            print(f"enrich already running pid={old}", flush=True)
            return 0
        # stale
        import shutil

        shutil.rmtree(lock_dir, ignore_errors=True)
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "pid").write_text(str(os.getpid()), encoding="utf-8")

    try:
        if not args.infile.exists():
            print(f"missing csv {args.infile}", flush=True)
            return 1
        rows = load_rows(args.infile)
        # NEVER freeze: any row with website and empty email is fair game
        todo_idx = [
            i
            for i, r in enumerate(rows)
            if (r.get("website") or "").strip() and not (r.get("email") or "").strip()
        ]
        if args.limit:
            todo_idx = todo_idx[: args.limit]
        print(
            f"enrich batch={batch} table={table} rows={len(rows)} "
            f"need_email={len(todo_idx)} workers={args.workers} db={db}",
            flush=True,
        )
        if not todo_idx:
            print("nothing to enrich", flush=True)
            return 0

        got = 0
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            futs = {
                ex.submit(
                    enrich_one,
                    rows[i].get("website") or "",
                    rows[i].get("company") or "",
                ): i
                for i in todo_idx
            }
            done_n = 0
            for fut in as_completed(futs):
                i = futs[fut]
                done_n += 1
                try:
                    email, contact = fut.result()
                except Exception as e:
                    print(f"row {i} fail: {e}", flush=True)
                    continue
                if email:
                    rows[i]["email"] = email
                    got += 1
                if contact and not (rows[i].get("contact_person") or "").strip():
                    rows[i]["contact_person"] = contact
                note = set(filter(None, (rows[i].get("notes") or "").split(";")))
                note.add("web_enrich")
                # do NOT add notes that block future re-enrich
                rows[i]["notes"] = ";".join(sorted(note))
                if done_n % 25 == 0 or done_n == len(futs):
                    print(
                        f"progress {done_n}/{len(futs)} emails_found={got}",
                        flush=True,
                    )

        write_csv(args.outfile, rows)

        db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db))
        ensure_table(conn, table)
        updated = 0
        for r in rows:
            if not (r.get("email") or "").strip() and not (r.get("contact_person") or "").strip():
                continue
            updated += update_db(
                conn,
                table,
                r.get("company") or "",
                r.get("website") or "",
                (r.get("state") or "").upper(),
                r.get("email") or "",
                r.get("contact_person") or "",
            )
        conn.commit()
        export_from_db(conn, table, args.outfile, state_csv)
        conn.close()
        print(
            f"done emails_new≈{got} db_updates≈{updated} csv={args.outfile}",
            flush=True,
        )
        return 0
    finally:
        import shutil

        try:
            holder = (lock_dir / "pid").read_text(encoding="utf-8").strip()
        except Exception:
            holder = ""
        if holder == str(os.getpid()) or not holder:
            shutil.rmtree(lock_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
