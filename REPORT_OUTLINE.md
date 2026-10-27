> **Upgrade note:** This document records the original pre-AI audit (7 classic quizzes, 25 curated questions, 167 tests). The application now also has the AI Practice Studio; see [`AI_UPGRADE_NOTES.md`](AI_UPGRADE_NOTES.md) for the exact report/PPT changes and the updated test count (198).

# Dynamic Learning Project Report Outline

**Working title:** Dynamic Learning — Personalized Learning-Resource Recommendation System Using Learner Progress and Adaptive Revision

**Template followed:** Supplied senior report, `FOOD ALLERGEN DETECTION AND SAFE MEALS`, 60 pages. The report will preserve its academic sequence: front matter, Chapters 1–10, appendices, and references.

## Report principles

- Describe the existing Flask/SQLAlchemy application; do not redesign or claim unimplemented features.
- Treat the project as a local academic prototype, not as a production learning platform.
- Call mastery a topic-level estimate derived from quiz evidence, not a grade or verified knowledge probability.
- Identify the offline comparison as synthetic benchmark evidence only.
- Do not claim adaptive-method superiority, educational improvement, validated forgetting detection, novelty, or reproduction of the supplied base paper.
- Use placeholders only for submission information that has not yet been supplied.
- Use genuine Dynamic Learning screenshots only. The senior report's food-allergen screenshots must not be reused.

## Front matter

### Title page

- Project title: Dynamic Learning — Personalized Learning-Resource Recommendation System Using Learner Progress and Adaptive Revision
- Submitted by: `[student full name] ([register number])`
- Degree: Bachelor of Engineering
- Department: `[department]`
- Institution: `[college/institution]`
- University: `[university]`
- Academic year/submission date: `[academic year or date]`

### Bonafide certificate

Follow the senior report's layout, but populate it only after receiving the student's institution, guide/supervisor, HOD, and other required signatory details. No signatures will be fabricated.

### Acknowledgement

Prepare a neutral project acknowledgement with placeholders for the institution, principal, HOD, guide, department staff, family, and friends. Replace or remove any paragraph that does not match the student's required institutional format.

### Abstract

Explain that the project is a lightweight, explainable Flask web application that uses server-scored quiz attempts, topic mastery estimates, prerequisites, resource completion, and revision timing to recommend a next learning resource. Mention the seven-topic Python catalog, working foundation quizzes, human-readable reasons, and local SQLite-backed persistence. State that the evaluation comparison is synthetic and does not establish educational improvement or recommender superiority.

### Table of contents

Use the senior report's chapter order and numbered headings. Page numbers must be generated after pagination, not typed from the outline.

### List of figures

Planned figures:

| Figure | Description |
| --- | --- |
| 4.1 | Proposed system architecture |
| 4.2 | Learner workflow and recommendation loop |
| 4.3 | Use case diagram |
| 4.4 | Class/data model diagram |
| 4.5 | Activity diagram for quiz submission and adaptation |
| 4.6 | Sequence diagram for recommendation generation |
| 7.1 | Synthetic offline benchmark comparison |

### List of tables

Planned tables:

| Table | Description |
| --- | --- |
| 3.1 | Functional requirements |
| 3.2 | Non-functional requirements |
| 5.1 | Project modules and responsibilities |
| 6.1 | Representative test case design |
| 7.1 | Synthetic offline benchmark results |
| 7.2 | Learning-rate sensitivity check |

## Chapter 1 — Introduction

### 1.1 Objective

- Build a secure learner account and progress dashboard.
- Provide a seven-topic Python learning path: Variables, Data Types, Conditionals, Loops, Functions, Lists, and Basic Algorithms.
- Provide working quizzes for Variables, Conditionals, Loops, and Functions.
- Calculate topic-wise mastery from server-scored quiz attempts.
- Record quiz history, question responses, and resource completion.
- Recommend resources with a deterministic human-readable explanation.
- Compare the adaptive ranker with stable-catalog and content-based baselines without inventing learner outcomes.

### 1.2 Scope

Cover authentication, dashboard, topic mastery, learning library, quizzes, completion tracking, prerequisites, explainable recommendations, admin-only evaluation, and local persistence. Explicitly exclude production content hosting, collaborative filtering, real learner studies, validated psychological thresholds, and browser/production claims not tested by the audit.

## Chapter 2 — Literature Survey

Use the verified literature map from `PROJECT_GUIDE.md`:

1. Brusilovsky and Millán (2007), adaptive hypermedia and user models.
2. Manouselis, Drachsler, Verbert, and Duval (2013), recommender systems for learning.
3. Piech et al. (2015), Deep Knowledge Tracing.
4. Settles and Meeder (2016), trainable spaced repetition.
5. You, Xu, and Wu (2026), MFF-CF.

For each work, distinguish identity/approach verification from full-text limitation evidence. Explain that the project is motivated by the question of making learner evidence, prerequisites, completion/revision rules, and recommendation reasons inspectable in a small local flow. Do not present this scoped implementation question as a proven research gap or novelty claim. State clearly that Dynamic Learning is not a reproduction of MFF-CF and does not implement collaborative filtering.

## Chapter 3 — Analysis

### 3.1 System analysis

#### 3.1.1 Problem identification

Discuss generic or static learning-resource lists that do not identify a learner's topic-specific difficulty, may ignore prerequisites, and may not expose why a resource was selected. Explain the need for a small auditable system that adapts after new quiz evidence.

#### 3.1.2 Existing system

Describe static catalogs, manual resource selection, aggregate-only progress views, and opaque or data-hungry recommendation approaches as context. Avoid attributing unsupported limitations to named papers.

#### 3.1.3 Proposed system

Describe the Flask application, server-scored quizzes, persisted history, EMA mastery, prerequisite-aware filtering, completion/revision policy, deterministic scoring, and recommendation explanations. Include advantages and boundaries.

### 3.2 Requirement analysis

#### 3.2.1 Functional requirements

Include registration/login, session-bound access, dashboard, catalog browsing/filtering, topic quizzes, server-side grading, feedback, mastery/history, completion, prerequisite handling, recommendations, evaluation, and CSRF-protected writes.

#### 3.2.2 Non-functional requirements

Include explainability, reproducibility, correctness, security, maintainability, accessibility, responsive behavior, persistence, and local resource requirements. Mark availability, scalability, and load performance as design considerations rather than certified production results.

#### 3.2.3 Hardware specification

Use a conservative local-development profile: modern dual-core processor or better, 4 GB RAM minimum, sufficient disk for Python environment and SQLite database, keyboard/display, and network access for external learning links. Label these as practical development requirements, not measured deployment limits.

#### 3.2.4 Software specification

Python, Flask, Flask-SQLAlchemy, SQLAlchemy, Flask-WTF, WTForms, SQLite for local development, HTML/Jinja templates, CSS, vanilla JavaScript, pytest, and a modern browser. Include the project commands from `README.md` without embedding credentials.

## Chapter 4 — Design

### 4.1 Overall design

Present the browser–Flask routes–domain services–SQLAlchemy–SQLite/PostgreSQL architecture. Explain the separation of authentication, dashboard, learning, and evaluation routes from mastery, recommendation, catalog, metrics, and offline-evaluation services.

### 4.2 UML diagrams

#### 4.2.1 Work flow diagram

Registration/login → cold-start dashboard → resource/quiz interaction → server scoring → mastery update → recommendation filtering/ranking → explanation and history display → later completion/revision.

#### 4.2.2 Use case diagram

Actors: Learner, Administrator, and External learning-resource website. Use cases: register, sign in, view dashboard, browse/filter library, take quiz, view feedback/history, complete resource, view recommendations, and view offline evaluation as administrator.

#### 4.2.3 Class/data model diagram

Use the implemented entities: User, Topic, Resource, Quiz, Question, QuizAttempt, QuestionResponse, ResourceCompletion, MasteryScore, Prerequisite, and ResourceInteraction. Show the relationships documented in `README.md`.

#### 4.2.4 Activity diagram

Model quiz loading, answer submission, validation, exact-option grading, atomic attempt/response/mastery update, and refreshed recommendation state.

#### 4.2.5 Sequence diagram

Show browser → learning route/API → validation/CSRF → quiz service and database → mastery service → recommender → JSON/HTML response.

## Chapter 5 — Implementation

### 5.1 Modules

1. Authentication and access-control module.
2. Catalog and learning-library module.
3. Quiz and server-side scoring module.
4. Mastery and learner-history module.
5. Recommendation module.
6. Resource completion and revision module.
7. Evaluation and baseline-comparison module.
8. Responsive learner interface module.

### 5.2 Module description

Explain each module using actual routes, models, services, and templates. Include the core formulas:

```text
new_mastery = old_mastery + 0.35 × (quiz_score − old_mastery)
priority = 50 + 35 × (1 − mastery) − 3 × difficulty − 20 × unmet_prerequisite_count
```

Explain that recent completions are filtered, resources completed at least 14 days earlier may return for revision, and tie-breaking is deterministic. State that the 65% weak-topic threshold, 14-day window, and 0.35 learning rate are transparent prototype constants, not validated settings.

## Chapter 6 — Testing

### 6.1 Testing and validation

Report actual verification only:

- Strict pytest suite: 167 passed with warnings treated as errors.
- Python compilation passed.
- JavaScript syntax check passed.
- Fresh dependency installation and `pip check` passed.
- Security checks covered authentication, authorization, CSRF, malformed input, sessions, production safeguards, and reset guards.
- HTTP workflow covered seed, login, quiz attempts, completion, persistence, logout, new-user isolation, and isolated reset.
- Offline evaluation arithmetic, candidate pool/K consistency, future-event exclusion, labels, coverage, and runtime calculation were checked.

State that no browser rendering engine was used in the final audit; visual layout, responsive behavior, keyboard behavior, and JavaScript click execution still require a manual browser walkthrough.

### 6.2 Build the test plan

Use representative cases rather than claiming every feature is a production guarantee:

| ID | Scenario | Expected result |
| --- | --- | --- |
| TC001 | Register with valid details | Account is created and session access works |
| TC002 | Login with valid credentials | Learner reaches dashboard |
| TC003 | Missing/invalid CSRF | Write is rejected |
| TC004 | Submit exact quiz options | Server returns score and feedback |
| TC005 | Submit malformed/unknown answer payload | Request is rejected safely |
| TC006 | Quiz updates mastery | Attempt, responses, and mastery commit together |
| TC007 | Complete a resource twice | One unique completion remains and badge persists |
| TC008 | Revisit recent completion | Resource is filtered from immediate queue |
| TC009 | Anonymous/learner evaluation access | Anonymous gets 401; learner gets 403; admin gets 200 |
| TC010 | Rerun normal seed | Learner records are preserved |
| TC011 | Explicit development reset | Isolated SQLite state is cleared and catalog is reseeded |
| TC012 | Offline metric arithmetic | Precision@5, Recall@5, NDCG@5, coverage, and runtime calculations match definitions |

## Chapter 7 — Result and Discussion

Discuss successful functional operation without overstating learning effectiveness. Include:

### 7.1 Application results

- Seven topics, 21 resources, seven quizzes, and 25 questions are seeded.
- Variables, Conditionals, Loops, and Functions have working multi-question quizzes.
- A clean workflow recorded quiz scores, mastery changes, recommendation explanations, completion filtering, and disk persistence.
- The local prototype passed the strict automated and HTTP checks listed in Chapter 6.

### 7.2 Synthetic benchmark results

Report the regenerated four-case, K=5 benchmark as synthetic ranking evidence:

| Method | Precision@5 | Recall@5 | NDCG@5 | Coverage |
| --- | ---: | ---: | ---: | ---: |
| Adaptive | 0.050000 | 0.250000 | 0.250000 | 0.285714 (6/21) |
| Stable catalog baseline | 0.150000 | 0.500000 | 0.375316 | 0.238095 (5/21) |
| Content-based baseline | 0.250000 | 1.000000 | 1.000000 | 0.571429 (12/21) |

Explain that the adaptive ranker performs below both baselines on these synthetic aggregate metrics. Note one hand-built case per scenario, authored labels and content-feature overlap, scenario/topic confounding, K larger than the relevant set in some cases, and absence of independent annotators or real learners. Do not call this a failure of the whole application; it is a limitation of this benchmark and a useful audit result.

### 7.3 Learning-rate sensitivity

Include alpha values 0.20, 0.35, 0.50, and 0.80 with the documented three-score estimate results and queue IDs, clearly labelled as formula/manual-state sensitivity rather than tuning or learning evidence.

## Chapter 8 — User Manual

Provide setup and usage steps:

1. Create/activate a Python virtual environment.
2. Install `requirements.txt`.
3. Set process environment variables, including a strong `SECRET_KEY` where appropriate.
4. Run `python seed.py`.
5. Start Flask with `flask --app run.py run --debug` for local development.
6. Register at `/register` and sign in.
7. Explore the dashboard and library.
8. Take a foundation quiz and inspect score, feedback, mastery, and recommendation reasons.
9. Mark a learning resource complete and refresh the library/dashboard.
10. Use `/evaluation` only with a separately managed local administrator account.
11. Use `python seed.py --reset` only for disposable development/test SQLite data after checking the warning.

Include a troubleshooting subsection for missing seed data, expired sessions, CSRF failures, missing templates, and evaluation permissions. Do not publish passwords or private environment values.

## Chapter 9 — Conclusion

Conclude that the project delivers a working, local, explainable recommender prototype with persisted learner evidence, topic mastery estimates, prerequisite-aware ranking, completion/revision policy, and reproducible tests. State that the implementation demonstrates functionality and auditability, not verified learning improvement, production readiness, novel research superiority, or accurate forgetting prediction.

## Chapter 10 — Future Enhancement

Use the documented next steps:

- Collect anonymized interaction data with consent and ethics approval.
- Add independently reviewed, held-out chronological relevance labels.
- Expand the benchmark with repeated and balanced scenarios across topics.
- Compare with collaborative filtering only when suitable interaction data is available.
- Validate thresholds and revision timing using pre-test, post-test, and delayed retention measures.
- Add instructor tools for editing resources, questions, and prerequisites.
- Add migrations, deployment observability, stronger operational controls, and broader browser/accessibility testing.

## Appendices

### Appendix 1 — Base paper

Insert the supplied base-paper material only if the user owns or is permitted to include it. Otherwise include the citation, metadata, and a short relation-to-project note. Do not present the Dynamic Learning implementation as MFF-CF reproduction.

### Appendix 2 — Screenshots

Reserve pages for genuine screenshots from a manual walkthrough: registration/login, cold-start dashboard, topic mastery/history, library, quiz, quiz feedback/adaptation, completion state, and admin evaluation. Screenshots must be captured from Dynamic Learning and labelled with figure numbers/captions.

### Appendix 3 — Internship certificate

Include only if the user supplies the certificate and confirms it is required. Never create or imitate a certificate.

## References

Use the verified references and links from `PROJECT_GUIDE.md`, with consistent IEEE-style formatting. Include the application/project documentation as implementation sources where appropriate. Keep verification notes concise and preserve the distinction between metadata-verified identity and unverified full-text limitation claims.
