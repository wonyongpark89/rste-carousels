"""RSTE new-article watcher, DOI register and approval workflow.

    python pipeline/rste_pipeline.py check [--scheduled] [--dry-run]
    python pipeline/rste_pipeline.py review
    python pipeline/rste_pipeline.py status [DOI]
    python pipeline/rste_pipeline.py record-draft DOI FOLDER
    python pipeline/rste_pipeline.py flag DOI "reason"
    python pipeline/rste_pipeline.py enqueue DOI            (queue a baseline/skipped article by hand)
    python pipeline/rste_pipeline.py prepare-draft DOI       (scheduled or interactive; hosts files, prints the Buffer DRAFT payload)
    python pipeline/rste_pipeline.py record-buffer-draft DOI POST_ID STATUS   (STATUS must be draft)
    python pipeline/rste_pipeline.py approve DOI
    python pipeline/rste_pipeline.py revise DOI "what to change"
    python pipeline/rste_pipeline.py reject DOI "reason"
    python pipeline/rste_pipeline.py prepare-publish DOI     (interactive only; prints the Buffer payload)
    python pipeline/rste_pipeline.py record-hosted DOI PDF_URL COVER_URL
    python pipeline/rste_pipeline.py record-buffer DOI POST_ID STATUS [POST_URL]
    python pipeline/rste_pipeline.py report
    python pipeline/rste_pipeline.py finish-run

Discovery sources (no scraping of the Cloudflare-protected HTML):
  1. Taylor & Francis RSS feed for crst20 - the same list as the "Latest articles" page
     (toc/crst20/0/0) plus the current issue. dc:date is first online publication;
     prism:volume/number appear only once the article is assigned to an issue.
  2. Crossref (ISSN 0263-5143 / 1470-1138), cursor-paginated - secondary source and the
     authority for authors and the published-online date.

Statuses in register.json:
  baseline, pre_existing, skipped_pre_baseline, skipped_non_article   (no post planned)
  new                  detected; draft not yet generated
  needs_manual_review  metadata/abstract/affiliation missing, or generation failed
  pending_approval     PDF + caption built; waiting for the Editor
  revision_requested   Editor asked for changes
  approved             Editor approved this DOI explicitly in an interactive session
  rejected             Editor rejected; files kept
  hosted               PDF and cover pushed to the public host
  queued / published   confirmed by Buffer (post id recorded)

Standard library only. Nothing in this script contacts LinkedIn or Buffer; Claude does that with the Buffer MCP.
A pending_approval article may carry buffer_draft_id: a Buffer DRAFT (never queued) the Editor approves in Buffer.
"""
import datetime as dt, hashlib, json, os, pathlib, re, shutil, sys, time
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent
CAROUSELS = PROJECT / "article-carousels"
REGISTER = HERE / "register.json"
REPORTS = HERE / "reports"
RUNS = HERE / "runs"
LOCK = HERE / ".run.lock"
SCHEDULED_MARKER = HERE / ".scheduled-run"
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))

UA = "RSTE-new-article-watcher/1.0 (editorial use; Research in Science & Technological Education)"
NS = {"rss": "http://purl.org/rss/1.0/", "dc": "http://purl.org/dc/elements/1.1/",
      "prism": "http://prismstandard.org/namespaces/basic/2.0/",
      "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
NON_ARTICLE = re.compile(r"^\s*(correction|corrigendum|erratum|retraction|retracted|expression of concern|"
                         r"editorial|publisher'?s note|acknowledg|reviewers?\b|thanks to reviewers|book review|"
                         r"call for papers|obituary|in memoriam)", re.I)
NO_POST = {"baseline", "pre_existing", "skipped_pre_baseline", "skipped_non_article"}
LOCKED = {"approved", "hosted", "queued", "published"}   # outputs the scheduled run must not touch


# ---------- small helpers ----------

def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t=None):
    return (t or now()).isoformat().replace("+00:00", "Z")


def norm_doi(doi):
    doi = doi.strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:|https?://www\.tandfonline\.com/doi/(full|abs|pdf)/)", "", doi, flags=re.I)
    return doi.split("?")[0].strip().lower()


def fetch(url, accept="application/json", tries=4):
    """GET with retries for timeouts, 429 and 5xx. Returns bytes or raises the last error."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (408, 425, 429, 500, 502, 503, 504):
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 3 * 2 ** attempt
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last, wait = e, 3 * 2 ** attempt
        if attempt < tries - 1:
            time.sleep(min(wait, 60))
    raise last


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_register():
    if not REGISTER.exists():
        return None
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def save_register(reg):
    if REGISTER.exists():
        shutil.copy2(REGISTER, HERE / "register.bak.json")
    tmp = REGISTER.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, REGISTER)


def event(rec, what, **extra):
    rec.setdefault("events", []).append({"at": iso(), "event": what, **extra})


def rel(p):
    try:
        return pathlib.Path(p).resolve().relative_to(PROJECT).as_posix()
    except ValueError:
        return str(p)


def get_rec(reg, doi):
    doi = norm_doi(doi)
    rec = reg["articles"].get(doi)
    if not rec:
        sys.exit(f"{doi} is not in the register. Check the DOI (run `review` to list them).")
    return doi, rec


# ---------- sources ----------

def from_rss():
    raw = fetch(CONFIG["rss_url"], accept="application/rss+xml, application/xml")
    root = ET.fromstring(raw)
    out = {}
    for it in root.findall("rss:item", NS):
        doi = (it.findtext("prism:doi", namespaces=NS) or "").strip()
        if not doi:
            continue
        vol = it.findtext("prism:volume", namespaces=NS)
        out[norm_doi(doi)] = {
            "doi": norm_doi(doi),
            "title": (it.findtext("dc:title", namespaces=NS) or it.findtext("rss:title", namespaces=NS) or "").strip(),
            "online_date": (it.findtext("dc:date", namespaces=NS) or "")[:10] or None,
            "volume": vol, "issue": it.findtext("prism:number", namespaces=NS),
            "creator_raw": (it.findtext("dc:creator", namespaces=NS) or "").strip(),
            "url": f"https://www.tandfonline.com/doi/full/{doi}",
        }
    return out


def cr_date(item, key):
    parts = (item.get(key) or {}).get("date-parts", [[None]])[0]
    if not parts or parts[0] is None:
        return None
    return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts))


def cr_record(item):
    authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() or a.get("name", "")
               for a in item.get("author", [])]
    return {
        "doi": norm_doi(item["DOI"]),
        "title": re.sub(r"<[^>]+>", "", (item.get("title") or [""])[0]).strip(),
        "authors": authors,
        "online_date": cr_date(item, "published-online"),
        "print_date": cr_date(item, "published-print"),
        "volume": item.get("volume"), "issue": item.get("issue"),
        "type": item.get("type"),
        "has_abstract": bool(item.get("abstract")),
        "crossref_created": (item.get("created") or {}).get("date-time"),
    }


def from_crossref(since):
    """All RSTE works created in Crossref since `since` (YYYY-MM-DD), following cursors."""
    out, cursor, pages = {}, "*", 0
    sel = "DOI,title,author,created,published-online,published-print,issue,volume,type,abstract"
    while True:
        q = urllib.parse.urlencode({"filter": f"from-created-date:{since}", "rows": 200,
                                    "cursor": cursor, "select": sel, "mailto": CONFIG.get("crossref_mailto", "")})
        msg = json.loads(fetch(f"https://api.crossref.org/journals/{CONFIG['issn_print']}/works?{q}"))["message"]
        items = msg.get("items", [])
        for it in items:
            r = cr_record(it)
            out[r["doi"]] = r
        pages += 1
        cursor = msg.get("next-cursor")
        if not items or not cursor or pages > 50:
            break
    return out


def crossref_one(doi):
    try:
        return cr_record(json.loads(fetch("https://api.crossref.org/works/" + urllib.parse.quote(doi)))["message"])
    except Exception:
        return None


def existing_folders():
    found = {}
    for m in CAROUSELS.glob("*/*-metadata.json"):
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
            if d.get("doi"):
                found[norm_doi(d["doi"])] = m.parent
        except (ValueError, OSError):
            pass
    return found


def buffer_csv():
    p = PROJECT / "buffer-drafts.csv"
    rows = {}
    if p.exists():
        import csv
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows[norm_doi(r["doi"])] = r
    return rows


# ---------- check ----------

def merge(rss, cr):
    """One record per DOI. Crossref wins for authors/dates; RSS fills gaps and supplies issue info."""
    merged = {}
    for doi in set(rss) | set(cr):
        a, b = rss.get(doi, {}), cr.get(doi, {})
        merged[doi] = {
            "doi": doi,
            "title": b.get("title") or a.get("title"),
            "authors": b.get("authors") or [],
            "online_date": b.get("online_date") or a.get("online_date"),
            "volume": b.get("volume") or a.get("volume"),
            "issue": b.get("issue") or a.get("issue"),
            "type": b.get("type") or ("journal-article" if a else None),
            "url": f"https://www.tandfonline.com/doi/full/{doi}",
            "seen_in": [s for s, d in (("tandf_rss", a), ("crossref", b)) if d],
        }
    return merged


def metadata_flags(r):
    flags = []
    if not r.get("title"):
        flags.append("title missing")
    if not r.get("authors"):
        flags.append("authors missing from Crossref")
    if not r.get("online_date"):
        flags.append("online publication date missing")
    return flags


def cmd_check(args):
    scheduled, dry = "--scheduled" in args, "--dry-run" in args
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3 * 3600:
        sys.exit("Another check appears to be running (pipeline/.run.lock). Remove it if stale.")
    if not dry:
        LOCK.write_text(iso(), encoding="utf-8")
    try:
        return _check(scheduled, dry)
    finally:
        LOCK.unlink(missing_ok=True)


def _check(scheduled, dry):
    reg = load_register()
    first_run = reg is None
    t = now()
    run = {"started": iso(t), "scheduled": scheduled, "dry_run": dry, "first_run": first_run,
           "sources": {}, "new": [], "manual": [], "issue_assigned": [], "skipped": []}
    if scheduled and not dry:
        SCHEDULED_MARKER.write_text(iso(t), encoding="utf-8")

    since = (t - dt.timedelta(days=CONFIG["baseline_lookback_days"] if first_run else CONFIG["lookback_days"])).date()
    if not first_run and reg["meta"].get("last_success"):
        last = dt.datetime.fromisoformat(reg["meta"]["last_success"].replace("Z", "+00:00"))
        since = min(since, (last - dt.timedelta(days=CONFIG["lookback_days"])).date())

    rss, cr = {}, {}
    try:
        rss = from_rss()
        run["sources"]["tandf_rss"] = f"ok ({len(rss)} items)"
    except Exception as e:
        run["sources"]["tandf_rss"] = f"unavailable: {e}"
    try:
        cr = from_crossref(since.isoformat())
        run["sources"]["crossref"] = f"ok ({len(cr)} works created since {since})"
    except Exception as e:
        run["sources"]["crossref"] = f"unavailable: {e}"
    if not rss and not cr:
        run["outcome"] = "both sources unavailable; register unchanged. The next run will catch up."
        return finish(reg, run, dry, ok=False)

    # RSS-only items: fill authors/dates from Crossref one by one.
    for doi in set(rss) - set(cr):
        one = crossref_one(doi)
        if one:
            cr[doi] = one
    found = merge(rss, cr)

    if first_run:
        reg = {"meta": {"created": iso(t), "baseline_date": t.date().isoformat(),
                        "journal": "Research in Science & Technological Education",
                        "note": "First run recorded every article then visible as baseline; no posts generated for them."},
               "articles": {}}
        folders, buf = existing_folders(), buffer_csv()
        for doi, r in found.items():
            status = "pre_existing" if doi in folders else "baseline"
            rec = {**r, "status": status, "first_detected": iso(t)}
            if doi in folders:
                rec["folder"] = rel(folders[doi])
            if doi in buf:
                rec["buffer_draft_id"] = buf[doi].get("buffer_draft_id")
                rec["notes"] = f"Buffer {buf[doi].get('status')} {buf[doi].get('buffer_draft_id')} created before this pipeline existed."
            event(rec, "baseline", status=status)
            reg["articles"][doi] = rec
        for doi, folder in folders.items():   # carousels made by hand for DOIs not in the window
            if doi not in reg["articles"]:
                rec = {"doi": doi, "status": "pre_existing", "folder": rel(folder), "first_detected": iso(t)}
                event(rec, "baseline", status="pre_existing")
                reg["articles"][doi] = rec
        run["outcome"] = f"baseline established with {len(reg['articles'])} articles; no drafts generated."
        return finish(reg, run, dry, ok=True)

    baseline_date = dt.date.fromisoformat(reg["meta"]["baseline_date"])
    grace = dt.timedelta(days=CONFIG["pre_baseline_grace_days"])
    for doi, r in sorted(found.items(), key=lambda kv: kv[1].get("online_date") or ""):
        rec = reg["articles"].get(doi)
        if rec:   # known DOI: only note issue assignment; never a second post
            if r.get("volume") and not rec.get("volume"):
                rec.update(volume=r["volume"], issue=r.get("issue"))
                event(rec, "issue_assigned", volume=r["volume"], issue=r.get("issue"))
                run["issue_assigned"].append(doi)
            rec["seen_in"] = sorted(set(rec.get("seen_in", [])) | set(r["seen_in"]))
            continue
        rec = {**r, "first_detected": iso(t)}
        online = dt.date.fromisoformat(r["online_date"][:10]) if r.get("online_date") else None
        if r.get("type") and r["type"] != "journal-article" or NON_ARTICLE.match(r.get("title") or ""):
            rec["status"], why = "skipped_non_article", f"not a research article ({r.get('type')}: {r.get('title')!r})"
            run["skipped"].append({"doi": doi, "why": why})
        elif online and online < baseline_date - grace:
            rec["status"], why = "skipped_pre_baseline", (f"first online {online}, before the baseline "
                                                          f"({baseline_date}); probably issue assignment of an older article")
            run["skipped"].append({"doi": doi, "why": why})
        elif metadata_flags(r):
            rec["status"], why = "needs_manual_review", "; ".join(metadata_flags(r))
            run["manual"].append({"doi": doi, "why": why})
        else:
            rec["status"], why = "new", "first online publication detected"
            run["new"].append(doi)
        event(rec, "detected", status=rec["status"], why=why)
        reg["articles"][doi] = rec
    run["outcome"] = f"{len(run['new'])} new, {len(run['manual'])} for manual review, {len(run['skipped'])} skipped."
    return finish(reg, run, dry, ok=True)


def finish(reg, run, dry, ok):
    run["finished"] = iso()
    if reg is not None and ok:
        reg["meta"]["last_success"] = run["finished"]
    if reg is not None:
        reg["meta"]["last_run"] = run["finished"]
        reg["meta"]["last_sources"] = run["sources"]
    if not dry:
        RUNS.mkdir(exist_ok=True)
        (RUNS / f"{run['finished'][:19].replace(':', '')}-check.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        if reg is not None:
            save_register(reg)
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if ok else 2


# ---------- generation bookkeeping ----------

def draft_files(folder):
    folder = pathlib.Path(folder)
    if not folder.is_absolute():
        folder = PROJECT / folder
    pdf = next(iter(folder.glob("*-carousel.pdf")), None)
    cap = next(iter(folder.glob("*-caption.txt")), None)
    cover = next(iter(folder.glob("*-slide-1.png")), None)
    meta = next(iter(folder.glob("*-metadata.json")), None)
    return folder, pdf, cap, cover, meta


def cmd_record_draft(doi, folder):
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] in LOCKED | {"rejected"}:
        sys.exit(f"{doi} is {rec['status']}; its outputs are not replaced automatically. "
                 "Ask the Editor to say 'Revise <DOI>' first.")
    folder, pdf, cap, cover, meta = draft_files(folder)
    problems = [n for n, p in (("carousel PDF", pdf), ("caption TXT", cap), ("slide-1 PNG", cover), ("metadata.json", meta)) if not p]
    if meta:
        m = json.loads(meta.read_text(encoding="utf-8"))
        if norm_doi(m.get("doi", "")) != doi:
            problems.append(f"metadata.json DOI is {m.get('doi')}")
        if m.get("missing"):
            problems.append("metadata.json still lists missing items")
    if problems:
        sys.exit("Not recorded: " + "; ".join(problems))
    rec.update(status="pending_approval", folder=rel(folder),
               files={"pdf": rel(pdf), "caption": rel(cap), "cover": rel(cover)},
               hashes={"pdf": sha256(pdf), "caption": sha256(cap), "cover": sha256(cover)})
    rec.pop("approval", None)
    prov = m.get("provisional") if meta else None
    if prov:
        rec["provisional"] = prov
    else:
        rec.pop("provisional", None)
    event(rec, "draft_recorded", folder=rel(folder), provisional=bool(prov))
    save_register(reg)
    print(f"{doi}: pending approval\n  {rel(pdf)}\n  {rel(cap)}")
    if prov:
        print(f"  PROVISIONAL: {'; '.join(prov['unverified'])}. {prov['action']}")


def cmd_flag(doi, reason):
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] in LOCKED:
        sys.exit(f"{doi} is {rec['status']}; not changed.")
    rec["status"], rec["manual_reason"] = "needs_manual_review", reason
    event(rec, "flagged", reason=reason)
    save_register(reg)
    print(f"{doi}: needs manual review - {reason}")


def cmd_retry(doi):
    """Put a needs_manual_review article back to `new` so the next run (or this session) builds it again."""
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] != "needs_manual_review":
        sys.exit(f"{doi} is {rec['status']}; only needs_manual_review articles can be retried.")
    rec["status"] = "new"
    rec.pop("manual_reason", None)
    event(rec, "retry", status="new")
    save_register(reg)
    print(f"{doi}: back to new")


def cmd_enqueue(doi):
    reg = load_register()
    doi = norm_doi(doi)
    rec = reg["articles"].get(doi)
    if rec is None:
        one = crossref_one(doi)
        if not one:
            sys.exit(f"{doi}: not found in Crossref.")
        rec = reg["articles"][doi] = {**one, "first_detected": iso(), "seen_in": ["manual"],
                                      "url": f"https://www.tandfonline.com/doi/full/{doi}"}
    elif rec["status"] not in NO_POST | {"needs_manual_review"}:
        sys.exit(f"{doi} is already {rec['status']}.")
    rec["status"] = "new"
    event(rec, "enqueued_by_editor")
    save_register(reg)
    print(f"{doi}: queued for draft generation")


# ---------- approval ----------

def interactive_guard(action):
    if SCHEDULED_MARKER.exists():
        sys.exit(f"Refused: a scheduled discovery run is in progress (pipeline/.scheduled-run). "
                 f"'{action}' is only allowed in an interactive session. If no scheduled run is active, "
                 "run `finish-run` and retry.")


def verify_hashes(rec):
    changed = [k for k, h in rec.get("hashes", {}).items() if sha256(PROJECT / rec["files"][k]) != h]
    return changed


def cmd_approve(doi):
    interactive_guard("approve")
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] != "pending_approval":
        sys.exit(f"{doi} is {rec['status']}; only a pending_approval draft can be approved.")
    changed = verify_hashes(rec)
    if changed:
        sys.exit(f"{doi}: {', '.join(changed)} changed since the draft was recorded. Re-run record-draft and review again.")
    rec["status"] = "approved"
    rec["approval"] = {"at": iso(), "by": "Editor, interactive Claude Code session", "doi": doi, "hashes": rec["hashes"]}
    event(rec, "approved")
    save_register(reg)
    if rec.get("provisional"):
        print("  Note: this draft was built from unverified sources (" + "; ".join(rec["provisional"]["unverified"]) + ").")
    print(f"{doi}: approved. Files are locked; publishing still needs a separate instruction (publish now or add to queue).")


def cmd_revise(doi, note):
    interactive_guard("revise")
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] in {"queued", "published"}:
        sys.exit(f"{doi} is already {rec['status']} in Buffer; edit or remove it there first.")
    rec["status"], rec["revision_note"] = "revision_requested", note
    rec.pop("approval", None)
    event(rec, "revision_requested", note=note)
    save_register(reg)
    print(f"{doi}: revision requested - {note}")


def cmd_reject(doi, reason):
    interactive_guard("reject")
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] in {"queued", "published"}:
        sys.exit(f"{doi} is already {rec['status']} in Buffer; remove it there first.")
    rec["status"], rec["reject_reason"] = "rejected", reason
    event(rec, "rejected", reason=reason)
    save_register(reg)
    print(f"{doi}: rejected (files kept in {rec.get('folder')})")


# ---------- hosting and Buffer ----------

def host_copy(doi, rec, copy=True):
    """Copy the PDF and cover (slide 1) into the public host repo. Returns (dest, git command, payload).
    With copy=False only the URLs and payload are worked out."""
    host = (PROJECT / CONFIG["host_repo"]).resolve()   # "." = this repo is the host repo
    suffix = doi.split("/", 1)[1]
    dest = host / "carousels" / suffix
    pdf, cover = PROJECT / rec["files"]["pdf"], PROJECT / rec["files"]["cover"]
    prefix = pdf.name.replace("-carousel.pdf", "")
    if copy:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, dest / pdf.name)
        shutil.copy2(cover, dest / f"{prefix}-cover.png")
    base = f"{CONFIG['host_base_url']}/carousels/{suffix}"
    caption = (PROJECT / rec["files"]["caption"]).read_text(encoding="utf-8").strip()
    payload = {
        "channelId": CONFIG["buffer_channel_id"],
        "schedulingType": "automatic",
        "text": caption,
        "assets": [{"document": {"url": f"{base}/{pdf.name}", "title": rec.get("title") or prefix,
                                 "thumbnailUrl": f"{base}/{prefix}-cover.png"}}],
    }
    git = (f'git -C "{host}" add carousels/{suffix} && git -C "{host}" commit -m "Add {prefix} carousel ({doi})" '
           f'&& git -C "{host}" push')
    return dest, git, payload


def cmd_prepare_draft(doi):
    """Host a pending_approval draft and print the Buffer DRAFT payload. Allowed in scheduled runs.
    Does not push and does not contact Buffer."""
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] != "pending_approval":
        sys.exit(f"{doi} is {rec['status']}; only a pending_approval draft gets a Buffer draft.")
    if rec.get("buffer_draft_id"):
        sys.exit(f"{doi} already has Buffer draft {rec['buffer_draft_id']}; not creating another.")
    changed = verify_hashes(rec)
    if changed:
        sys.exit(f"{doi}: {', '.join(changed)} changed since record-draft. Re-run record-draft first.")
    dest, git, payload = host_copy(doi, rec)
    payload["saveToDraft"] = True
    print(f"Copied to {dest}\nNext:\n  {git}")
    print("  wait until both asset URLs return HTTP 200, then Buffer create_post with exactly this "
          "(saveToDraft true, no mode, no dueAt):")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  then: record-buffer-draft {doi} <post id> <Buffer status>")


def cmd_record_buffer_draft(doi, post_id, status):
    """Record a Buffer DRAFT. Refuses (and says so loudly) unless Buffer's status is 'draft'."""
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if status.lower() != "draft":
        sys.exit(f"ALERT: Buffer post {post_id} for {doi} has status '{status}', not 'draft'. Nothing recorded. "
                 "Delete that post in Buffer now (delete_post) unless it has already been sent, and tell the Editor.")
    if rec["status"] != "pending_approval":
        sys.exit(f"{doi} is {rec['status']}; not recording a Buffer draft.")
    _, _, payload = host_copy(doi, rec, copy=False)
    doc = payload["assets"][0]["document"]
    for u in (doc["url"], doc["thumbnailUrl"]):
        try:
            fetch(u, accept="*/*", tries=2)
        except Exception as e:
            sys.exit(f"{u} is not reachable ({e}); the draft's PDF would not load. Nothing recorded.")
    rec.update(buffer_draft_id=post_id, buffer_draft_status=status, pdf_url=doc["url"], cover_url=doc["thumbnailUrl"])
    event(rec, "buffer_draft_created", buffer_post_id=post_id, buffer_status=status)
    save_register(reg)
    print(f"{doi}: Buffer draft {post_id} recorded (still pending_approval; the Editor approves in Buffer).")


def cmd_prepare_publish(doi):
    """Copy the approved PDF and cover into the public host repo and print the Buffer payload.
    Does not push and does not contact Buffer."""
    interactive_guard("prepare-publish")
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] not in {"approved", "hosted"}:
        sys.exit(f"{doi} is {rec['status']}; it must be approved first (say 'Approve {doi}').")
    changed = verify_hashes(rec)
    if changed:
        sys.exit(f"{doi}: {', '.join(changed)} changed after approval. Approval is void; re-review.")
    dest, git, payload = host_copy(doi, rec)
    payload["mode"] = "shareNow | addToQueue (Editor chooses)"
    print(f"Copied to {dest}\nNext (interactive, after the Editor's go-ahead):")
    print(f"  {git}")
    if rec.get("buffer_draft_id"):
        print(f"  NOTE: Buffer draft {rec['buffer_draft_id']} already exists. Prefer the Editor's 'Add to Queue' "
              "on that draft in Buffer over creating a second post.")
    print(f"  wait until both URLs return HTTP 200, then record-hosted, then Buffer create_post with:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_record_hosted(doi, pdf_url, cover_url):
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] not in {"approved", "hosted"}:
        sys.exit(f"{doi} is {rec['status']}; not approved.")
    for u in (pdf_url, cover_url):
        try:
            fetch(u, accept="*/*", tries=2)
        except Exception as e:
            sys.exit(f"{u} is not reachable yet ({e}). Wait for GitHub Pages to deploy.")
    rec.update(status="hosted", pdf_url=pdf_url, cover_url=cover_url)
    event(rec, "hosted", pdf_url=pdf_url, cover_url=cover_url)
    save_register(reg)
    print(f"{doi}: hosted")


def cmd_record_buffer(doi, post_id, status, post_url=None):
    """Record what Buffer returned. STATUS is Buffer's own post status (e.g. sent, scheduled, buffer, draft)."""
    reg = load_register()
    doi, rec = get_rec(reg, doi)
    if rec["status"] not in {"approved", "hosted", "queued"}:
        sys.exit(f"{doi} is {rec['status']}; refusing to record a Buffer post for an unapproved article.")
    rec["buffer_post_id"], rec["buffer_status"] = post_id, status
    if post_url:
        rec["post_url"] = post_url
    rec["status"] = "published" if status.lower() in {"sent", "published"} else "queued"
    event(rec, rec["status"], buffer_post_id=post_id, buffer_status=status, post_url=post_url)
    save_register(reg)
    print(f"{doi}: {rec['status']} (Buffer post {post_id})")


# ---------- review and report ----------

def line(rec):
    who = (rec.get("authors") or ["?"])[0].split()[-1] if rec.get("authors") else "?"
    return f"{rec['doi']}  [{rec['status']}]  {who} - {rec.get('title') or '(no title)'}  (online {rec.get('online_date') or '?'})"


def cmd_review():
    reg = load_register()
    if not reg:
        sys.exit("No register yet. Run `check` first.")
    groups = {}
    for rec in reg["articles"].values():
        groups.setdefault(rec["status"], []).append(rec)
    for st in ("pending_approval", "revision_requested", "needs_manual_review", "new", "approved", "hosted", "queued"):
        for rec in groups.get(st, []):
            print(line(rec))
            for k, v in (rec.get("files") or {}).items():
                print(f"    {k}: {v}")
            for k in ("manual_reason", "revision_note"):
                if rec.get(k):
                    print(f"    {k}: {rec[k]}")
            if rec.get("provisional"):
                print(f"    PROVISIONAL (unverified): {'; '.join(rec['provisional']['unverified'])}. {rec['provisional']['action']}")
    print("\nCounts:", ", ".join(f"{k} {len(v)}" for k, v in sorted(groups.items())))


def cmd_status(doi=None):
    reg = load_register()
    if doi:
        print(json.dumps(get_rec(reg, doi)[1], ensure_ascii=False, indent=2))
    else:
        cmd_review()


def cmd_report():
    reg = load_register()
    runs = sorted(RUNS.glob("*-check.json"))
    run = json.loads(runs[-1].read_text(encoding="utf-8")) if runs else {}
    arts = reg["articles"] if reg else {}
    det = set(run.get("new", [])) | {m["doi"] for m in run.get("manual", [])}
    by = lambda *s: [r for r in arts.values() if r["status"] in s]
    L = [f"# RSTE new-article check - {run.get('finished', iso())[:16].replace('T', ' ')} UTC", ""]
    L += [f"- Run type: {'scheduled' if run.get('scheduled') else 'manual'}{' (dry run)' if run.get('dry_run') else ''}"
          f"{' - FIRST RUN, baseline only' if run.get('first_run') else ''}",
          f"- Outcome: {run.get('outcome', 'n/a')}"]
    for s, v in run.get("sources", {}).items():
        L.append(f"- Source {s}: {v}")
    L += ["- Nothing was published or queued. Buffer drafts, if any, are listed below.", "", "## Newly detected articles", ""]
    L += [f"- {line(arts[d])}" for d in sorted(det) if d in arts] or ["- None."]
    L += ["", "## Drafts awaiting approval", ""]
    for r in by("pending_approval"):
        L.append(f"- {line(r)}")
        L.append(f"    - Buffer draft: {r['buffer_draft_id']}" if r.get("buffer_draft_id") else "    - Buffer draft: none yet")
        for k, v in r.get("files", {}).items():
            L.append(f"    - {k}: `{v}`")
        if r.get("provisional"):
            L.append(f"    - PROVISIONAL: built without the publisher page. {r['provisional']['action']} "
                     f"Unverified: {'; '.join(r['provisional']['unverified'])}.")
    if not by("pending_approval"):
        L.append("- None.")
    L += ["", "## Needs manual attention", ""]
    L += [f"- {line(r)} - {r.get('manual_reason') or r.get('revision_note') or ''}" for r in by("needs_manual_review", "revision_requested", "new")] or ["- None."]
    L += ["", "## Issue assignment noted (no new post)", ""]
    L += [f"- {line(arts[d])} -> vol {arts[d].get('volume')}, issue {arts[d].get('issue')}" for d in run.get("issue_assigned", [])] or ["- None."]
    L += ["", "## Skipped this run", ""]
    L += [f"- {s['doi']}: {s['why']}" for s in run.get("skipped", [])] or ["- None."]
    L += ["", "## Already processed", ""]
    L += [f"- {line(r)}" + (f" - folder `{r['folder']}`" if r.get("folder") else "") + (f" - {r['notes']}" if r.get("notes") else "")
          for r in by("pre_existing", "approved", "hosted", "queued", "published", "rejected")] or ["- None."]
    n_base = len(by("baseline", "skipped_pre_baseline", "skipped_non_article"))
    L += ["", f"Baseline/skipped articles in register (no post planned): {n_base}. "
          "To post one anyway: `python pipeline/rste_pipeline.py enqueue <DOI>`.", "",
          "## Commands for an interactive session", "",
          "- Review pending RSTE posts", "- Approve <DOI>", "- Revise <DOI>: <what to change>", "- Reject <DOI>: <reason>"]
    REPORTS.mkdir(exist_ok=True)
    text = "\n".join(L) + "\n"
    stamp = run.get("finished", iso())[:16].replace(":", "").replace("T", "-")
    (REPORTS / f"{stamp}-report.md").write_text(text, encoding="utf-8")
    (REPORTS / "latest-report.md").write_text(text, encoding="utf-8")
    print(text)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    c, a = argv[0], argv[1:]
    table = {
        "check": lambda: cmd_check(a),
        "review": cmd_review, "status": lambda: cmd_status(*a[:1]),
        "record-draft": lambda: cmd_record_draft(a[0], a[1]),
        "flag": lambda: cmd_flag(a[0], " ".join(a[1:]) or "unspecified"),
        "enqueue": lambda: cmd_enqueue(a[0]),
        "retry": lambda: cmd_retry(a[0]),
        "approve": lambda: cmd_approve(a[0]),
        "revise": lambda: cmd_revise(a[0], " ".join(a[1:]) or "unspecified"),
        "reject": lambda: cmd_reject(a[0], " ".join(a[1:]) or "unspecified"),
        "prepare-draft": lambda: cmd_prepare_draft(a[0]),
        "record-buffer-draft": lambda: cmd_record_buffer_draft(*a[:3]),
        "prepare-publish": lambda: cmd_prepare_publish(a[0]),
        "record-hosted": lambda: cmd_record_hosted(*a[:3]),
        "record-buffer": lambda: cmd_record_buffer(*a[:4]),
        "report": cmd_report,
        "finish-run": lambda: (SCHEDULED_MARKER.unlink(missing_ok=True), print("scheduled-run marker cleared")),
    }
    if c not in table:
        sys.exit(__doc__)
    try:
        r = table[c]()
    except IndexError:
        sys.exit(__doc__)
    sys.exit(r if isinstance(r, int) else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
