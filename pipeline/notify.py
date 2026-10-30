"""Review-notification emails for the RSTE LinkedIn workflow.

    python pipeline/notify.py prepare [--run-error "what failed"]
    python pipeline/notify.py sent GMAIL_MESSAGE_ID
    python pipeline/notify.py failed "reason"
    python pipeline/notify.py log

`prepare` reads register.json and the latest runs/*.json, works out what the Editor has not
yet been told about, and writes pipeline/outbox/notification.json (to, subject, body,
html_body, keys). Exit codes: 0 = an email should be sent, 3 = nothing new (send nothing),
4 = no notification address configured.

Claude sends that email with the Gmail connector, then runs `sent <message id>`. Only then
are the keys written to notifications.json, so a failed send is retried on the next run and
a successful one is never repeated. `failed` records the attempt and keeps the outbox.

What is notified (each once):
  draft:<DOI>:<buffer draft id>   pending_approval article with a Buffer draft
  nodraft:<DOI>                   pending_approval article with no Buffer draft recorded
  manual:<DOI>                    article flagged needs_manual_review
  sources:<run file>              a check where a discovery source failed
  runerror:<date>:<text>          an error passed with --run-error

This script only reads the register. It never contacts Buffer, LinkedIn or Gmail.
"""
import datetime as dt, hashlib, html, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
REGISTER = HERE / "register.json"
RUNS = HERE / "runs"
LOG = HERE / "notifications.json"
OUTBOX = HERE / "outbox" / "notification.json"
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))

BUFFER_URL = "https://publish.buffer.com"
CLOSING = ("Please review the drafts in Buffer. Select Add to Queue for any posts you approve. "
           "Buffer will publish them according to the journal's posting schedule.")


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_log():
    if LOG.exists():
        return json.loads(LOG.read_text(encoding="utf-8"))
    return {"notified": {}, "attempts": []}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def latest_run():
    files = sorted(RUNS.glob("*-check.json"))
    return (files[-1], json.loads(files[-1].read_text(encoding="utf-8"))) if files else (None, None)


def collect(run_error=None):
    arts = json.loads(REGISTER.read_text(encoding="utf-8"))["articles"]
    done = load_log()["notified"]
    drafts, problems = [], []
    for doi, rec in sorted(arts.items()):
        st = rec.get("status")
        if st == "pending_approval":
            bid = rec.get("buffer_draft_id")
            key = f"draft:{doi}:{bid}" if bid else f"nodraft:{doi}"
            if key in done:
                continue
            if bid:
                drafts.append({"key": key, "doi": doi, "title": rec.get("title", ""), "buffer_draft_id": bid,
                               "provisional": bool(rec.get("provisional"))})
            else:
                problems.append({"key": key, "doi": doi, "title": rec.get("title", ""),
                                 "what": "Carousel built, but no Buffer draft was recorded. "
                                         f"Local files: {rec.get('folder', '(folder not recorded)')}"})
        elif st == "needs_manual_review":
            key = f"manual:{doi}"
            if key not in done:
                problems.append({"key": key, "doi": doi, "title": rec.get("title", ""),
                                 "what": "Needs manual review: " + (rec.get("manual_reason") or "reason not recorded")})
    path, run = latest_run()
    if run:
        bad = {s: v for s, v in run.get("sources", {}).items() if not str(v).startswith("ok")}
        key = f"sources:{path.name}"
        if bad and key not in done:
            problems.append({"key": key, "doi": None, "title": "",
                             "what": "Discovery source problem in the check of " + run.get("started", path.name) + ": "
                                     + "; ".join(f"{s}: {v}" for s, v in bad.items())})
    if run_error:
        key = f"runerror:{dt.date.today().isoformat()}:{hashlib.sha1(run_error.encode()).hexdigest()[:10]}"
        if key not in done:
            problems.append({"key": key, "doi": None, "title": "", "what": "Scheduled run error: " + run_error})
    return drafts, problems


def compose(drafts, problems):
    n = len(drafts)
    if n:
        subject = f"[RSTE LinkedIn] {n} post{'s' if n != 1 else ''} ready for review"
    else:
        subject = f"[RSTE LinkedIn] Action needed: {len(problems)} issue{'s' if len(problems) != 1 else ''} in the scheduled run"
    t = [f"{n} new RSTE LinkedIn post{'s are' if n != 1 else ' is'} saved as {'drafts' if n != 1 else 'a draft'} in Buffer "
         "for the Research in Science & Technological Education LinkedIn Page." if n else
         "No new Buffer drafts were created in this run, but something needs your attention.", ""]
    h = [f"<p>{html.escape(t[0])}</p>"]
    if drafts:
        h.append("<ol>")
        for i, d in enumerate(drafts, 1):
            t += [f"{i}. {d['title']}", f"   DOI: https://doi.org/{d['doi']}",
                  f"   Buffer draft ID: {d['buffer_draft_id']} (open {BUFFER_URL} > RSTE LinkedIn Page > Drafts)"]
            if d["provisional"]:
                t.append("   CHECK BEFORE APPROVING: abstract and affiliations come from OpenAlex/Crossref, not the "
                         "publisher page. Compare them with the tandfonline page.")
            t.append("")
            h.append(f"<li><strong>{html.escape(d['title'])}</strong><br>"
                     f"DOI: <a href=\"https://doi.org/{d['doi']}\">{d['doi']}</a><br>"
                     f"Buffer draft ID: <code>{d['buffer_draft_id']}</code>"
                     + ("<br><strong>Check before approving:</strong> abstract and affiliations come from OpenAlex/Crossref, "
                        "not the publisher page. Compare them with the tandfonline page." if d["provisional"] else "")
                     + "</li>")
        h.append("</ol>")
    if problems:
        t.append("NEEDS YOUR ATTENTION")
        h.append("<p><strong>Needs your attention</strong></p><ul>")
        for p in problems:
            head = f"{p['title']} (https://doi.org/{p['doi']}): " if p["doi"] else ""
            t.append(f"- {head}{p['what']}")
            link = (f"<a href=\"https://doi.org/{p['doi']}\">{html.escape(p['title'] or p['doi'])}</a>: " if p["doi"] else "")
            h.append(f"<li>{link}{html.escape(p['what'])}</li>")
        t.append("")
        h.append("</ul>")
    t += [f"Buffer: {BUFFER_URL}", "", "To approve a post, open its draft, check the caption and all three PDF pages, "
          "and select \"Add to Queue\". Nothing is published or scheduled until you do this.", "", CLOSING, "",
          "Sent by the RSTE LinkedIn scheduled run (Claude Code)."]
    h += [f"<p><a href=\"{BUFFER_URL}\">Open Buffer (publish.buffer.com)</a></p>",
          "<p>To approve a post, open its draft, check the caption and all three PDF pages, and select "
          "<strong>Add to Queue</strong>. Nothing is published or scheduled until you do this.</p>",
          f"<p>{html.escape(CLOSING)}</p>",
          "<p style=\"color:#666;font-size:12px\">Sent by the RSTE LinkedIn scheduled run (Claude Code).</p>"]
    return subject, "\n".join(t), "\n".join(h)


def cmd_prepare(argv):
    run_error = argv[argv.index("--run-error") + 1] if "--run-error" in argv else None
    to = (CONFIG.get("notify_to") or "").strip()
    if not to:
        print("No notification address: set \"notify_to\" in pipeline/config.json. Nothing sent.")
        return 4
    drafts, problems = collect(run_error)
    if not drafts and not problems:
        OUTBOX.unlink(missing_ok=True)
        print("Nothing new to notify. Do not send an email.")
        return 3
    subject, body, html_body = compose(drafts, problems)
    msg = {"prepared": now(), "to": [to], "subject": subject, "body": body, "html_body": html_body,
           "keys": [x["key"] for x in drafts + problems],
           "draft_dois": [d["doi"] for d in drafts]}
    save_json(OUTBOX, msg)
    print(json.dumps(msg, indent=2, ensure_ascii=False))
    return 0


def cmd_sent(message_id):
    if not OUTBOX.exists():
        sys.exit("No prepared notification in pipeline/outbox/. Run `prepare` first.")
    msg = json.loads(OUTBOX.read_text(encoding="utf-8"))
    log = load_log()
    for k in msg["keys"]:
        log["notified"][k] = {"at": now(), "gmail_message_id": message_id}
    log["attempts"].append({"at": now(), "result": "sent", "gmail_message_id": message_id,
                            "subject": msg["subject"], "to": msg["to"], "keys": msg["keys"]})
    save_json(LOG, log)
    OUTBOX.unlink()
    print(f"Recorded {len(msg['keys'])} item(s) as notified (Gmail message {message_id}).")
    return 0


def cmd_failed(reason):
    msg = json.loads(OUTBOX.read_text(encoding="utf-8")) if OUTBOX.exists() else {}
    log = load_log()
    log["attempts"].append({"at": now(), "result": "failed", "reason": reason,
                            "subject": msg.get("subject"), "keys": msg.get("keys", [])})
    save_json(LOG, log)
    print("Recorded failed attempt; the items stay unsent and will be retried next run.")
    return 0


def cmd_log():
    log = load_log()
    for a in log["attempts"][-10:]:
        print(f"{a['at']}  {a['result']:6}  {a.get('subject')}  {a.get('gmail_message_id') or a.get('reason', '')}")
    print(f"{len(log['notified'])} item(s) notified in total.")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]
    if cmd == "prepare":
        return cmd_prepare(rest)
    if cmd == "sent" and len(rest) == 1:
        return cmd_sent(rest[0])
    if cmd == "failed" and len(rest) == 1:
        return cmd_failed(rest[0])
    if cmd == "log":
        return cmd_log()
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
