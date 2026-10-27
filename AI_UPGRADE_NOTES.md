# AI Practice upgrade — implementation and submission notes

This note maps the new code to the attached `novin report.pdf` and `Final Review Template (1).pdf`. The PDFs were used as reference material; they were not edited. Use the checklist below to update the report and presentation before submission.

## What changed in the application

1. **AI Practice Studio (`/practice`)** — a modern topic/length/difficulty builder with 8, 10, 12, 15, or 20 questions. The default is 10, so the old 3–4-question limit no longer defines the main practice experience.
2. **Fresh questions every session** — each generation creates a private `Quiz` row and a new set of questions. Recent prompts from the learner's last attempts on that topic are passed to the generator and skipped.
3. **Real AI provider support, without a hard dependency** — set `AI_API_KEY` to use any OpenAI-compatible Chat Completions model. The server validates the JSON response, then stores questions and explanations. With no key, the app uses `app/services/question_bank.py`, a local parameterized generator. The UI states which mode is active; the offline mode is explicitly **not** called a large language model.
4. **Adaptive difficulty** — mastery below 40% selects foundation questions, 40–69% selects core, and 70%+ selects stretch. Learners can override this. This uses the existing EMA evidence; it does not invent a new learner model.
5. **Longer quiz experience** — a keyboard-friendly wizard with progress bar, question palette, skipped-answer warning, score ring, skill-gap chips, per-question explanations, correct answers, and the next recommended resource.
6. **Server-side integrity and privacy** — answers are never included in quiz HTML/API JSON, generated quizzes are private, each AI session can be submitted once, CSRF is enforced, and responses are marked `no-store`.
7. **Richer visual design** — gradient dashboard hero, AI hero, animated orb, stronger metric cards, AI practice cards, modern forms, result cards, and responsive mobile layouts.
8. **Schema compatibility** — `app/services/schema.py` adds new nullable/defaulted columns to existing SQLite/PostgreSQL databases. Fresh databases get them through `db.create_all()`.
9. **Tests** — the suite grew from 167 to 198 passing tests, including offline-generation validation, full workflow, privacy, one-time submission, live-provider parsing/fallback, unsupported-topic handling, and legacy-schema migration coverage.

## Exact claims that are still true

- The **seeded shared catalog** still has 7 topics, 21 resources, 7 classic quizzes, and 25 curated questions. This keeps the original audit reproducible.
- The **recommender algorithm** is still deterministic, explainable, and unchanged in its ranking formula.
- Mastery is still an EMA estimate from server-scored attempts, not a grade or a probability.
- No claim is made that AI quizzes improve learning outcomes. Freshness and adaptive difficulty are design improvements only.

## Report/PPT update checklist

### Abstract / Chapter 1 / PPT slides 4 and 11

Add one sentence:

> The system adds an AI Practice Studio that generates a private, server-validated set of 8–20 fresh Python questions per session, with optional live LLM generation and an always-available offline fallback.

Remove or qualify any blanket statement that the whole application is “algorithm-free” or requires “no LLM”. A correct statement is:

> The recommender remains deterministic and requires no LLM; live AI is optional and used only for question generation.

### Objectives / PPT slide 9

Add:

> To generate longer, non-repeating practice quizzes from stored mastery evidence while preserving server-side grading, explanations, and privacy.

### Scope / PPT slide 10

Change “7 topic quizzes” to:

> 7 short classic catalog quizzes plus learner-specific AI practice sessions of 8–20 questions.

Add that generated sessions are private and one-time.

### Proposed system / PPT slide 11

Add a small AI quiz flow:

```text
Learner mastery + topic + recent prompts
        ↓
AI quiz orchestrator (live LLM or offline generator)
        ↓
Strict validation: count, 4 options, one answer, explanation, uniqueness
        ↓
Private generated Quiz + Questions → wizard → server grading → EMA mastery
```

Keep the existing recommendation formula separate. Do not imply that the recommender itself became a neural model.

### Modules / PPT slides 13–15 and report Chapter 5

Add two module rows:

| Module | Responsibility |
| --- | --- |
| AI quiz service | Provider call, fallback, adaptive tier selection, recent-prompt avoidance, and strict validation |
| Offline question bank | Curated and parameterized Python questions with deterministic answers and explanations |

Mention that generated questions store `explanation`, `skill`, and `difficulty`.

### Screenshots / PPT slides 16–18 and report Appendix II

Replace or add screenshots for:

1. New dashboard hero and AI practice cards.
2. `/practice` studio with provider status and adaptive signal.
3. Quiz wizard progress and question palette.
4. Result page with score ring, skill gaps, explanations, and next resource.
5. Quiz history showing the `✧ AI · 10 Q` badge.

These screenshots are important because the old slides show the plain interface the user wanted improved.

### Testing / report Chapter 6

Update “167 passing tests” to **198 passing tests**. Add test categories: AI workflow, privacy, one-time submission, live provider parsing/fallback, offline generator validation, unsupported-topic handling, and legacy schema migration.

### Results / report Chapter 7

Add a short subsection titled “AI practice generation”:

- State that 20-question offline generation was validated for all 7 topics at all 3 difficulty tiers.
- State that two consecutive sessions generated zero prompt overlap in the automated workflow test.
- State that live provider failures are handled by fallback.
- Explicitly say these are **functional** checks, not evidence of improved learning.

### Conclusion / PPT slide 19

Add:

> The upgraded prototype combines explainable recommendation with fresh, adaptive practice, while keeping grading and learner evidence auditable.

### Future enhancement / PPT slide 20 and report Chapter 10

Good future items to list:

1. Instructor review/approval queue for LLM-generated questions and content moderation.
2. Per-skill mastery using stored `Question.skill` rather than only topic-level mastery.
3. Rate limiting, cost budgets, and caching for live AI providers.
4. Alembic migrations instead of the small built-in schema helper.
5. A consent-based pre-test / post-test / delayed retention study to evaluate learning impact.
6. Accessibility and browser walkthrough evidence for the new wizard.

## Improvements still needed beyond this upgrade

- **Content quality:** LLM questions should be reviewed before high-stakes use. Schema validation cannot guarantee pedagogical correctness.
- **Learning model:** mastery is still topic-level; skill-level mastery would use the new tags more effectively.
- **Evaluation:** the existing offline benchmark measures ranking, not learning. A real learner study is still missing.
- **Security/operations:** disable the demo account in production, use a long random `SECRET_KEY`, add rate limits, and monitor AI provider cost/latency.
- **Data migration:** use Alembic if this moves beyond a student prototype.
- **Documentation:** regenerate report figures and PPT screenshots from the new UI; do not submit old screenshots alongside new feature claims.

## Demo script for the upgraded app

1. `python seed.py` and start Flask.
2. Sign in and open the new dashboard hero.
3. Open `/practice`, show the offline/live provider status and adaptive signal.
4. Generate 12 Variables questions; show progress and question variety.
5. Submit a mixture of correct and wrong answers; show explanation, skill gaps, mastery, and next resource.
6. Generate another Variables set; show that the questions are fresh and recent prompts were skipped.
7. Open quiz history and the classic quick check to show both flows coexist.
8. Discuss the honesty boundary: fresh AI practice is implemented, but learning improvement is not experimentally proven.
