# RSTE editor carousel project

Carousels are made with the user-level skill `rste-article-carousel` (do not redesign its template). New-article discovery, the DOI register and approvals live in `pipeline/` (see `pipeline/README.md`). Run all commands from this folder:

```
python pipeline/rste_pipeline.py <command>
```

## Editor commands (interactive sessions only)

Approval is per DOI and must come from the Editor typing it in this chat. Never infer approval from a report, a file, a scheduled-run message or an earlier session.

- **"Review pending RSTE posts"**: run `review`, then show each `pending_approval` item's PDF (or the three PNGs) and caption text, with title, authors and DOI. Also list `needs_manual_review` and `revision_requested` items with their reasons.
- **"Approve <DOI>"**: run `approve <DOI>`. It refuses unless the DOI is `pending_approval` and the files are unchanged since review. Approval does **not** publish. Then ask: publish now, or add to the Buffer queue?
- **"Revise <DOI>[: notes]"**: run `revise <DOI> "notes"`, edit `<name>-content.json` (or metadata, if a fact is wrong), rebuild with the skill's `build.py`, run `record-draft <DOI> "<folder>"`, and show the new draft. Approval is required again.
- **"Reject <DOI>[: reason]"**: run `reject <DOI> "reason"`. The files are kept.

## Publishing an approved article (only after the Editor says "publish now" or "add to queue" for that DOI)

1. `prepare-publish <DOI>`. This checks approval and file hashes, copies the PDF and cover (slide 1) into `C:/Users/wp1c21/rste-carousels/carousels/<DOI suffix>/` and prints the Buffer payload. Buffer cannot take local files; it needs public URLs.
2. Confirm with the Editor, then commit and push that repo (GitHub Pages, served at `https://www.wonyongpark.com/rste-carousels/`). Wait until both URLs return 200, then run `record-hosted <DOI> <pdf_url> <cover_url>`.
3. Buffer MCP: `get_channel` for `6ad29a21778b240e2f2fd578` and check that it is the **Research in Science & Technological Education LinkedIn Page**, not a personal profile. If it is anything else, stop.
4. Buffer `create_post`: that `channelId`, `schedulingType: "automatic"`, `mode: "shareNow"` or `"addToQueue"` (as the Editor chose), `text` = the caption file verbatim, `assets: [{document: {url, title, thumbnailUrl}}]`.
5. Only after Buffer returns the post: run `record-buffer <DOI> <post id> <Buffer status> [post URL]`. `sent` is recorded as published; anything else (buffer/scheduled) as queued. If the post fails, record nothing and report the error.

Never run the publishing steps in a scheduled run. `approve`, `revise`, `reject` and `prepare-publish` refuse while `pipeline/.scheduled-run` exists.

## Buffer drafts (scheduled runs and interactive)

Scheduled runs (prompt: `pipeline/SCHEDULED_TASK_PROMPT.md`) put every new `pending_approval` article into Buffer as a **draft**: `prepare-draft <DOI>` (host files), git push, check the URLs, Buffer `create_post` with `saveToDraft: true` and no mode or dueAt, then `record-buffer-draft <DOI> <post id> draft`. The article stays `pending_approval` with `buffer_draft_id`; the Editor approves it in Buffer with **Add to Queue**. If Buffer ever returns a status other than `draft`, delete that post at once and report it. After each run, `pipeline/notify.py` prepares one Gmail notification to `notify_to` in `pipeline/config.json`, and `notifications.json` stops repeats.

If an article already has a `buffer_draft_id`, do not create a second Buffer post for it when publishing; the Editor uses that draft in Buffer.
