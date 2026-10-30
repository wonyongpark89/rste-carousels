# RSTE new-article pipeline

Discovery → draft → Buffer **draft** + email to the Editor → Editor approves in Buffer ("Add to Queue").

Scheduled runs host each new carousel and create a Buffer draft (`prepare-draft`, then `record-buffer-draft`, which refuses anything whose Buffer status is not `draft`), then send one Gmail notification (`notify.py`). They never queue, schedule or publish.

| File | Purpose |
|---|---|
| `rste_pipeline.py` | all commands (stdlib Python only) |
| `config.json` | feed URL, ISSN, look-back windows, host repo, Buffer channel |
| `register.json` | persistent DOI register: status and event history per article (`register.bak.json` = previous copy) |
| `runs/*.json` | raw result of each check |
| `reports/latest-report.md` | human report of the last run |
| `notify.py` | builds the one review-notification email per run (`prepare` / `sent` / `failed` / `log`); address is `notify_to` in `config.json` |
| `notifications.json` | what has already been emailed, so nothing is notified twice |
| `SCHEDULED_TASK_PROMPT.md` | the prompt to paste into the recurring Claude Code Desktop task |

## How discovery works

- The "Latest articles" page `toc/crst20/0/0` returns HTTP 403 to scripts (Cloudflare). The checker therefore reads the **official T&F RSS feed** for crst20, which lists the same ahead-of-print articles plus the current issue. `dc:date` is the first online date. `prism:volume`/`number` appear only once the article is in an issue.
- **Crossref** (ISSN 0263-5143) is the secondary source, read with cursor pagination. It is the authority for author lists and `published-online`. A DOI found only in RSS is looked up in Crossref individually.
- Each request is retried four times with back-off (timeouts, 429, 5xx). If one source fails, the run continues with the other and the report says so. If both fail, nothing is added and the command exits with code 2.
- The **first run** stored everything visible as `baseline` (116 articles on 2026-10-16) plus the two carousels already made (`pre_existing`). No posts are generated for them.
- On later runs, a DOI not in the register is:
  - `new` if it was first published online on or after the baseline (−7 days);
  - `skipped_pre_baseline` if it is older, which normally means an old article has just been assigned to an issue;
  - `skipped_non_article` for corrections, editorials and similar;
  - `needs_manual_review` if Crossref lacks the title, authors or online date.
- A known DOI that gains a volume/issue gets an `issue_assigned` event only. It never gets a second post.
- To post a baseline article anyway: `enqueue <DOI>`.

## Draft generation (done by Claude in the scheduled run)

For each `new` DOI, Claude follows the `rste-article-carousel` skill unchanged: `fetch_metadata.py`, then publisher-page verification in the built-in browser, then `content.json`, then `build.py`. Then `record-draft <DOI> "<folder>"` stores file paths and SHA-256 hashes and sets `pending_approval`. If the abstract or affiliations cannot be confirmed, the build fails, or the browser cannot reach tandfonline, Claude runs `flag <DOI> "reason"` instead. Nothing is invented.

Folder naming is unchanged: `article-carousels/<First author> - <first six title words>/`, because the Editor found DOI-named folders hard to recognise. The register maps each DOI to its folder, and every `metadata.json` holds the DOI.

## Approval and publishing

See `../CLAUDE.md`. Approval locks the files by hash; any later change voids it. Publishing hosts the PDF and cover in the public `rste-carousels` GitHub Pages repo, posts through the Buffer MCP to the RSTE LinkedIn **Page** channel, and records the Buffer post ID and status only after Buffer confirms.

## Scheduling (Claude Code Desktop)

1. Run it manually first: open this folder in Claude Code and paste the prompt from `SCHEDULED_TASK_PROMPT.md` (or run `python pipeline/rste_pipeline.py check` then `report`).
2. Then, in the Claude Desktop app, open the scheduled task `rste-new-article-linkedin-post` (sidebar → Scheduled), replace its prompt with `SCHEDULED_TASK_PROMPT.md`, and set the frequency:
   - **weekly**: e.g. Mondays 08:00;
   - **fortnightly**: the scheduler has no fortnightly preset. Use weekly; a weekly check of an empty feed costs little. Alternatively, ask Claude to "make the RSTE check run every other Monday", which sets a custom cron, e.g. `0 8 1-7,15-21 * 1` (about fortnightly).
3. Set the working folder to this project folder. The run needs network access and the built-in browser (for publisher-page verification). Without the browser, articles are flagged for manual review rather than drafted.
