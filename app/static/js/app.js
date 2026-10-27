(() => {
  'use strict';

  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || '';

  async function post(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'Accept': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || data.error || `Request failed (${response.status}). Please refresh and try again.`);
    return data;
  }

  function markComplete(form) {
    const card = form.closest('[data-resource-card]');
    const button = form.querySelector('button');
    const feedback = form.querySelector('.form-feedback');
    const badge = card?.querySelector('[data-completed-badge]');
    button.disabled = true;
    if (feedback) { feedback.textContent = 'Saving…'; feedback.classList.remove('error'); }
    return post(form.action, {}).then(() => {
      button.textContent = 'Completed ✓';
      if (badge) badge.hidden = false;
      if (feedback) feedback.textContent = 'Saved. Your progress is now visible in your overview.';
    }).catch(error => {
      if (feedback) { feedback.textContent = error.message; feedback.classList.add('error'); }
      button.disabled = false;
    });
  }

  document.querySelectorAll('form[data-complete]').forEach(form => {
    form.addEventListener('submit', event => { event.preventDefault(); markComplete(form); });
  });

  // Progressive enhancement for server-rendered generation forms: the forms
  // still submit normally without JavaScript.
  document.querySelectorAll('form[data-generate-quiz]').forEach(form => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type="submit"]');
      const label = form.querySelector('[data-generate-label]');
      const status = form.querySelector('[data-generate-status]');
      if (label) label.textContent = 'Creating your set…';
      if (status) status.textContent = 'Generating fresh questions. This can take a moment with live AI.';
      if (button) {
        button.setAttribute('aria-busy', 'true');
        // The submit event has already begun; disabling now only prevents a
        // second accidental click while preserving the normal POST.
        button.disabled = true;
      }
    });
  });

  function initPracticeSignals() {
    const dataNode = document.getElementById('practice-topic-data');
    const select = document.querySelector('[data-topic-select]');
    if (!dataNode || !select) return;
    let topics = [];
    try { topics = JSON.parse(dataNode.textContent || '[]'); } catch (_) { return; }
    const ring = document.querySelector('[data-signal-ring]');
    const setText = (selector, value) => {
      const node = document.querySelector(selector);
      if (node) node.textContent = value;
    };
    const update = () => {
      const topic = topics.find(item => String(item.id) === String(select.value));
      if (!topic) return;
      const percent = Math.round(Number(topic.mastery || 0) * 100);
      setText('[data-signal-topic]', topic.name);
      setText('[data-signal-mastery]', `${percent}%`);
      setText('[data-signal-status]', topic.assessed ? 'Assessed' : 'Not assessed');
      setText('[data-signal-score]', topic.latest_score === null || topic.latest_score === undefined
        ? 'No attempt' : `${Math.round(topic.latest_score * 100)}%`);
      setText('[data-signal-level]', topic.suggested_difficulty
        ? topic.suggested_difficulty.charAt(0).toUpperCase() + topic.suggested_difficulty.slice(1) : '—');
      setText('[data-signal-reason]', topic.difficulty_reason || 'Adaptive difficulty uses your recorded mastery.');
      if (ring) ring.style.setProperty('--value', String(percent));
    };
    select.addEventListener('change', update);
    update();
  }
  initPracticeSignals();

  function initQuizWizard(form) {
    const steps = [...form.querySelectorAll('[data-question-step]')];
    if (steps.length < 2) return null;
    const total = steps.length;
    const progress = form.querySelector('[data-quiz-progress]');
    const palette = form.querySelector('[data-question-palette]');
    const controls = form.querySelector('[data-wizard-controls]');
    const prev = form.querySelector('[data-wizard-prev]');
    const next = form.querySelector('[data-wizard-next]');
    const wizardSubmit = form.querySelector('[data-wizard-submit]');
    const status = form.querySelector('.form-feedback');
    const paletteButtons = [...(palette?.querySelectorAll('[data-jump-question]') || [])];
    let current = 0;

    form.noValidate = true;
    form.classList.add('wizard-active');
    if (progress) progress.hidden = false;
    if (palette) palette.hidden = false;
    if (controls) controls.hidden = false;

    const answered = index => Boolean(steps[index].querySelector('input[type="radio"]:checked'));
    const setText = (selector, value) => {
      const node = form.querySelector(selector);
      if (node) node.textContent = value;
    };
    const updatePalette = () => {
      paletteButtons.forEach((button, index) => {
        button.classList.toggle('is-answered', answered(index));
        button.classList.toggle('is-current', index === current);
        if (index === current) button.setAttribute('aria-current', 'step');
        else button.removeAttribute('aria-current');
      });
    };
    const showStep = index => {
      current = Math.max(0, Math.min(total - 1, index));
      steps.forEach((step, stepIndex) => step.classList.toggle('is-active', stepIndex === current));
      const percent = Math.round(((current + 1) / total) * 100);
      setText('[data-progress-label]', `Question ${current + 1} of ${total}`);
      setText('[data-progress-percent]', `${percent}%`);
      const fill = form.querySelector('[data-progress-fill]');
      const track = form.querySelector('.progress-track');
      if (fill) fill.style.width = `${percent}%`;
      if (track) track.setAttribute('aria-valuenow', String(current + 1));
      if (prev) prev.disabled = current === 0;
      if (next) next.hidden = current === total - 1;
      if (wizardSubmit) wizardSubmit.hidden = current !== total - 1;
      setText('[data-wizard-hint]', current === total - 1
        ? 'Review your answers, then submit once.' : 'Choose the best answer');
      updatePalette();
    };

    prev?.addEventListener('click', () => showStep(current - 1));
    next?.addEventListener('click', () => showStep(current + 1));
    paletteButtons.forEach(button => button.addEventListener('click', () => {
      showStep(Number(button.dataset.jumpQuestion) - 1);
    }));
    form.querySelectorAll('input[type="radio"]').forEach(input => {
      input.addEventListener('change', () => {
        form.dataset.confirmPartial = '0';
        updatePalette();
      });
    });

    // First submit on an incomplete wizard asks the learner to review. A
    // deliberate second submit is allowed and omitted answers score as wrong.
    form.addEventListener('submit', event => {
      const missing = steps.findIndex((_, index) => !answered(index));
      if (missing >= 0 && form.dataset.confirmPartial !== '1') {
        event.preventDefault();
        event.stopImmediatePropagation();
        form.dataset.confirmPartial = '1';
        showStep(missing);
        if (status) {
          status.textContent = `Question ${missing + 1} is unanswered. Review it, or press Submit again to score it as incorrect.`;
          status.classList.add('error');
        }
      }
    }, true);
    showStep(0);
    return {showStep, status};
  }

  function renderAdaptation(panel, adaptation) {
    const target = panel.querySelector('[data-adaptation-summary]');
    if (!target || !adaptation) return;
    target.replaceChildren();
    const label = document.createElement('span');
    label.className = 'reason-label';
    label.textContent = 'HOW YOUR PATH ADAPTED';
    const text = document.createElement('p');
    const previousScore = adaptation.previous_score === null
      ? 'No previous attempt' : `${Math.round(adaptation.previous_score * 100)}% previous score`;
    const scoreChange = adaptation.score_change === null
      ? 'This establishes your first score.'
      : `${adaptation.score_change >= 0 ? '+' : ''}${Math.round(adaptation.score_change * 100)} percentage points versus your previous score.`;
    const masteryChange = `${adaptation.mastery_change >= 0 ? '+' : ''}${Math.round(adaptation.mastery_change * 100)} points of estimated mastery.`;
    const next = adaptation.next_primary ? `Next primary step: ${adaptation.next_primary.title}.` : 'No primary step is currently available.';
    text.textContent = `${previousScore}; latest score ${Math.round(adaptation.latest_score * 100)}%. ${scoreChange} ${masteryChange} ${adaptation.recommendations_changed ? 'Your recommended next steps changed.' : 'The recommendation queue stayed stable for now.'} ${next}`;
    target.append(label, text);
  }

  function renderFocusSkills(panel, feedback) {
    const target = panel.querySelector('[data-focus-skills]');
    if (!target) return;
    const skills = [...new Set((feedback || []).filter(item => !item.correct && item.skill)
      .map(item => item.skill))].slice(0, 6);
    target.replaceChildren();
    if (!skills.length) {
      target.hidden = false;
      const label = document.createElement('span');
      label.textContent = '✓ No skill gaps in this set';
      target.append(label);
      return;
    }
    target.hidden = false;
    const label = document.createElement('span');
    label.textContent = 'SKILLS TO REVIEW';
    target.append(label);
    skills.forEach(skill => {
      const chip = document.createElement('span');
      chip.textContent = skill;
      target.append(chip);
    });
  }

  function renderNextResource(panel, item) {
    const target = panel.querySelector('[data-next-resource]');
    if (!target) return;
    target.replaceChildren();
    if (!item) { target.hidden = true; return; }
    target.hidden = false;
    const label = document.createElement('span');
    label.className = 'reason-label';
    label.textContent = 'RECOMMENDED NEXT STEP';
    const heading = document.createElement('h3');
    const link = document.createElement('a');
    link.href = item.url || '#';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = item.title || 'Open resource';
    heading.append(link);
    const reason = document.createElement('p');
    reason.textContent = item.reason || item.explanation || 'Selected from your current learning signals.';
    target.append(label, heading, reason);
  }

  function renderFeedback(panel, result) {
    const percent = Math.round(Number(result.score || 0) * 100);
    const ring = panel.querySelector('[data-score-ring]');
    if (ring) ring.style.setProperty('--score', String(percent));
    const scorePercent = panel.querySelector('[data-score-percent]');
    if (scorePercent) scorePercent.textContent = `${percent}%`;
    const score = panel.querySelector('[data-score]');
    if (score) score.textContent = `${result.correct} of ${result.total} correct`;
    const mastery = panel.querySelector('[data-mastery]');
    if (mastery) mastery.textContent = `Estimated topic mastery: ${Math.round(Number(result.mastery) * 100)}%. Return to your overview to see your updated recommendations.`;
    renderAdaptation(panel, result.adaptation);
    renderFocusSkills(panel, result.feedback);
    renderNextResource(panel, result.primary_recommendation);
    const another = panel.querySelector('[data-another-quiz]');
    if (another && result.practice_url) another.href = result.practice_url;
    const details = panel.querySelector('[data-question-feedback]');
    if (!details) return;
    details.replaceChildren();
    (result.feedback || []).forEach((item, index) => {
      const section = document.createElement('div');
      section.className = `question-feedback${item.correct ? '' : ' is-wrong'}`;
      const title = document.createElement('strong');
      title.textContent = `${item.correct ? '✓' : '↗'} ${index + 1}. ${item.prompt || 'Question'}`;
      const explanation = document.createElement('p');
      explanation.textContent = item.explanation || `Correct answer: ${item.correct_answer || ''}`;
      section.append(title, explanation);
      if (!item.correct) {
        const answers = document.createElement('div');
        answers.className = 'feedback-answer';
        const yours = document.createElement('span');
        yours.textContent = `Your answer: ${item.answer || 'Unanswered'}`;
        const correct = document.createElement('span');
        correct.textContent = `Correct: ${item.correct_answer || ''}`;
        answers.append(yours, correct);
        section.append(answers);
      }
      details.append(section);
    });
  }

  document.querySelectorAll('form[data-quiz]').forEach(form => {
    const wizard = form.hasAttribute('data-quiz-wizard') ? initQuizWizard(form) : null;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const buttons = [...form.querySelectorAll('button[type="submit"]')];
      const status = form.querySelector('.form-feedback');
      const answers = {};
      new FormData(form).forEach((value, key) => { if (key.startsWith('q_')) answers[key.slice(2)] = value; });
      buttons.forEach(button => { button.disabled = true; });
      if (status) {
        status.textContent = 'Checking your answers…';
        status.classList.remove('error');
      }
      try {
        const result = await post(form.action, {answers});
        const shell = form.closest('.quiz-shell') || form.parentElement;
        const panel = shell.querySelector('.quiz-feedback');
        if (!panel) throw new Error('Result panel is unavailable. Please refresh the page.');
        renderFeedback(panel, result);
        form.hidden = true;
        const card = form.closest('.quiz-card');
        if (card) card.hidden = true;
        panel.hidden = false;
        panel.focus();
      } catch (error) {
        if (status) {
          status.textContent = error.message;
          status.classList.add('error');
        }
        buttons.forEach(button => { button.disabled = false; });
        if (wizard) wizard.showStep(0);
      }
    });
  });

  const search = document.querySelector('[data-library-search]');
  const grid = document.querySelector('[data-library-grid]');
  if (search && grid) {
    const cards = [...grid.querySelectorAll('[data-resource-card]')];
    const empty = document.querySelector('[data-search-empty]');
    const count = document.querySelector('[data-library-count]');
    const filter = () => {
      const needle = search.value.trim().toLowerCase();
      let visible = 0;
      cards.forEach(card => {
        const match = !needle || card.dataset.searchText.includes(needle);
        card.hidden = !match;
        if (match) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
      if (count) count.innerHTML = `<strong>${visible}</strong> resource${visible === 1 ? '' : 's'} in this view`;
    };
    search.addEventListener('input', filter);
  }
})();
