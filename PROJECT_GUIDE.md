# Seventh-Semester Project Guide

## Project title

**Dynamic Learning-Resource Recommender Using Learner Progress and Adaptive Revision**

## Abstract

This project presents a lightweight and explainable working-software academic prototype that recommends the next learning resource for a student using topic-level quiz performance, previous attempts, prerequisite knowledge, resource completion, and revision timing. It includes a seven-topic Python learning path, server-side quiz scoring, topic mastery estimates, weak-topic detection, learning history, and recommendation explanations.

The prototype addresses a practical gap in personalized learning systems: a recommendation can be useful only when a learner can understand why it was selected and when the recommendation changes after new evidence is recorded. The implementation therefore uses a deterministic Python scoring algorithm rather than a paid API, cloud model, GPU, or opaque machine-learning service.

## Relation to the base paper

The project is motivated by the following paper supplied for this project:

> Hongnan You, Lijun Xu, and Dongping Wu, “MFF-CF: A Multi-Feature Fused Collaborative Filtering Framework for Personalized Learning Resource Recommendation in Smart Education,” *Discover Artificial Intelligence*, 2026. DOI: https://doi.org/10.1007/s44163-026-01715-0. Full paper: https://link.springer.com/article/10.1007/s44163-026-01715-0

This implementation is **not a reproduction of MFF-CF** and does not implement collaborative filtering. Crossref metadata confirms the supplied title, authors, journal, DOI, and online date of 21 August 2026 (volume 6, article 860). The full Springer article could not be read during the audit because the publisher returned a client challenge. Its alleged limitations and the claimed research gap remain unverified; metadata alone does not establish them.

## Short related-work map and investigated gap

These works motivate questions, not a novelty claim. Publication identity and full-text support are separate checks. Earlier text called interpretive scope mappings “documented limitations”; that attribution was not substantiated and is corrected below. No systematic literature review or comparative reproduction was performed.

| Relevant work and verification source | Verified approach/scope | Limitation evidence status | Question investigated here |
| --- | --- | --- | --- |
| Brusilovsky & Millán (2007), “User Models for Adaptive Hypermedia and Adaptive Educational Systems,” *The Adaptive Web*, pp. 3–53. [DOI](https://doi.org/10.1007/978-3-540-72079-9_1) | Chapter identity/authors/pages verified by DOI/Crossref; parent volume year 2007 verified at [volume DOI](https://doi.org/10.1007/978-3-540-72079-9). | Springer full text blocked. Earlier cold-start/sparse-evidence limitation attribution was not verified against a passage. | Can a small local application show an inspectable estimate and distinguish unassessed from weak? |
| Manouselis, Drachsler, Verbert & Duval (2013), *Recommender Systems for Learning*, SpringerBriefs. [DOI](https://doi.org/10.1007/978-1-4614-4361-2) | Title/authors and 2013 print year verified by Crossref; online metadata was created in 2012. This is a book, not the different 2011 TEL chapter. | Full text blocked. The earlier list of privacy/cold-start/interoperability limitations was not passage-verified. | Can a reproducible small-catalog demonstration work without collaborative interaction data? |
| Piech, Bassen, Huang, Ganguli, Sahami, Guibas & Sohl-Dickstein (2015), “Deep Knowledge Tracing,” *NIPS 28*. [Proceedings](https://papers.nips.cc/paper/5654-deep-knowledge-tracing) | Proceedings abstract verifies recurrent neural networks for modeling student interactions and predictive evaluation on real student data. | Removed the unsupported “less interpretable” attribution: the abstract explicitly claims straightforward interpretation/discovery of curriculum structure. This audit did not compare interpretability. | Can an explicit EMA and a resource reason be explained in this local prototype? |
| Settles & Meeder (2016), “A Trainable Spaced Repetition Model for Language Learning,” *ACL*, pp. 1848–1858. [ACL record](https://aclanthology.org/P16-1174/), [DOI](https://doi.org/10.18653/v1/P16-1174) | Title/authors/venue/year/pages verified by ACL and Crossref. Language-learning spaced repetition is the stated scope. | The PDF endpoint returned raw binary rather than readable text. Detailed model limitations/transfer claims were not verified; do not attribute them to the authors. | Can a conservative revision policy be presented without claiming to detect forgetting? |
| You, Xu & Wu (2026), “MFF-CF: a multi-feature fused collaborative filtering framework for personalized learning resource recommendation in smart education,” *Discover Artificial Intelligence* 6, 860. [Crossref record](https://api.crossref.org/works/10.1007/s44163-026-01715-0) | Identity, publication date, and collaborative-filtering framing confirmed by metadata. | Full text blocked. GPU needs, compute burden, inability to identify weak topics, and lack of revision/prerequisite modeling are **unverified hypotheses**, not established limitations of this paper. | Investigate the behavior of this lightweight prototype, without claiming superiority to or reproduction of MFF-CF. |

The scoped gap is therefore an implementation and evaluation question: how to make topic-level evidence, explicit prerequisites, completion/revision rules, and recommendation explanations visible and reproducible for a small local learner flow when collaborative data is unavailable. It is not a claim that prior work lacks these ideas, and no novelty or educational-outcome claim is made.

### Reference-audit note

Audit date: 12 October 2026. Four identity records were verified using DOI/Crossref/ACL and the fifth via NeurIPS proceedings. Only the DKT abstract was substantively readable among the research summaries used here. Publisher access challenges, rate limits, and unreadable PDF extraction are verification limits, not evidence that a paper lacks a capability. Obtain readable full texts and passage-level citations before presenting the proposed gap as a literature finding.

## Problem statement

Many learning-resource systems recommend content without identifying the exact topic a learner is struggling with. A student may also be directed to an advanced resource before prerequisite concepts are understood, while revision needs can be hidden by a single aggregate score. This project uses persisted learner evidence to produce topic-sensitive, prerequisite-aware, and revision-aware recommendations.

## Limitations investigated and implemented response

| Existing limitation to investigate | Implemented response in this project |
| --- | --- |
| Difficulty identifying specific weak topics | Topic-wise attempts are stored; assessed topics below the code constant of 65% are listed as weak. This is a prototype threshold, not a validated cut point. |
| Revision needs may be overlooked | Attempts influence EMA; low latest scores have explanations. Completed resources become eligible again after the 14-day code constant. There is no validated forgetting model or separate repeated-mistake/decline detector in the current ranker. |
| Prerequisite knowledge may be missing | `Prerequisite` records explicitly connect topics, and unmet prerequisite mastery reduces a resource priority and appears in its explanation. |
| Advanced models may require high computing resources | The recommender is deterministic, database-backed, explainable, and runs locally with SQLite and Flask. Live LLM use is optional and limited to quiz generation; a validated offline generator keeps the app usable with no GPU, cloud service, or API key. |

## Main objective

To improve personalized learning recommendations by considering the student's actual learning progress, knowledge gaps, prerequisite readiness, and revision needs.

## Specific objectives

1. Build a secure learner account and progress dashboard.
2. Provide a structured Python learning path with Variables, Data Types, Conditionals, Loops, Functions, Lists, and Basic Algorithms.
3. Provide short classic quizzes plus an AI Practice Studio that generates longer fresh question sets on every attempt.
4. Calculate and display topic-wise mastery from server-scored quiz attempts.
5. Record quiz history, question responses, skill-level feedback, and resource completion.
6. Recommend resources with a human-readable explanation and priority score.
7. Evaluate the adaptive approach against both a content-based baseline and a stable-catalog baseline without inventing results.
8. Keep AI-generated content private, server-graded, validated, and honest about whether a live LLM or the offline generator produced it.

## Demonstration flow for a guide review

1. Run `python seed.py` and start the Flask server.
2. Open `/register` and create a learner account. For a disposable local walkthrough only, the seeded demonstration account in `README.md` can be used; its published password and administrator role are development-only and must not be used for deployment.
3. Open the dashboard. Show the cold-start state: seven topic rows, unassessed mastery, weak-topic onboarding, resources, and explainable recommendations.
4. Open `/practice` and generate a 12-question Variables set. Point out the current mastery signal, the chosen adaptive difficulty, the provider status, and the wizard progress bar.
5. Intentionally submit some incorrect answers. Show the score ring, skills to review, per-question explanations, exact correct answers, and the updated Variables mastery.
6. Return to the dashboard. Show that Variables appears as a weak topic, the AI session has a history badge, and recommendation explanations mention the low recent score.
7. Complete a beginner resource in the library. Show the resource completion count and that the recently completed resource is removed from the immediate queue.
8. Generate a second Variables set from the dashboard. Show that the prompts are different, recent prompts were skipped, and the quiz is longer than the original quick check. Submit it and compare the mastery and recommendation changes.
9. Open the original “Classic quick check” to show that the short seeded quiz still works, then open the topic-wise mastery and quiz history tables to explain the learner model.
10. If required, sign in with a separately created local administrator (or the development-only `demo@example.com` account) and open `/evaluation` to discuss baseline metrics and the limitations of the current evidence.

## Algorithm in presentation language

For each topic, the system keeps quiz attempts as the evidence history. A topic mastery value is an estimate derived from that evidence, not ground-truth knowledge, a grade, or a validated probability of future success. The latest evidence has more influence without deleting historical evidence. The persisted mastery update uses an exponential moving average:

```text
new_mastery = old_mastery + 0.35 * (quiz_score - old_mastery)
```

`0.35` is a transparent starting heuristic: it gives the newest score a visible 35% weight while retaining 65% of the prior estimate. It is intentionally easy to audit and reproduce, not learned or validated as an optimal rate. Sparse, noisy, or unrepresentative quiz evidence can make the estimate wrong, which is why the interface and discussion should call it an estimate.

### Learning-rate sensitivity procedure

Hold the seeded catalog, initial estimate (`0.0`), prerequisite data, and completion state constant. The audit test applies `[0.8, 0.8, 0.8]` using the manual, no-attempt-row branch of `update_mastery` for each rate and records recommendation IDs. The implementation rounds **every update to four decimals**, not just display. The live attempt-replay path remains fixed at 0.35; the custom rate argument is not a global setting. Thus this is a formula/manual-state sensitivity check, not a live learner study or a tuned model. See `tests/test_submission_audit.py` for the executable checks and `SUBMISSION_AUDIT.md` for observed ranks.

| Rate | New-score weight | Estimate after 1 / 3 scores | How recommendations can change |
| ---: | ---: | ---: | --- |
| 0.20 | 20% | 0.1600 / 0.3904 | Slow adaptation can keep the topic in the weak-topic queue longer after improvement. |
| 0.35 | 35% | 0.2800 / 0.5803 | Transparent starting point; other ranking rules may still keep the same primary resource. |
| 0.50 | 50% | 0.4000 / 0.7000 | A few good scores can move the topic past a threshold and let another topic lead. |
| 0.80 | 80% | 0.6400 / 0.7936 | Fast adaptation can reorder recommendations after one score, but is more sensitive to noise. |

These are sensitivity results, not a selection experiment and not evidence that one rate improves learning. Prerequisite penalties, resource difficulty, recent completion suppression, and stable ID tie-breaking can outweigh the mastery change, so the observed queue must be reported alongside the numeric estimate. The operational replay instructions also appear in `README.md`.

The recommendation score then combines:

- low topic mastery;
- low or recent quiz performance;
- resource difficulty;
- unmet prerequisite mastery;
- resource completion and revision age;
- stable resource ordering as a deterministic tie-breaker.

The system attaches reasons such as:

- “Your current Loops mastery is 42%.”
- “Your recent Functions quiz score was low (50%).”
- “Study Variables first because it is a prerequisite.”
- “It has been a while since you completed this resource; revision is due.”

These are rule-based explanations derived from stored records. They are not a claim that the system predicts forgetting accurately; that claim requires a validated learner study.

## System modules

| Module | Responsibility |
| --- | --- |
| Flask routes | Authentication, dashboard, AI practice studio, quiz generation, library, completion, and evaluation endpoints |
| SQLAlchemy models | Users, topics, prerequisites, resources, shared/generated quizzes, questions with explanations and skill tags, attempts, responses, mastery, and interactions |
| AI quiz service | Optional live LLM call, strict JSON/schema validation, adaptive difficulty, recent-prompt avoidance, and offline fallback |
| Offline question bank | Curated plus parameterized Python code-tracing questions with deterministic answers and teaching explanations |
| Mastery service | Topic mastery and recent-attempt weighting |
| Recommender service | Candidate filtering, prerequisite checks, scoring, revision rules, and explanations |
| Metrics/evaluation services | Progress summary, quiz history, weak topics, multi-scenario offline evaluation, baselines, and Precision@K/Recall@K/NDCG@K helpers |
| Catalog service | Reproducible Python topics, resources, quiz questions, and answer explanations |
| Jinja/CSS/JavaScript UI | Responsive dashboard, learning library, quiz flow, accessible feedback, and completion actions |

## Scope and limitations

- The catalog is seeded educational demonstration data, not a production content marketplace.
- External resource URLs may change or become unavailable; the URLs are not hosted by this application.
- The current recommender is content- and learner-signal-based. It does not use collaborative filtering or claim the results of the base paper.
- Ranking metrics require held-out relevance labels. The application deliberately reports `null` for Precision@5, Recall@5, and NDCG@5 when such labels are absent.
- The 65% mastery threshold and 14-day revision window are code constants, not validated psychological thresholds.
- Live LLM questions are schema-validated but not semantically guaranteed; a production deployment should add instructor review, content moderation, and a curated-question approval queue.
- The offline generator is a deterministic template engine, not a language model. It is labelled honestly in the UI and supports the seven seeded Python topics.
- Fresh questions and adaptive difficulty are learning-design improvements, not proof of better learning outcomes.
- A future learner study should use consent, a pre-test, an intervention, a post-test, and a delayed retention test before making learning-outcome claims.

## Suggested future work

1. Collect anonymized interaction data with ethics approval.
2. Add held-out chronological relevance labels for evaluation.
3. Compare the rule-based method with the included stable and content-based baselines, then add a collaborative baseline only when suitable interaction data is available.
4. Validate thresholds and revision timing using delayed post-tests rather than clicks alone.
5. Add instructor tools for reviewing AI-generated questions and editing prerequisites, questions, and resources.
6. Move from topic-level mastery to skill-level mastery using the stored `Question.skill` values, then validate difficulty calibration with real learner data.
7. Add rate limiting and cost controls for live AI generation, and replace the small schema helper with Alembic migrations for larger deployments.
