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

  document.querySelectorAll('form[data-quiz]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const button = form.querySelector('button[type="submit"]');
      const status = form.querySelector('.form-feedback');
      const answers = {};
      new FormData(form).forEach((value, key) => { if (key.startsWith('q_')) answers[key.slice(2)] = value; });
      button.disabled = true;
      status.textContent = 'Checking your answers…';
      status.classList.remove('error');
      try {
        const result = await post(form.action, {answers});
        const panel = form.parentElement.querySelector('.quiz-feedback');
        panel.querySelector('[data-score]').textContent = `${result.correct} of ${result.total} correct`;
        panel.querySelector('[data-mastery]').textContent = `Estimated topic mastery: ${Math.round(Number(result.mastery) * 100)}%. Return to your overview to see your updated recommendations.`;
        const adaptation = result.adaptation;
        if (adaptation) {
          const summary = document.createElement('div');
          summary.className = 'recommendation-reason adaptation-summary';
          const label = document.createElement('span');
          label.className = 'reason-label';
          label.textContent = 'HOW YOUR PATH ADAPTED';
          const text = document.createElement('p');
          const previousScore = adaptation.previous_score === null ? 'No previous attempt' : `${Math.round(adaptation.previous_score * 100)}% previous score`;
          const scoreChange = adaptation.score_change === null ? 'This establishes your first score.' : `${adaptation.score_change >= 0 ? '+' : ''}${Math.round(adaptation.score_change * 100)} points versus your previous score.`;
          const masteryChange = `${adaptation.mastery_change >= 0 ? '+' : ''}${Math.round(adaptation.mastery_change * 100)} points of estimated mastery.`;
          const next = adaptation.next_primary ? `Next primary step: ${adaptation.next_primary.title}.` : 'No primary step is currently available.';
          text.textContent = `${previousScore}; latest score ${Math.round(adaptation.latest_score * 100)}%. ${scoreChange} ${masteryChange} ${adaptation.recommendations_changed ? 'Your recommended next steps changed.' : 'The recommendation queue stayed stable for now.'} ${next}`;
          summary.append(label, text);
          const old = panel.querySelector('.adaptation-summary');
          if (old) old.replaceWith(summary); else panel.insertBefore(summary, panel.querySelector('[data-question-feedback]'));
        }
        const details = panel.querySelector('[data-question-feedback]');
        details.replaceChildren();
        (result.feedback || []).forEach(item => {
          const section = document.createElement('div');
          section.className = 'question-feedback';
          const title = document.createElement('strong');
          title.textContent = `${item.correct ? '✓' : '↗'} ${item.prompt || 'Question'}`;
          const explanation = document.createElement('p');
          explanation.textContent = item.explanation || `Correct answer: ${item.answer || item.correct_answer || ''}`;
          section.append(title, explanation);
          details.append(section);
        });
        form.hidden = true;
        panel.hidden = false;
        panel.focus();
      } catch (error) {
        status.textContent = error.message;
        status.classList.add('error');
        button.disabled = false;
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
