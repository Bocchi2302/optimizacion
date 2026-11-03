/* Método de las Dos Fases · interacción del formulario y de los resultados.
   Sin bibliotecas remotas. El servidor calcula y escapa el informe (Jinja); aquí
   solo se arma el formulario, se valida de forma preliminar, se muestra la vista
   previa y se maneja el recorrido guiado. El texto del usuario nunca se inserta
   como HTML: se usa textContent. */
(() => {
  'use strict';
  const root = document.querySelector('main[data-api-url]');
  const endpoints = {resolve: root.dataset.apiUrl, report: root.dataset.reportUrl};
  const byId = id => document.getElementById(id);
  const examples = JSON.parse(byId('df-examples').textContent);
  const exampleNames = {profesora: 'EJEMPLO DE LA PROFESORA', minimo: 'COSTO DE SERVICIOS', infactible: 'CASO INFACTIBLE', no_acotado: 'CASO NO ACOTADO'};
  let n = 2, constraints = [], lastPayload = null, lastKey = '', busy = false, lastResult = null, loadedExample = 'profesora', exampleKey = '';
  const guided = {slides: [], index: 0, opener: null};

  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const minus = s => String(s).replace(/(^|[^\w)])-(?=[\d(])/g, '$1−');
  // x con subíndice construido con nodos (sin innerHTML).
  function varNode(j) { const s = el('span', 'x', 'df-var'); s.append(el('sub', String(j + 1))); return s; }
  function field(labelText, value, id, {maxLength = 160, placeholder = ''} = {}) {
    const wrap = el('div', undefined, 'df-field');
    const label = el('label', labelText); label.htmlFor = id;
    const input = el('input'); input.type = 'text'; input.id = id; input.maxLength = maxLength; input.value = value ?? ''; input.placeholder = placeholder;
    wrap.append(label, input); return wrap;
  }
  function coefInput(id, value, aria) {
    const input = el('input', undefined, 'df-coef'); input.type = 'text'; input.id = id; input.maxLength = 40; input.value = value ?? '0';
    input.inputMode = 'text'; input.autocomplete = 'off'; input.spellcheck = false; input.setAttribute('aria-label', aria); return input;
  }

  // ---------- Validación preliminar (el servidor sigue siendo la autoridad) ----------
  const NUM = /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d{1,2})?$|^[+-]?\d+\/[+-]?\d+$/;
  function checkNumber(text) {
    const t = String(text).trim();
    if (!t || t.length > 40 || !NUM.test(t)) return 'Número inválido. Usa, por ejemplo, 2, 0.5 o 1/3.';
    if (t.includes('/') && Number(t.split('/')[1]) === 0) return 'Fracción inválida: el denominador no puede ser 0.';
    return null;
  }
  function validateLocal(m) {
    const problems = [];
    m.objective.forEach((v, j) => { const e = checkNumber(v); if (e) problems.push([`df-c-${j}`, `Z · x${j + 1}: ${e}`]); });
    m.constraints.forEach((c, i) => {
      c.coefficients.forEach((v, j) => { const e = checkNumber(v); if (e) problems.push([`df-a-${i}-${j}`, `R${i + 1} · x${j + 1}: ${e}`]); });
      const e = checkNumber(c.rhs); if (e) problems.push([`df-b-${i}`, `R${i + 1} · K: ${e}`]);
    });
    return problems;
  }
  function clearFieldErrors() {
    document.querySelectorAll('.df-field-error').forEach(w => w.classList.remove('df-field-error'));
    document.querySelectorAll('.df-invalid').forEach(i => i.classList.remove('df-invalid'));
    document.querySelectorAll('.df-field-msg').forEach(m => m.remove());
    document.querySelectorAll('[aria-invalid]').forEach(i => { i.removeAttribute('aria-invalid'); i.removeAttribute('aria-describedby'); });
  }
  function markField(id, message) {
    const input = byId(id);
    if (!input) return false;
    input.classList.add('df-invalid'); input.setAttribute('aria-invalid', 'true');
    const host = input.closest('.df-field') || input.closest('.df-eq');
    if (input.closest('.df-field')) host.classList.add('df-field-error');
    if (!host.querySelector(`#${id}-msg`)) { const msg = el('p', message, 'df-field-msg'); msg.id = `${id}-msg`; host.append(msg); }
    input.setAttribute('aria-describedby', `${id}-msg`);
    return true;
  }

  // ---------- Modelo <-> formulario ----------
  function draft() {
    return {sense: byId('df-sense').value,
      objective: Array.from({length: n}, (_, j) => byId(`df-c-${j}`)?.value ?? '0'),
      constraints: constraints.map((_, i) => ({
        coefficients: Array.from({length: n}, (_, j) => byId(`df-a-${i}-${j}`)?.value ?? '0'),
        operator: byId(`df-op-${i}`)?.value ?? '<=', rhs: byId(`df-b-${i}`)?.value ?? '0',
        label: byId(`df-label-${i}`)?.value ?? `R${i + 1}`, unit: byId(`df-cunit-${i}`)?.value ?? ''})),
      variables: Array.from({length: n}, (_, j) => ({name: byId(`df-name-${j}`)?.value ?? `x${j + 1}`, unit: byId(`df-unit-${j}`)?.value ?? 'unidades'})),
      context: byId('df-context').value, objective_name: byId('df-objective-name').value, objective_unit: byId('df-objective-unit').value};
  }
  function render(model) {
    clearFieldErrors();
    n = model.objective.length; constraints = model.constraints;
    byId('df-count').value = n; byId('df-sense').value = model.sense ?? 'max';
    byId('df-context').value = model.context ?? '';
    byId('df-objective-name').value = model.objective_name ?? 'Valor de Z';
    byId('df-objective-unit').value = model.objective_unit ?? 'unidades';
    const obj = byId('df-objective');
    const head = el('span', '', 'df-eq-text'); head.id = 'df-obj-head';
    const parts = [head];
    model.objective.forEach((v, j) => {
      if (j) parts.push(el('span', '+', 'df-eq-text'));
      const t = el('span', undefined, 'df-eq-text'); t.append(varNode(j));
      parts.push(coefInput(`df-c-${j}`, v, `Coeficiente de x${j + 1} en Z`), t);
    });
    obj.replaceChildren(...parts);
    const cards = constraints.map((row, i) => {
      const card = el('div', undefined, 'df-constraint'); card.setAttribute('role', 'group'); card.setAttribute('aria-label', `Restricción R${i + 1}`);
      const eq = el('div', undefined, 'df-eq');
      eq.append(el('span', `R${i + 1}`, 'df-tag'));
      row.coefficients.slice(0, n).concat(Array(Math.max(0, n - row.coefficients.length)).fill('0')).forEach((v, j) => {
        if (j) eq.append(el('span', '+', 'df-eq-text'));
        const t = el('span', undefined, 'df-eq-text'); t.append(varNode(j));
        eq.append(coefInput(`df-a-${i}-${j}`, v, `R${i + 1}: coeficiente de x${j + 1}`), t);
      });
      const sel = el('select', undefined, 'df-rel'); sel.id = `df-op-${i}`; sel.setAttribute('aria-label', `R${i + 1}: relación`);
      [['<=', '≤'], ['>=', '≥'], ['=', '=']].forEach(([v, t]) => { const o = el('option', t); o.value = v; sel.append(o); });
      sel.value = {'≤': '<=', '≥': '>='}[row.operator] ?? row.operator;
      eq.append(sel, coefInput(`df-b-${i}`, row.rhs, `R${i + 1}: término independiente K`), el('span', undefined, 'df-spacer'));
      const remove = el('button', '×', 'df-text-btn df-remove'); remove.type = 'button'; remove.setAttribute('aria-label', `Eliminar restricción R${i + 1}`);
      remove.disabled = constraints.length === 1;
      remove.addEventListener('click', () => { const m = draft(); m.constraints.splice(i, 1); render(m); dirty(); });
      eq.append(remove);
      const names = el('div', undefined, 'df-two');
      names.append(field('Qué representa', row.label ?? `R${i + 1}`, `df-label-${i}`), field('Unidad (opcional)', row.unit ?? '', `df-cunit-${i}`, {maxLength: 80}));
      card.append(eq, names); return card;
    });
    byId('df-constraints').replaceChildren(...cards);
    byId('df-variables').replaceChildren(...Array.from({length: n}, (_, j) => {
      const v = model.variables?.[j] ?? {};
      const w = el('div', undefined, 'df-two');
      w.append(field(`x${j + 1} representa`, v.name ?? `x${j + 1}`, `df-name-${j}`), field('Unidad', v.unit ?? 'unidades', `df-unit-${j}`, {maxLength: 80}));
      return w;
    }));
    byId('df-add-constraint').disabled = constraints.length >= 12;
    refreshPreview();
  }

  // ---------- Vista previa y «lo que hará el método» ----------
  function termNodes(coefs) {
    const frag = []; let first = true;
    coefs.forEach((raw, j) => {
      const t = String(raw).trim(); const bad = checkNumber(t);
      if (!bad && Number(t.replace(',', '.').split('/').reduce((a, b) => a / b)) === 0) return;
      const neg = !bad && t.startsWith('-');
      const mag = bad ? t || '?' : t.replace(/^[+-]/, '');
      if (!first) frag.push(document.createTextNode(neg ? ' − ' : ' + ')); else if (neg) frag.push(document.createTextNode('−'));
      if (bad) frag.push(el('span', mag, 'df-bad-num')); else if (mag !== '1') frag.push(document.createTextNode(mag));
      frag.push(varNode(j)); first = false;
    });
    if (first) frag.push(document.createTextNode('0'));
    return frag;
  }
  function refreshPreview() {
    const m = draft();
    const lines = [];
    const z = el('span'); z.append(document.createTextNode(`${m.sense === 'max' ? 'Max' : 'Min'} Z = `), ...termNodes(m.objective)); lines.push(z);
    lines.push(el('small', 'sujeto a'));
    m.constraints.forEach(c => {
      const s = el('span'); const k = String(c.rhs).trim();
      s.append(...termNodes(c.coefficients), document.createTextNode(` ${{'<=': '≤', '>=': '≥', '=': '='}[c.operator]} `));
      if (checkNumber(k)) s.append(el('span', k || '?', 'df-bad-num')); else s.append(document.createTextNode(minus(k)));
      lines.push(s);
    });
    const nn = el('span'); m.objective.forEach((_, j) => { if (j) nn.append(document.createTextNode(', ')); nn.append(varNode(j)); }); nn.append(document.createTextNode(' ≥ 0')); lines.push(nn);
    byId('df-preview').replaceChildren(...lines);
    byId('df-obj-head').textContent = `${m.sense === 'max' ? 'Max' : 'Min'}  Z =`;
    // Plan del método (texto derivado de las relaciones; el cálculo real lo hace el servidor).
    const items = []; const arts = [];
    m.constraints.forEach((c, i) => {
      let op = c.operator; const k = String(c.rhs).trim(); let pre = '';
      if (!checkNumber(k) && k.startsWith('-') && Number(k.replace(',', '.').split('/').reduce((a, b) => a / b)) !== 0) { op = {'<=': '>=', '>=': '<=', '=': '='}[op]; pre = `R${i + 1} tiene K negativo: se multiplica por −1 y queda ${{'<=': '≤', '>=': '≥', '=': '='}[op]}. `; }
      if (op === '<=') items.push(['', `${pre}R${i + 1} es ≤: se suma la holgura S${i + 1}.`]);
      else if (op === '>=') { arts.push(`A${i + 1}`); items.push(['is-f1', `${pre}R${i + 1} es ≥: se resta el excedente S${i + 1} y se suma la artificial A${i + 1}.`]); }
      else { arts.push(`A${i + 1}`); items.push(['is-f1', `${pre}R${i + 1} es una igualdad: se suma la artificial A${i + 1}.`]); }
    });
    items.push(['is-f1', arts.length ? `La Fase 1 minimizará r = ${arts.join(' + ')} hasta que valga 0.` : 'No hacen falta artificiales: la Fase 1 termina de inmediato con r = 0.']);
    items.push(['is-f2', `Después, la Fase 2 ${m.sense === 'max' ? 'maximizará' : 'minimizará'} Z desde la base factible.`]);
    byId('df-plan-list').replaceChildren(...items.map(([cls, t]) => el('li', t, cls)));
    const chip = (head, name, unit) => { const c = el('span', undefined, 'df-chip'); c.append(head, document.createTextNode(` · ${name || '—'}${unit ? ` (${unit})` : ''}`)); return c; };
    byId('df-context-summary').replaceChildren(...m.variables.map((v, j) => chip(varNode(j), v.name, v.unit)), chip(document.createTextNode('Z'), m.objective_name, m.objective_unit));
  }

  // ---------- Estado visible ----------
  function showError(message) { byId('df-error-text').textContent = message; byId('df-error').hidden = false; }
  function hideError() { byId('df-error').hidden = true; }
  function markStale(on) { byId('df-stale').hidden = !on; byId('df-result').classList.toggle('df-stale-result', on); }
  function dirty() {
    hideError(); refreshPreview();
    if (!lastPayload) return;
    const changed = JSON.stringify(draft()) !== lastKey;
    markStale(changed);
    if (changed) byId('df-status').textContent = 'Hay cambios sin calcular. Lo que ves corresponde al último modelo resuelto.';
  }
  function setRoute(states) {
    document.querySelectorAll('#df-route li').forEach(li => { if (states[li.dataset.step]) li.dataset.state = states[li.dataset.step]; });
  }
  function routeForResult(status) {
    const s = {plantear: 'done', estandarizar: 'done', fase1: 'done', fase2: 'done', comprobar: 'done'};
    if (status === 'infeasible') { s.fase1 = 'fail'; s.fase2 = 'skip'; s.comprobar = 'skip'; }
    if (status === 'unbounded') s.fase2 = 'warn';
    if (status === 'iteration_limit') { s.fase2 = 'warn'; s.comprobar = 'skip'; }
    return s;
  }
  function selectTab(name) {
    document.querySelectorAll('#df-tabs [data-tab]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === name)));
    document.querySelectorAll('#df-result [data-df-panel]').forEach(p => { p.hidden = p.dataset.dfPanel !== name; });
  }
  function download(blob, name) {
    const url = URL.createObjectURL(blob), a = el('a'); a.href = url; a.download = name;
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ---------- Resolver ----------
  async function solve() {
    if (busy) return;
    clearFieldErrors(); hideError();
    const model = draft();
    const local = validateLocal(model);
    if (local.length) {
      local.forEach(([id, msg]) => markField(id, msg.replace(/^[^:]+: /, '')));
      showError(`${local[0][1].replace(/\.$/, '')}${local.length > 1 ? ` (y ${local.length - 1} dato${local.length > 2 ? 's' : ''} más)` : ''}. Corrige lo marcado y vuelve a resolver.`);
      byId(local[0][0]).focus();
      if (lastPayload) markStale(true);
      byId('df-status').textContent = 'El modelo no pudo calcularse. Revisa los datos marcados.';
      return;
    }
    busy = true; byId('df-solve').disabled = true;
    byId('df-status').textContent = 'Calculando las dos fases y verificando las restricciones…';
    try {
      const response = await fetch(endpoints.resolve, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(model)});
      const result = await response.json();
      if (!response.ok) { const err = new Error(result.error ?? 'No se pudo procesar el modelo.'); err.field = result.field; throw err; }
      // El HTML procede de Jinja con autoescape; el navegador no compone HTML con texto del usuario.
      byId('df-result').innerHTML = result.html;
      lastResult = result; lastPayload = model; lastKey = JSON.stringify(model); markStale(false);
      byId('df-tabs').hidden = false; byId('df-export-actions').hidden = false; selectTab('resumen');
      byId('df-expand').textContent = 'Abrir todas las operaciones'; byId('df-expand').setAttribute('aria-pressed', 'false');
      byId('df-results-eyebrow').textContent = `RESULTADO · ${JSON.stringify(model) === exampleKey ? exampleNames[loadedExample] : 'TU MODELO'}`;
      setRoute(routeForResult(result.status));
      const label = {optimal: 'Solución óptima', infeasible: 'Modelo infactible', unbounded: 'Objetivo no acotado', iteration_limit: 'Cálculo detenido'}[result.status] ?? 'Cálculo completo';
      byId('df-status').textContent = `${label}: ${result.events.length} tablas y ${result.iterations} pivote${result.iterations === 1 ? '' : 's'}. Fracciones exactas.`;
      byId('df-results').scrollIntoView({behavior: 'auto', block: 'start'});
    } catch (exc) {
      if (exc.field) markField(exc.field, exc.message.replace(/^[^:]+: /, ''));
      showError(exc.message); if (lastPayload) markStale(true);
      byId('df-status').textContent = 'El modelo no pudo calcularse. Revisa los datos.';
    } finally { busy = false; byId('df-solve').disabled = false; }
  }

  // ---------- Recorrido guiado ----------
  const phaseText = {0: ['', 'is-n'], 1: ['Fase 1 · llegar', 'is-f1'], 2: ['Fase 2 · subir', 'is-f2']};
  function strip(node) { node.removeAttribute('id'); node.querySelectorAll('[id]').forEach(x => x.removeAttribute('id')); return node; }
  function buildSlides() {
    const res = byId('df-result'); const slides = [];
    const maxi = lastResult.model.sense === 'max';
    const plan = el('div', undefined, 'df-g-plan');
    const pv = el('div', undefined, 'df-sheet df-preview'); pv.append(strip(byId('df-preview').cloneNode(true)));
    const pl = el('div', undefined, 'df-sheet'); pl.append(el('h3', 'Lo que hará el método'), strip(byId('df-plan-list').cloneNode(true)));
    plan.append(pv, pl);
    slides.push({eyebrow: 'Paso 01 · Plantear', title: 'El modelo que vamos a resolver', phase: 0, step: 'plantear', node: plan});
    const prep = res.querySelector('#df-modelo');
    if (prep) slides.push({eyebrow: 'Paso 02 · Estandarizar', title: 'Del modelo a la forma estándar', phase: 0, step: 'estandarizar', node: strip(prep.cloneNode(true))});
    res.querySelectorAll('article[data-df-slide="tabla"]').forEach(a => {
      const ph = Number(a.dataset.phase);
      const node = strip(a.cloneNode(true));
      node.querySelectorAll('details').forEach(d => { d.open = false; });
      const ops = node.querySelector('.df-step-main > details.df-operations'); if (ops) ops.parentElement.append(ops); // en el recorrido, primero la tabla
      slides.push({eyebrow: `Tabla ${a.dataset.number} · ${ph === 1 ? 'Fase 1 · llegar a lo factible' : (maxi ? 'Fase 2 · subir al óptimo' : 'Fase 2 · bajar al óptimo')}`,
        title: a.dataset.headline, phase: ph, step: ph === 1 ? 'fase1' : 'fase2', node});
    });
    const verif = res.querySelector('#df-verificacion');
    if (verif) slides.push({eyebrow: 'Paso 05 · Comprobar', title: 'Se comprueba en el modelo original', phase: 0, step: 'comprobar', node: strip(verif.cloneNode(true))});
    const conc = res.querySelector('#df-conclusion');
    if (conc) slides.push({eyebrow: 'Conclusión', title: conc.querySelector('.df-conc-title')?.textContent ?? 'Conclusión', phase: 0, step: 'comprobar', node: strip(conc.cloneNode(true))});
    return slides;
  }
  const lowerFirst = t => t.charAt(0).toLowerCase() + t.slice(1);
  function showSlide(i) {
    guided.index = Math.max(0, Math.min(i, guided.slides.length - 1));
    const s = guided.slides[guided.index];
    const wrap = el('div', undefined, 'df-g-slide');
    const eyebrow = el('p', s.eyebrow, `df-g-eyebrow ${phaseText[s.phase][1]}`);
    wrap.append(eyebrow, el('h2', s.title, 'df-g-title'), s.node);
    byId('df-g-body').replaceChildren(wrap); byId('df-g-body').scrollTop = 0;
    byId('df-g-count').textContent = `${guided.index + 1} de ${guided.slides.length}`; // «Paso 01…05» queda para las estaciones de la ruta
    const chipEl = byId('df-g-phase'); chipEl.textContent = phaseText[s.phase][0]; chipEl.hidden = !s.phase;
    chipEl.className = `df-chip ${s.phase === 1 ? 'df-chip-f1' : 'df-chip-f2'}`;
    byId('df-g-segments').replaceChildren(...guided.slides.map((x, k) => el('span', null, `${x.phase === 1 ? 'is-f1' : x.phase === 2 ? 'is-f2' : ''} ${k < guided.index ? 'is-done' : k === guided.index ? 'is-now' : ''}`)));
    const prev = guided.slides[guided.index - 1], next = guided.slides[guided.index + 1];
    byId('df-g-prev').disabled = !prev;
    byId('df-g-prev').querySelector('span').textContent = prev ? `Anterior: ${lowerFirst(prev.title)}` : 'Anterior';
    byId('df-g-next').querySelector('span').textContent = next ? `Siguiente: ${lowerFirst(next.title)}` : 'Terminar el recorrido';
    const order = ['plantear', 'estandarizar', 'fase1', 'fase2', 'comprobar'];
    const base = routeForResult(lastResult.status);
    order.forEach(k => { if (k === s.step) base[k] = 'current'; });
    setRoute(base);
  }
  function openGuided(i = 0) {
    if (!lastResult) return;
    guided.opener = document.activeElement; guided.slides = buildSlides();
    byId('df-guided').hidden = false; document.body.classList.add('df-guided-open');
    showSlide(i); byId('df-g-body').focus();
  }
  function closeGuided() {
    if (document.fullscreenElement) document.exitFullscreen?.();
    byId('df-guided').hidden = true; document.body.classList.remove('df-guided-open');
    setRoute(routeForResult(lastResult.status)); selectTab('resumen');
    (guided.opener && document.contains(guided.opener) ? guided.opener : byId('df-tab-guiado')).focus();
  }
  byId('df-g-prev').addEventListener('click', () => showSlide(guided.index - 1));
  byId('df-g-next').addEventListener('click', () => { if (guided.index >= guided.slides.length - 1) closeGuided(); else showSlide(guided.index + 1); });
  byId('df-g-close').addEventListener('click', closeGuided);
  byId('df-g-full').addEventListener('click', () => {
    const g = byId('df-guided');
    if (document.fullscreenElement) document.exitFullscreen?.(); else g.requestFullscreen?.().catch(() => g.classList.toggle('df-projecting'));
  });
  document.addEventListener('fullscreenchange', () => byId('df-guided').classList.toggle('df-projecting', Boolean(document.fullscreenElement)));
  document.addEventListener('keydown', e => {
    if (byId('df-guided').hidden) return;
    if (['ArrowRight', 'PageDown'].includes(e.key)) { e.preventDefault(); byId('df-g-next').click(); }
    else if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); showSlide(guided.index - 1); }
    else if (e.key === 'Home') { e.preventDefault(); showSlide(0); }
    else if (e.key === 'End') { e.preventDefault(); showSlide(guided.slides.length - 1); }
    else if (e.key === 'Escape') { e.preventDefault(); closeGuided(); }
    else if (e.key === 'Tab') { // foco contenido dentro del diálogo
      const f = [...byId('df-guided').querySelectorAll('button:not([disabled]),[tabindex="0"],summary,a[href]')].filter(x => x.offsetParent !== null);
      if (!f.length) return; const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // ---------- Eventos ----------
  byId('df-editor').addEventListener('submit', event => { event.preventDefault(); solve(); });
  byId('df-editor').addEventListener('input', event => {
    const t = event.target;
    if (t.classList?.contains('df-invalid')) { t.classList.remove('df-invalid'); t.removeAttribute('aria-invalid'); byId(`${t.id}-msg`)?.remove(); t.closest('.df-field-error')?.classList.remove('df-field-error'); }
    dirty();
  });
  byId('df-editor').addEventListener('change', dirty);
  byId('df-count').addEventListener('change', () => {
    const m = draft(), k = Number(byId('df-count').value);
    m.objective = Array.from({length: k}, (_, j) => m.objective[j] ?? '0');
    m.constraints.forEach(r => { r.coefficients = Array.from({length: k}, (_, j) => r.coefficients[j] ?? '0'); });
    m.variables = Array.from({length: k}, (_, j) => m.variables[j] ?? {name: `x${j + 1}`, unit: 'unidades'});
    render(m); dirty();
  });
  byId('df-add-constraint').addEventListener('click', () => {
    if (constraints.length >= 12) return;
    const m = draft(); m.constraints.push({coefficients: Array(n).fill('0'), operator: '<=', rhs: '0', label: `R${constraints.length + 1}`, unit: ''});
    render(m); dirty(); byId(`df-a-${m.constraints.length - 1}-0`)?.focus();
  });
  function loadExample(name) { loadedExample = name; byId('df-example').value = name; render(structuredClone(examples[name])); exampleKey = JSON.stringify(draft()); }
  byId('df-load-example').addEventListener('click', () => { loadExample(byId('df-example').value); dirty(); });
  byId('df-result').addEventListener('click', event => {
    if (event.target.closest('#df-run-example')) { loadExample('profesora'); solve(); }
    if (event.target.closest('[data-df-action="guiado"]')) openGuided(0);
  });
  byId('df-tabs').addEventListener('click', event => {
    const b = event.target.closest('[data-tab]'); if (!b) return;
    if (b.dataset.tab === 'guiado') openGuided(0); else selectTab(b.dataset.tab);
  });
  byId('df-tabs').addEventListener('keydown', event => {
    if (!['ArrowRight', 'ArrowLeft'].includes(event.key)) return;
    const tabs = [...byId('df-tabs').querySelectorAll('[data-tab]')]; const i = tabs.indexOf(document.activeElement);
    if (i < 0) return; tabs[(i + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length].focus();
  });
  byId('df-route').addEventListener('click', event => {
    const li = event.target.closest('li'); if (!li) return;
    const step = li.dataset.step;
    if (step === 'plantear') return; // ancla directa al formulario
    event.preventDefault();
    if (!lastResult) { byId('df-editor').scrollIntoView({behavior: 'smooth'}); return; }
    const target = {estandarizar: 'df-modelo', fase1: 'df-fase-1', fase2: 'df-fase-2', comprobar: 'df-verificacion'}[step];
    selectTab(step === 'comprobar' ? 'resumen' : 'desarrollo');
    (byId(target) || byId('df-results')).scrollIntoView({behavior: 'smooth', block: 'start'});
  });
  byId('df-download-model').addEventListener('click', () => download(new Blob([JSON.stringify(draft(), null, 2)], {type: 'application/json'}), 'modelo_dos_fases.json'));
  byId('df-import').addEventListener('change', async event => {
    try {
      const f = event.target.files[0]; if (!f) return;
      if (f.size > 100000) throw new Error('El archivo debe ocupar menos de 100 kB.');
      const m = JSON.parse(await f.text());
      if (!m || !Array.isArray(m.objective) || m.objective.length < 1 || m.objective.length > 8 || !Array.isArray(m.constraints) || m.constraints.length < 1 || m.constraints.length > 12 || !m.constraints.every(r => r && Array.isArray(r.coefficients) && r.coefficients.length === m.objective.length)) throw new Error('El JSON no tiene la estructura de un modelo admitido.');
      render(m); dirty();
    } catch (exc) { showError(`No se pudo importar: ${exc.message}`); }
    finally { event.target.value = ''; }
  });
  byId('df-expand').addEventListener('click', () => {
    const items = [...byId('df-result').querySelectorAll('details.df-operations')], open = items.some(d => !d.open);
    items.forEach(d => { d.open = open; });
    if (open) selectTab('desarrollo');
    byId('df-expand').textContent = open ? 'Cerrar todas las operaciones' : 'Abrir todas las operaciones';
    byId('df-expand').setAttribute('aria-pressed', String(open));
  });
  byId('df-report-download').addEventListener('click', async () => {
    if (!lastPayload) return;
    const button = byId('df-report-download'); button.disabled = true;
    try {
      const response = await fetch(endpoints.report, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(lastPayload)});
      if (!response.ok) throw new Error('No se pudo generar el informe.');
      download(await response.blob(), 'informe_dos_fases.html');
    } catch (exc) { showError(exc.message); } finally { button.disabled = false; }
  });
  let printState = [];
  window.addEventListener('beforeprint', () => { printState = [...document.querySelectorAll('details.df-operations')].map(d => [d, d.open]); printState.forEach(([d]) => { d.open = true; }); });
  window.addEventListener('afterprint', () => { printState.forEach(([d, open]) => { d.open = open; }); });
  byId('df-print').addEventListener('click', () => window.print());
  loadExample('profesora');
})();
