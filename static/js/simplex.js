const main = document.querySelector('main');
const MAX_VARS = Number(main.dataset.maxVars), MAX_RES = Number(main.dataset.maxRes);
const $ = id => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e[k] = v; else e.setAttribute(k, v);
  }
  e.append(...children);
  return e;
}
const fmt = v => Math.abs(v) < 1e-8 ? '0' : Number(v).toFixed(4).replace(/\.?0+$/, '');
const lim = (v, vacio) => v === null || v === undefined ? vacio : fmt(v);

/* ───────── estado del modelo (los inputs lo actualizan sin redibujar) ───────── */
let model = ejemplo();
function ejemplo() {
  return {
    sentido: 'max', unidad_z: 'miles de pesos',
    variables: [{nombre: 'Puertas', unidad: 'puertas', costo: '3'}, {nombre: 'Ventanas', unidad: 'ventanas', costo: '5'}],
    restricciones: [
      {nombre: 'Planta 1', unidad: 'horas', coefs: ['1', '0'], rhs: '4'},
      {nombre: 'Planta 2', unidad: 'horas', coefs: ['0', '2'], rhs: '12'},
      {nombre: 'Planta 3', unidad: 'horas', coefs: ['3', '2'], rhs: '18'}],
    contexto: 'Una empresa fabrica puertas y ventanas en tres plantas. Cada planta tiene un número limitado de horas semanales disponibles. Se quiere decidir cuántas puertas y ventanas producir por semana para maximizar la ganancia.',
  };
}

function entrada(valor, clase, alCambiar, etiqueta) {
  const i = el('input', {type: 'text', inputmode: 'decimal', value: valor, class: clase || '', 'aria-label': etiqueta || ''});
  i.addEventListener('input', () => { alCambiar(i.value); preview(); });
  return i;
}
function texto(valor, clase, alCambiar, etiqueta, ph = '') {
  const i = el('input', {type: 'text', value: valor, class: clase, 'aria-label': etiqueta, placeholder: ph});
  i.addEventListener('input', () => { alCambiar(i.value); preview(); });
  return i;
}

function render() {
  const g = $('grid');
  g.replaceChildren();
  const v = model.variables, r = model.restricciones;
  const filaNombres = el('tr', {}, el('th', {}, 'VARIABLE'));
  const filaUnidad = el('tr', {}, el('th', {}, 'UNIDAD'));
  const filaZ = el('tr', {class: 'zrow'}, el('th', {}, 'Z ='));
  v.forEach((x, j) => {
    const quitar = el('button', {type: 'button', class: 'remove', title: 'Quitar variable', 'aria-label': `Quitar ${x.nombre}`}, '×');
    quitar.onclick = () => { if (v.length > 1) { v.splice(j, 1); r.forEach(q => q.coefs.splice(j, 1)); render(); } };
    filaNombres.append(el('td', {}, texto(x.nombre, 'nombre', s => x.nombre = s, `Nombre de la variable ${j + 1}`, `x${j + 1}`), quitar));
    filaUnidad.append(el('td', {}, texto(x.unidad, 'unidad', s => x.unidad = s, `Unidad de la variable ${j + 1}`, 'unid.')));
    filaZ.append(el('td', {}, entrada(x.costo, '', s => x.costo = s, `Coeficiente de la variable ${j + 1} en Z`)));
  });
  g.append(filaNombres, filaUnidad, filaZ, el('tr', {}, el('th', {colspan: v.length + 3}, 'RESTRICCIONES (RECURSO · UNIDAD)')));
  r.forEach((q, i) => {
    const quitar = el('button', {type: 'button', class: 'remove', title: 'Quitar restricción', 'aria-label': `Quitar restricción ${i + 1}`}, '×');
    quitar.onclick = () => { if (r.length > 1) { r.splice(i, 1); render(); } };
    const fila = el('tr', {}, el('td', {}, texto(q.nombre, 'nombre', s => q.nombre = s, `Nombre de la restricción ${i + 1}`, `R${i + 1}`), ' ',
                                texto(q.unidad, 'unidad', s => q.unidad = s, `Unidad de la restricción ${i + 1}`, 'unid.')));
    q.coefs.forEach((c, j) => fila.append(el('td', {}, entrada(c, '', s => q.coefs[j] = s, `Coeficiente de ${v[j].nombre || 'x' + (j + 1)} en la restricción ${i + 1}`))));
    fila.append(el('td', {class: 'op'}, '≤'), el('td', {}, entrada(q.rhs, '', s => q.rhs = s, `Lado derecho de la restricción ${i + 1}`)), el('td', {}, quitar));
    g.append(fila);
  });
  $('sentido').value = model.sentido;
  $('unidad-z').value = model.unidad_z;
  $('contexto').value = model.contexto;
  preview();
}

function preview() {
  const nombres = model.variables.map((x, j) => x.nombre.trim() || `x${j + 1}`);
  const lin = coefs => coefs.map((c, j) => `${(String(c).trim() || '0')}·${nombres[j]}`).join(' + ').replace(/\+ -/g, '- ');
  const lineas = [`${model.sentido}  Z = ${lin(model.variables.map(x => x.costo))}`, 's.a.'];
  model.restricciones.forEach(q => lineas.push(`   ${lin(q.coefs)}  ≤  ${String(q.rhs).trim() || '?'}`));
  lineas.push(`   ${nombres.join(', ')} ≥ 0`);
  $('preview').textContent = lineas.join('\n');
}

$('sentido').onchange = e => { model.sentido = e.target.value; preview(); };
$('unidad-z').oninput = e => { model.unidad_z = e.target.value; };
$('contexto').oninput = e => { model.contexto = e.target.value; };
$('add-var').onclick = () => {
  if (model.variables.length >= MAX_VARS) return mostrarError(`Máximo ${MAX_VARS} variables.`);
  model.variables.push({nombre: '', unidad: '', costo: '0'});
  model.restricciones.forEach(q => q.coefs.push('0'));
  render();
};
$('add-res').onclick = () => {
  if (model.restricciones.length >= MAX_RES) return mostrarError(`Máximo ${MAX_RES} restricciones.`);
  model.restricciones.push({nombre: '', unidad: '', coefs: model.variables.map(() => '0'), rhs: '0'});
  render();
};
$('sample').onclick = () => { model = ejemplo(); ocultar(); render(); };
$('theme').onclick = () => document.body.classList.toggle('light');

function mostrarError(msg) { $('error').textContent = msg; }
function ocultar() { mostrarError(''); ['result', 'interp', 'sens', 'steps'].forEach(id => $(id).hidden = true); }

/* ───────── resultados ───────── */
function tabla(destino, cabecera, filas, resaltar) {
  destino.replaceChildren(el('thead', {}, el('tr', {}, ...cabecera.map(h => el('th', {}, h)))),
    el('tbody', {}, ...filas.map((f, i) => el('tr', {class: resaltar && resaltar(i) ? 'limitante' : ''}, ...f.map(c => el('td', {}, c))))));
}

function mostrar(d) {
  $('result').hidden = $('interp').hidden = $('steps').hidden = false;
  $('sens').hidden = d.estado !== 'optimo';
  const stats = $('stats');
  stats.replaceChildren();
  const estado = d.estado === 'optimo' ? 'ÓPTIMO' : 'NO ACOTADO';
  stats.append(el('div', {class: 'stat'}, el('small', {}, 'Estado'), el('span', {class: 'badge' + (d.estado === 'optimo' ? '' : ' warn')}, '● ' + estado)));
  if (d.estado === 'optimo') {
    stats.append(el('div', {class: 'stat'}, el('small', {}, `Z* ${d.unidad_z}`), el('strong', {}, fmt(d.z))));
    d.variables.forEach((x, j) => stats.append(el('div', {class: 'stat'}, el('small', {}, x.nombre + (x.unidad ? ` (${x.unidad})` : '')), el('strong', {}, fmt(d.x[j])))));
    stats.append(el('div', {class: 'stat'}, el('small', {}, 'Iteraciones'), el('strong', {}, String(d.iterations.length - 1))));
  }
  const body = $('interp-body');
  body.replaceChildren(...d.interpretacion.map((s, k) => {
    const esUltima = k === d.interpretacion.length - 1 && d.estado === 'optimo';
    return el('div', {class: 'interp-sec' + (esUltima ? ' concl' : '')}, el('h3', {}, s.titulo),
      s.items.length === 1 && s.titulo === 'Contexto' ? el('p', {}, s.items[0]) : el('ul', {}, ...s.items.map(t => el('li', {}, t))));
  }));
  if (d.estado === 'optimo') {
    tabla($('t-res'), ['Restricción', 'b', 'Holgura', 'Precio sombra', 'b mín', 'b máx'],
      d.sens_restricciones.map((s, i) => [s.restriccion, fmt(s.rhs), fmt(d.holguras[i]), fmt(s.precio_sombra), lim(s.minimo, '−∞'), lim(s.maximo, '∞')]),
      i => d.sens_restricciones[i].precio_sombra !== 0);
    tabla($('t-var'), ['Variable', 'Tipo', 'c', 'c mín', 'c máx', 'Costo reducido'],
      d.sens_variables.map(s => [s.variable, s.tipo, fmt(s.coeficiente), lim(s.minimo, '−∞'), lim(s.maximo, '∞'), fmt(s.costo_reducido)]));
  }
  $('modelo').textContent = d.modelo;
  const cont = $('tables');
  cont.replaceChildren(...d.iterations.map((paso, k) => {
    const det = el('details', {}, el('summary', {}, `Tabla ${k + 1} · ${paso.label}`));
    if (k === 0 || k === d.iterations.length - 1) det.open = true;
    const t = el('table', {class: 'tableau'}, el('tr', {}, ...['Base', ...paso.columns].map(n => el('th', {}, n))));
    paso.rows.forEach((fila, r) => {
      const ultima = r === paso.rows.length - 1;
      t.append(el('tr', {}, el('th', {}, ultima ? 'Z' : paso.basis[r]),
        ...fila.map((v, c) => el('td', {class: paso.pivot && paso.pivot[0] === r && paso.pivot[1] === c ? 'pivot' : ''}, fmt(v)))));
    });
    det.append(el('div', {class: 'scroll'}, t));
    return det;
  }));
}

$('solve').onclick = async () => {
  mostrarError('');
  const cuerpo = {
    sentido: model.sentido, unidad_z: model.unidad_z, contexto: model.contexto,
    variables: model.variables.map(x => ({nombre: x.nombre, unidad: x.unidad, costo: x.costo})),
    restricciones: model.restricciones.map(q => ({nombre: q.nombre, unidad: q.unidad, coefs: q.coefs, tipo: '<=', rhs: q.rhs})),
  };
  try {
    const resp = await fetch(main.dataset.apiUrl, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cuerpo)});
    const data = await resp.json();
    if (!resp.ok) throw Error(data.error || 'No se pudo calcular.');
    mostrar(data);
    $('result').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (e) { mostrarError(e.message); }
};

render();
