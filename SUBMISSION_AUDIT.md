> **Upgrade note:** This document records the original pre-AI audit (7 classic quizzes, 25 curated questions, 167 tests). The application now also has the AI Practice Studio; see [`AI_UPGRADE_NOTES.md`](AI_UPGRADE_NOTES.md) for the exact report/PPT changes and the updated test count (198).

# Submission-readiness audit

**Date:** 12 October 2026, Asia/Kolkata. **Scope:** existing Flask/SQLAlchemy/SQLite project; correctness and reproducibility, no new product features or visual redesign.

## Verdict

The corrected project passes the executed functional checks for a **local academic prototype**. It is **not evidence of a superior recommender, a verified novel research combination, or improved learning**. The four-case synthetic comparison has material validity limitations and the adaptive method performs worse than both baselines on its aggregate ranking metrics.

### Important database side effect

An early audit probe mistakenly executed reset against the default workspace development database, not an isolated database. It was reseeded afterward. Any learner activity present before that reset would have been removed; no pre-reset backup or recovery was verified. This is not described as preserved data. The final workflow, security, reset, and persistence tests instead use in-memory databases or a temporary on-disk database outside the workspace. Reset now refuses production/non-SQLite targets, but remains destructive when explicitly used in development.

## Checks and results

| Requested check | Result and evidence |
| --- | --- |
| Complete pytest suite | Initial baseline: `44 passed in 13.53s`, but it missed several defects. Final fresh-environment run: `167 passed in 32.99s` with `-W error`; no skipped tests or warnings in that run. |
| Python compilation | `python -m compileall -q app tests config.py seed.py run.py` executed successfully. |
| JavaScript syntax | `node --check app\static\js\app.js` executed successfully. This does not execute browser JavaScript. |
| Dependency installation | Created a new venv outside the workspace and installed `requirements.txt`; installation passed. `python -m pip check` returned `No broken requirements found.` |
| Offline comparison | Regenerated from the seeded 21-resource catalog: 4 labeled synthetic cases, K=5, adaptive/content/stable methods. Instrumented tests confirm the identical candidate tuple and K for all three methods, with pre-split filtering. |
| Label independence | Reversing all rankers leaves the generated labels unchanged. This establishes output independence only, **not independent expert/learner relevance judgments**. |
| Metric arithmetic | Independent test calculations verify per-case metrics, aggregate macro means, per-scenario means, coverage, and runtime mean arithmetic. Existing tests also check nontrivial DCG ranks, short lists, no labels, invalid K, duplicate IDs and future-event exclusion. |
| Mastery sensitivity | Verified the three-score formula and implementation at four rates; recorded real planner IDs/priority changes in isolated manual-state tests. Attempt-backed replay is fixed at 0.35, not configurable through the manual helper argument. |
| Auth/CSRF/access | Password hashing and exact password preservation, malformed auth/quiz input rejection, session handling, missing/invalid CSRF tokens, and HTML/API evaluation access are exercised. Anonymous: 401; learner: 403; admin: 200. Disabled demo logins and existing demo sessions are rejected. |
| Clean setup/demo/reset | Real Flask CLI subprocess and HTTP cookie client, CSRF enabled, disposable disk SQLite database: seed twice, login, two quizzes, completion, refresh, new-user isolation, logout, stop server, new app reads same DB, non-destructive seed, then explicit isolated reset. All passed. |
| Related work | All five publication identities can be matched to actual records; corrected one conflated citation year/title. DKT abstract read. Full-text limitation claims remain partially/unverified; see `PROJECT_GUIDE.md`. |

### Fresh verification environment

- Python 3.13.5; Windows PowerShell 5.1; Node v20.20.0.
- Fresh dependencies included Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.4, Flask-WTF 1.3.0, WTForms 3.2.2, pytest 8.4.2.
- The old workspace venv did **not** contain pytest; system Python had hidden that setup gap. `pytest>=8.3,<9` is now in `requirements.txt`.
- Environment path used for the clean install: `C:\Users\NOVINK~1\AppData\Local\Temp\omnirush\submission-audit-venv`.
- Runtime measurements below vary between executions; rankings and metric values were reproducible for the same catalog/cases.

## Defects reproduced and corrected

1. **Setup:** requirements omitted pytest. README also implied copying `.env` was enough, although no guaranteed dotenv loader exists. Added pytest; documented process-environment configuration instead of silently adding another loader.
2. **Metric helpers:** `metrics.py` used returned-list length for Precision@K while the offline evaluator used K; absent-label behavior also differed. All public helpers now delegate to the same validated metric function.
3. **Completion rendering:** library routes did not pass learner completion state, so completion badges were lost on refresh. Correct context is now supplied without changing the template or CSS.
4. **Quiz correctness:** Python answers were compared case-insensitively and malformed/non-option/unknown-question payloads could be accepted or crash. Exact-option grading and object/answer validation now reject these payloads; omitted answers still count as incorrect as before.
5. **Atomicity/mastery:** quiz records committed separately from mastery, and stale caches could differ from replay. Attempt, responses and refreshed mastery now commit together; regression tests inject a write failure and verify rollback.
6. **Authentication:** malformed JSON handling, registration password trimming and HTML logout behavior were corrected. Existing valid JSON contracts were retained.
7. **Production safeguards:** production cannot enable the published demo administrator, rejects known placeholder/missing secrets before DB initialization, and uses Secure cookies. Existing demo sessions are rejected when disabled. Direct `python run.py` no longer forces the debugger on.
8. **Reset safety:** reset checks environment and every database engine before any drop. Production/staging and non-SQLite targets are refused. Seed output no longer prints credentials or falsely says a disabled demo was created.
9. **Test teardown:** the first fresh-environment `-W error` run completed 11 assertions/tests but failed teardown due to unclosed SQLite connections. Engine/session disposal was corrected in fixtures and the disk audit context; the final strict suite passed.

Agent reproduction runs before fixes found 6 failing security probes and 44 failing consistency probes. Those were genuine newly exposed issues, not a failing original suite. Invalid ad-hoc shell probes were corrected and rerun; they are not counted as verification passes.

## Regenerated offline evaluation

**Dataset:** `synthetic-learning-scenarios-v2`. **21 resources, 4 cases, 4 labeled cases, 1 case per scenario, K=5.** These are seeded demonstration results, not real learner outcomes. No model parameters or label rules were retuned to obtain these results during the audit.

| Method | Precision@5 | Recall@5 | NDCG@5 | Coverage | Illustrative mean ranking runtime |
| --- | ---: | ---: | ---: | ---: | ---: |
| Adaptive | 0.050000 | 0.250000 | 0.250000 | 0.285714 (6/21) | about 0.029 ms |
| Stable catalog baseline | 0.150000 | 0.500000 | 0.375316 | 0.238095 (5/21) | about 0.003 ms |
| Content-based baseline | 0.250000 | 1.000000 | 1.000000 | 0.571429 (12/21) | about 0.007 ms |

Each scenario cell below is **Precision / Recall / NDCG at K=5**:

| Scenario | Adaptive | Stable | Content-based |
| --- | --- | --- | --- |
| Beginner cold start | 0.2 / 1 / 1 | 0.2 / 1 / 1 | 0.2 / 1 / 1 |
| Struggling with a topic | 0 / 0 / 0 | 0.4 / 1 / 0.501266 | 0.4 / 1 / 1 |
| Ready for advanced material (author-assigned name) | 0 / 0 / 0 | 0 / 0 / 0 | 0.2 / 1 / 1 |
| Revision due (time-policy case) | 0 / 0 / 0 | 0 / 0 / 0 | 0.2 / 1 / 1 |

### Arithmetic and timing definitions verified

- Binary labels are a set of relevant resource IDs. Precision is hits/K even if fewer than K items are returned. Recall is hits/number of relevant IDs.
- DCG uses `sum(relevance_at_rank / log2(rank + 2))` with zero-based ranks. IDCG has `min(K, relevant_count)` ideal hits; NDCG is DCG/IDCG.
- No/empty labels yield null, not a fabricated zero measurement. Such cases are excluded from precision/recall/NDCG macro means, but can contribute to coverage.
- Coverage is the union of returned top-K IDs divided by full catalog size, not the number of hits or number of cases.
- Runtime uses `perf_counter()` around one ranking call per method/case; mean runtime is total/case count. Dataset loading, shared filtering, metrics, rendering, network and database cost of the live ranker are excluded. These microsecond-scale samples are not a throughput benchmark or proof of efficiency at scale.
- The two metrics implementations previously disagreed; they now share the offline evaluator's convention. Independent calculations, not only calls to that same helper, check the output.

### What does NOT pass as a research-validity claim

1. **Equal pools are verified; equal information is not true.** Stable order ignores history, adaptive uses history, and content-based receives explicit target topic/difficulty authored alongside the labels. In the struggling case the difficulty is even selected from the labeled subset. This strong alignment explains the content baseline's perfect NDCG; it is not independently collected preference evidence.
2. **Label independence is limited.** No ranking function is called to construct labels, and changing outputs does not change labels. Nevertheless, label rules and content features overlap structurally. They have no external annotator, inter-rater agreement, or held-out real-world validation.
3. **Only four hand-built cases.** One case per situation; scenario is confounded with selected topic (catalog-ID order). There are no repetitions, balanced topic coverage, confidence intervals or significance tests. K=5 exceeds the one/two labeled items, so perfect recall need not imply high precision.
4. **Advanced readiness is mislabeled as a fact.** Two topic scores `[0.9, 0.95]` replay to `0.5373`, below the project's 0.65 threshold. The prerequisite histories yield `0.315`, below 0.6. The name is author intent, not readiness demonstrated by the application. The case was not silently rewritten during this audit.
5. **Revision is a policy, not forgetting evidence.** A 21-day-old completion is outside the 14-day filter window. The scenario has no quiz/retention evidence. Adaptive ranking does not currently add a revision boost; it merely allows the old resource back into the candidate pool.
6. **Adaptive behavior is narrower than earlier documentation implied.** The score penalizes difficulty monotonically, even for strong mastery. Repeated mistakes/declining performance are not separately modeled; recent scores influence EMA and wording. These are remaining algorithm limitations, not fixed by re-labeling tests. The offline numerical adaptive proxy was checked against the live ranker for all four cases and matched; runtime still excludes live database-query costs.

These risks are now present in README, PROJECT_GUIDE, and the evaluation report assumptions. Ranking code and scenario labels were left intact rather than improved merely to make the audit favorable. A defensible next research phase needs independently reviewed labels, comparable input information, corrected readiness histories, broader cases and real learner evidence. That is outside this no-feature audit.

## Mastery sensitivity: mathematical and implementation checks

For constant score 0.8 and initial estimate 0, the unrounded closed form after three updates is `0.8 × (1 - (1 - alpha)^3)`. The implementation rounds each update to four decimals. Both yield the following displayed results for this specific sequence:

| Alpha | After one | After three | Actual primary + support IDs in seeded manual-state replay | Variables beginner priority |
| ---: | ---: | ---: | --- | ---: |
| 0.20 | 0.1600 | 0.3904 | 1, 2, 4 | 68.34 |
| 0.35 | 0.2800 | 0.5803 | 4, 16, 1 | 61.69 |
| 0.50 | 0.4000 | 0.7000 | 4, 5, 7 | 57.50 |
| 0.80 | 0.6400 | 0.7936 | 4, 5, 7 | 54.22 |

IDs are tied to the fresh seed order: 1/2 = Variables guide/practice, 4/5 = Data Types guide/practice, 7 = Conditionals guide, 16 = Lists guide. The earlier quality test checked only **one** observation and priority direction, not the documented three-observation sequence or queue. The audit adds those missing checks.

The custom-rate replay deliberately has no `QuizAttempt` rows. Actual quiz-attempt replay always uses 0.35, ordered by timestamp then ID. The tests now verify this distinction. No assertion is made that alpha=0.35 is optimal, calibrated, or measures definite knowledge. The zero initial prior makes early estimates conservative and should be disclosed.

## Clean development workflow evidence

The final disk-database HTTP test runs `seed.py` twice, starts `python -m flask --app run.py run --host 127.0.0.1 --port <temporary-port> --no-debugger --no-reload`, and uses actual HTTP requests and cookies:

- Anonymous evaluation access rejected; login without CSRF rejected.
- Demo login with a valid CSRF token accepted; cold-start weak list empty.
- Variables quiz 1: 25% score, mastery 0.0875, no previous score.
- Variables quiz 2: 100% score, previous score 25%, mastery 0.4069; reasons/priorities reported as changed (not necessarily different resource IDs).
- Repeated completion POSTs leave **one unique completed resource**; 1/21 completion count and library completed badge survive refresh.
- Normal learner registration succeeds but both evaluation routes reject it; `?user_id=1` cannot expose the demo's private progress.
- Admin evaluation HTML is genuinely HTML, not a hidden JSON fallback; all three methods and four cases are available.
- After HTTP server shutdown, a new app reads two attempts, eight responses, one completion, and the same mastery from disk. Re-running ordinary seed preserves these records.
- Explicit reset on this disposable database removes learner state and restores 7 topics / 21 resources / 7 quizzes / 25 questions and the local demo account.

No browser rendering engine was used in this final audit. The HTTP flow verifies routes, HTML rendering and persistence, not button-click JavaScript execution, responsive visual layout or keyboard behavior. CSS/templates were not redesigned. A final manual browser walkthrough remains recommended.

## Authentication and reset boundaries

Verified protections include Werkzeug password hashing, server-scored selected answers, session-bound private progress, Flask-WTF CSRF on form and JSON writes, HttpOnly/SameSite cookies, production Secure cookies, and admin-only evaluation routes. Known development/placeholder secrets are refused in production. This is **not** a penetration test: password brute-force throttling, recovery flows, multi-worker concurrency, TLS deployment, dependency vulnerability scanning and long-running production operations were not certified.

Production mode now blocks the demo account regardless of the enable flag and rejects existing demo sessions. Disabling demo seeding does not delete the persisted user; access is blocked instead. Changing secret/environment still requires restarting the process. Secret quality beyond known placeholders is the operator's responsibility.

Reset is a CLI action, not a web endpoint. The guard checks environment and database engines before dropping tables. It is still destructive for development/test SQLite, including existing users, and has no automatic backup. Never run it on important data without a verified backup.

## Bibliography verification

See `PROJECT_GUIDE.md` for source links and per-reference evidence. The Manouselis four-author book was incorrectly dated 2011; Crossref identifies the matching book as **2013**, with a different 2011 TEL chapter. This was corrected. MFF-CF metadata confirms the supplied authors/title/date (21 August 2026)/DOI, but its full text returned a publisher challenge. Brusilovsky & Millán identity/pages and the 2007 parent volume were verified. DKT's NeurIPS abstract explicitly claims interpretability; the unsupported contrary attribution was removed. Settles & Meeder's ACL identity/year/pages were verified; PDF extraction was not readable.

Earlier table cells labeled "documented limitations" were not established with page-level full-text evidence. They are now marked as unverified hypotheses/scope questions. This audit does not establish that the proposed combination is missing from prior work or is novel.

## Reproduce the checks and launch

From the project root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m compileall -q app tests config.py seed.py run.py
node --check app\static\js\app.js
.\.venv\Scripts\python.exe -m pip check
# Show regenerated synthetic results and sensitivity output:
.\.venv\Scripts\python.exe -m pytest tests/test_submission_audit.py -q -s
# Non-destructive seed and local server:
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe -m flask --app run.py run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000/login`. The fresh-environment audit used the same commands with the external venv interpreter and a temporary `DATABASE_URL`, not a second reset of the working database. No OS other than Windows was tested.

## Changed files in this audit

- Setup/docs: `requirements.txt`, `.gitignore`, `README.md`, `PROJECT_GUIDE.md`, `SUBMISSION_AUDIT.md`.
- Safety/auth: `config.py`, `seed.py`, `run.py`, `app/__init__.py`, `app/routes/auth.py`, `app/routes/common.py`.
- Correctness: `app/routes/learning.py`, `app/services/mastery.py`, `app/services/metrics.py`.
- Evaluation: `app/services/offline_evaluation.py` (assumption text only; no ranking/label changes).
- Verification: `tests/conftest.py`, `tests/test_audit_security.py`, `tests/test_audit_consistency.py`, `tests/test_submission_audit.py`.
- Workspace side effect: the default `instance/dynamic_learning.sqlite3` was reset/reseeded early in the audit as disclosed above; later non-destructive `seed()` calls only refreshed the catalog. It is private and ignored by version control.

**Remaining unverified:** full-paper limitation claims, novelty, unbiased effectiveness, real learning improvement, real-browser execution/visual behavior, production deployment/load/concurrency, and preservation/recovery of any pre-audit learner data.

## Final report-package completeness check

| Required report material | Status |
| --- | --- |
| Architecture | Present: Mermaid architecture and database diagrams in `README.md`; module explanation in `PROJECT_GUIDE.md`. |
| Algorithm explanation | Present: mastery EMA, candidate filtering, scoring formula, prerequisites, completion/revision policy, and explanations in `README.md`/`PROJECT_GUIDE.md`. |
| Test evidence | Present: `167 passed` strict suite, compile, JavaScript syntax, dependency, security, HTTP, persistence, and reset evidence in this file. |
| Limitations | Present: benchmark bias, unverified research claims, synthetic-data limitations, reset disclosure, and unverified production/browser claims. |
| References | Present: related-work table and source links in `PROJECT_GUIDE.md`; full-text limitations are explicitly marked. |
| Future work | Present in `PROJECT_GUIDE.md`, including independently reviewed labels, real learner evidence, delayed tests, and instructor tools. |
| Screenshots | **Not found in the repository.** No `png`, `jpg`, `jpeg`, `webp`, or `gif` report assets were present, and no screenshot capture was claimed. If the college report requires screenshots, add genuine screenshots from a manual browser walkthrough before submission. This is the only identified packaging blocker; it is not a software-test failure. |
