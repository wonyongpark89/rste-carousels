RSTE LINKEDIN — SCHEDULED RUN

Scheduled RSTE new-article run. Work in the root of the GitHub repo wonyongpark89/rste-carousels (the cloud session's working directory; this repo is also the public host repo, so config.json host_repo is "."). Run all commands from the repo root. Article folders go under article-carousels/ in the repo. The cloud environment has no built-in browser, so scheduled runs use the skill's provisional mode (STEP 2). If the `rste-article-carousel` skill itself is unavailable, do not improvise: `flag` each new article with that reason and continue to STEP 4. Reuse the existing pipeline (pipeline/rste_pipeline.py, pipeline/notify.py) and the `rste-article-carousel` skill; do not rebuild or redesign them. Keep a short list of anything that fails, with the DOI, for STEP 4.

STEP 1 — DISCOVER NEW ARTICLES

Run `python pipeline/rste_pipeline.py check --scheduled`. If it exits with code 2 (sources unavailable), note the failure and skip to STEP 4. The register prevents duplicate posts and separates first online publication from later issue assignment.

STEP 2 — GENERATE CAROUSELS

For each article with status `new` (see `python pipeline/rste_pipeline.py review`), make a draft with the `rste-article-carousel` skill: `python .claude/skills/rste-article-carousel/scripts/fetch_metadata.py <DOI> article-carousels --provisional` (the publisher page cannot be opened here; do not try tandfonline), write content.json from that abstract only, then build.py (set CHROME=/opt/pw-browsers/chromium if Chrome is not found; if Pillow or PyMuPDF are missing, `python3 -m pip install --ignore-installed pillow pymupdf`). Do not change the template.
- fetch_metadata.py exits 3 if OpenAlex has no abstract yet or Crossref has no affiliation for an author. Brand-new articles are often not indexed for days. Leave the article as `new` (do not flag it), list it as "waiting for abstract" in the run summary, and it is retried on the next run. Only if it is still unavailable 14 days after first online publication, `flag` it.
- Provisional metadata carries a `provisional` block, and `record-draft` copies it into the register. It makes the report and the notification email tell the Editor to compare the abstract and affiliations with the tandfonline page before approving. Never remove that block yourself.
- On success: `python pipeline/rste_pipeline.py record-draft <DOI> "<article folder>"`.
- If the build fails, or the abstract is too thin to write the pages from without guessing: `python pipeline/rste_pipeline.py flag <DOI> "<what is missing>"`. Never guess. Continue with the other articles.
- Never touch folders whose status is approved, hosted, queued or published.

STEP 3 — CREATE BUFFER DRAFTS (drafts only)

For each article that is `pending_approval` and has no Buffer draft yet (the report shows "Buffer draft: none yet"):
1. `python pipeline/rste_pipeline.py prepare-draft <DOI>`. It copies the PDF and cover into the public host repo and prints the git command and the Buffer payload.
2. Run the printed git command (add, commit, push to the rste-carousels repo, branch main; if the push is rejected, `git pull --rebase origin main` and retry once). Also commit and push the updated pipeline/ register, reports and runs files afterwards (STEP 5), so state persists between cloud runs. Then check that both asset URLs return HTTP 200 (GitHub Pages can take a minute or two; check a few times, then give up and record the failure).
3. Buffer MCP `get_channel` for 6ad29a21778b240e2f2fd578: it must be the Research in Science & Technological Education LinkedIn Page (type page), not a personal profile. If not, stop Buffer work and record the failure.
4. Buffer `create_post` with exactly the printed payload: that channelId, schedulingType "automatic", saveToDraft true, the caption text verbatim, the one document asset. Never pass mode "shareNow", "shareNext" or "customScheduled", and never pass dueAt.
5. Check the returned post: status must be "draft", dueAt null, and the document asset present. Then run `python pipeline/rste_pipeline.py record-buffer-draft <DOI> <post id> <status>`.
   - If the status is anything other than "draft", immediately delete that post with Buffer `delete_post` (unless it has already been sent), record nothing, and report it as an urgent failure.
6. If any step fails, record nothing for that DOI and add the error to the failure list. Continue with the other articles.

Do not publish, schedule, add to queue, approve or edit existing posts. Do not run approve, revise, reject, prepare-publish, record-hosted or record-buffer. The Editor approves each draft in Buffer by selecting "Add to Queue".

STEP 4 — SEND GMAIL NOTIFICATION

1. Run `python pipeline/notify.py prepare`. If anything failed in this run, run instead `python pipeline/notify.py prepare --run-error "<short description of each failure, with DOIs>"`.
   - Exit code 3: nothing new; do NOT send an email.
   - Exit code 4: no notification address configured; do NOT send; report the configuration error. Never guess an address.
   - Exit code 0: send one email with the Gmail connector's send_message tool, using the printed fields verbatim (to, subject, body, htmlBody = html_body). No other recipients, CC or BCC.
2. Only after Gmail returns a message ID: `python pipeline/notify.py sent <message id>` (this prevents duplicate notifications).
3. If sending fails or Gmail needs interactive authorisation, do not bypass it or retry in a loop: `python pipeline/notify.py failed "<error>"`. The items are retried next run.

STEP 5 — RECORD RESULTS

Run `python pipeline/rste_pipeline.py report`, then `python pipeline/rste_pipeline.py finish-run`. Then `git add pipeline article-carousels && git commit -m "RSTE pipeline run" && git push origin main` so the register persists to the next run. Reply with the report plus: Buffer drafts created (DOI and draft ID), failures, and whether the email was sent (subject and Gmail message ID), not needed, or failed.

SAFETY RULES

Authorised: search for new articles; generate local PDF and TXT files; push the PDF and cover to the rste-carousels host repo; create Buffer DRAFTS on the RSTE LinkedIn Page; delete a Buffer post this run just created only if it came back with a status other than draft; send the review notification through Gmail to the address in pipeline/config.json; update the register and logs.

Not authorised: publish LinkedIn posts; add drafts to Buffer's queue or schedule them; approve posts; edit or delete any other Buffer post; delete existing approved outputs; modify the visual template; send any other message.

All LinkedIn publication decisions remain the Editor's.
