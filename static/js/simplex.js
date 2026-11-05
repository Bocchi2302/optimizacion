const main = document.querySelector('main');
const MAX_VARS = Number(main.dataset.maxVars), MAX_RES = Number(main.dataset.maxRes);
const $ = id => document.getElementById(id);
const REDUCIR = matchMedia('(prefers-reduced-motion: reduce)').matches;
const NS = 'http://www.w3.org/2000/svg';
const COLORES = ['#ff5b3a', '#6b4dff', '#17b6bb', '#ff6fb5', '#e0a800', '#7aa000'];

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e[k] = v; else e.setAttribute(k, v);
  }
  e.append(...children);
  return e;
}
function svg(tag, attrs = {}, texto) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (texto !== undefined) e.textContent = texto;
  return e;
}
const fmt = v => Math.abs(v) < 1e-8 ? '0' : Number(v).toFixed(4).replace(/\.?0+$/, '');
const lim = (v, vacio) => v === null || v === undefined ? vacio : fmt(v);
function num(s) {   // acepta 2,5 y 1/3 igual que el servidor
  s = String(s).trim().replace(',', '.');
  if (s.includes('/')) { const [a, b] = s.split('/'); return Number(a) / Number(b); }
  return Number(s);
}

/* ───────── estado del modelo (los inputs lo actualizan sin redibujar) ───────── */
/* ───────── biblioteca de ejemplos ───────── */
function plan(sentido, unidad_z, vars, res, contexto) {
  return {
    sentido, unidad_z, contexto,
    variables: vars.map(([nombre, unidad, costo]) => ({nombre, unidad, costo})),
    restricciones: res.map(([nombre, unidad, coefs, rhs]) => ({nombre, unidad, coefs, rhs})),
  };
}
const EJEMPLOS = [
  {grupo: 'Problemas de aplicación', id: 'puertas', nombre: 'Puertas y ventanas (el clásico)',
   nota: 'Dos variables: mira cómo el punto salta de vértice en vértice en "La ruta".',
   modelo: plan('max', 'miles de pesos', [['Puertas', 'puertas', '3'], ['Ventanas', 'ventanas', '5']],
     [['Planta 1', 'horas', ['1', '0'], '4'], ['Planta 2', 'horas', ['0', '2'], '12'], ['Planta 3', 'horas', ['3', '2'], '18']],
     'Una empresa fabrica puertas y ventanas en tres plantas. Cada planta tiene un número limitado de horas semanales disponibles. Se quiere decidir cuántas puertas y ventanas producir por semana para maximizar la ganancia.')},
  {grupo: 'Problemas de aplicación', id: 'muebles', nombre: 'Taller de muebles (3 productos)',
   nota: 'Hay una silla que no se fabrica: fíjate en su costo reducido en la interpretación.',
   modelo: plan('max', 'miles de pesos', [['Mesas', 'mesas', '90'], ['Sillas', 'sillas', '50'], ['Escritorios', 'escritorios', '120']],
     [['Madera', 'm²', ['6', '3', '8'], '360'], ['Carpintería', 'horas', ['4', '2', '5'], '200'], ['Acabado', 'horas', ['2', '2', '3'], '110']],
     'Un taller fabrica mesas, sillas y escritorios. Cada producto consume madera, horas de carpintería y horas de acabado, que son limitadas. Se busca la combinación que deje la mayor utilidad por mes.')},
  {grupo: 'Problemas de aplicación', id: 'jugos', nombre: 'Fábrica de jugos (todo se agota)',
   nota: 'Los tres recursos quedan limitantes: compara sus precios sombra para saber cuál conviene ampliar.',
   modelo: plan('max', 'USD', [['Jugo de mango', 'lotes', '8'], ['Jugo de fresa', 'lotes', '6'], ['Jugo de maracuyá', 'lotes', '6']],
     [['Pulpa', 'kg', ['1', '1', '3'], '300'], ['Azúcar', 'kg', ['3', '2', '2'], '240'], ['Envasado', 'horas', ['3', '3', '1'], '150']],
     'Una fábrica prepara lotes de jugo de mango, fresa y maracuyá. Cada lote usa pulpa, azúcar y horas de envasado, y el ingreso por lote es distinto. Se quiere maximizar el ingreso semanal con los recursos disponibles.')},
  {grupo: 'Problemas de aplicación', id: 'inversion', nombre: 'Plan de inversión',
   nota: 'El retorno es una fracción: fíjate en cómo la interpretación usa la unidad de Z.',
   modelo: plan('max', 'millones de retorno', [['CDT', 'millones', '0.06'], ['Fondos', 'millones', '0.09'], ['Acciones', 'millones', '0.14'], ['Bienes raíces', 'millones', '0.11']],
     [['Presupuesto', 'millones', ['1', '1', '1', '1'], '100'], ['Riesgo', 'puntos', ['1', '3', '5', '4'], '300'],
      ['Tope en acciones', 'millones', ['0', '0', '1', '0'], '30'], ['Tope en bienes raíces', 'millones', ['0', '0', '0', '1'], '40']],
     'Un inversionista dispone de 100 millones y puede ponerlos en CDT, fondos, acciones y bienes raíces. Cada opción tiene un retorno distinto y un nivel de riesgo, y no quiere superar cierto riesgo total ni poner demasiado en acciones o bienes raíces. Quiere maximizar el retorno.')},
  {grupo: 'Casos especiales', id: 'multiples', nombre: 'Óptimos múltiples',
   nota: 'La recta de Z es paralela a una restricción: hay muchas soluciones con el mismo Z. Mira la sección de observaciones.',
   modelo: plan('max', 'pesos', [['Producto A', 'unidades', '2'], ['Producto B', 'unidades', '4']],
     [['Horas de máquina', 'horas', ['1', '2'], '10'], ['Tope del producto A', 'unidades', ['1', '0'], '8']],
     'Dos productos comparten la misma máquina. El producto B rinde exactamente el doble que A y usa el doble de tiempo, así que a la empresa le da igual qué combinación elegir.')},
  {grupo: 'Casos especiales', id: 'degenerado', nombre: 'Solución degenerada',
   nota: 'Dos restricciones se cruzan justo en el óptimo: una variable básica vale 0.',
   modelo: plan('max', 'pesos', [['Producto A', 'unidades', '2'], ['Producto B', 'unidades', '1']],
     [['Capacidad total', 'unidades', ['1', '1'], '4'], ['Tope del producto A', 'unidades', ['1', '0'], '4'], ['Tope del producto B', 'unidades', ['0', '1'], '3']],
     'Una planta puede producir a lo sumo 4 unidades en total, y el producto A también tiene un tope de 4. Esas dos restricciones se vuelven activas al mismo tiempo.')},
  {grupo: 'Casos especiales', id: 'no_acotado', nombre: 'Problema no acotado',
   nota: 'Falta una restricción: el algoritmo detecta que Z puede crecer sin límite.',
   modelo: plan('max', 'pesos', [['Producto A', 'unidades', '2'], ['Producto B', 'unidades', '1']],
     [['Relación A − B', 'unidades', ['1', '-1'], '4']],
     'Un modelo mal planteado: solo se limita la diferencia entre A y B, pero no hay ningún recurso que impida producir cada vez más de ambos.')},
];
const copiar = o => JSON.parse(JSON.stringify(o));
let model = ejemplo();
function ejemplo() { return copiar(EJEMPLOS[0].modelo); }

(function armarSelector() {
  const sel = $('ejemplos');
  for (const grupo of [...new Set(EJEMPLOS.map(e => e.grupo))]) {
    sel.append(el('optgroup', {label: grupo}, ...EJEMPLOS.filter(e => e.grupo === grupo).map(e => el('option', {value: e.id}, e.nombre))));
  }
  sel.onchange = () => {
    const e = EJEMPLOS.find(x => x.id === sel.value);
    if (!e) return;
    model = copiar(e.modelo); ocultar(); render();
    $('ej-nota').textContent = e.nota;
  };
})();

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

try { if (localStorage.getItem('simplex-tema') === 'night') document.body.classList.add('night'); } catch (e) {}
$('theme').onclick = () => {
  const noche = document.body.classList.toggle('night');
  try { localStorage.setItem('simplex-tema', noche ? 'night' : 'day'); } catch (e) {}
};

function mostrarError(msg) { $('error').textContent = msg; }
function ocultar() { mostrarError(''); detener(); ['result', 'interp', 'sens', 'steps', 'path', 'whatif', 'dual'].forEach(id => $(id).hidden = true); }

/* ───────── efectos ───────── */
function contar(destino, hasta) {
  destino.dataset.final = fmt(hasta);   // el informe impreso usa siempre el valor final
  if (REDUCIR) { destino.textContent = fmt(hasta); return; }
  const t0 = performance.now(), dur = 1000;
  (function paso(t) {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    destino.textContent = fmt(hasta * e);
    if (p < 1) requestAnimationFrame(paso); else destino.textContent = fmt(hasta);
  })(t0);
}
function confeti(origen) {
  if (REDUCIR) return;
  const r = origen.getBoundingClientRect(), x0 = r.left + r.width / 2, y0 = r.top + r.height / 2;
  const paleta = ['#ff5b3a', '#ffd23f', '#4fe3e6', '#c8f031', '#6b4dff', '#ff6fb5'];
  for (let i = 0; i < 42; i++) {
    const c = el('div', {class: 'confetti'});
    c.style.left = x0 + 'px'; c.style.top = y0 + 'px'; c.style.background = paleta[i % paleta.length];
    if (i % 3 === 0) c.style.borderRadius = '50%';
    document.body.append(c);
    const ang = Math.random() * Math.PI * 2, dist = 90 + Math.random() * 220;
    c.animate([{transform: 'translate(0,0) rotate(0)', opacity: 1},
      {transform: `translate(${Math.cos(ang) * dist}px,${Math.sin(ang) * dist + 120}px) rotate(${Math.random() * 720}deg)`, opacity: 0}],
      {duration: 900 + Math.random() * 500, easing: 'cubic-bezier(.2,.7,.3,1)'}).onfinish = () => c.remove();
  }
}

/* ───────── tablas de resultados ───────── */
function tabla(destino, cabecera, filas, resaltar) {
  destino.replaceChildren(el('thead', {}, el('tr', {}, ...cabecera.map(h => el('th', {}, h)))),
    el('tbody', {}, ...filas.map((f, i) => el('tr', {class: resaltar && resaltar(i) ? 'limitante' : ''}, ...f.map(c => el('td', {}, c))))));
}

/* ───────── ruta del Simplex (vértice a vértice) y gráfica de Z ───────── */
let R = null;   // estado de la animación

function detener() { if (R) { R.token++; R.jugando = false; const b = $('p-play'); if (b) b.textContent = '▶'; } }

function paso(max) {
  const crudo = max / 6, mag = Math.pow(10, Math.floor(Math.log10(crudo)));
  return [1, 2, 2.5, 5, 10].map(m => m * mag).find(m => m >= crudo);
}
function segmento(a, b, c, xm, ym) {
  const pts = [];
  if (b) for (const x of [0, xm]) { const y = (c - a * x) / b; if (y >= -1e-9 && y <= ym + 1e-9) pts.push([x, y]); }
  if (a) for (const y of [0, ym]) { const x = (c - b * y) / a; if (x >= -1e-9 && x <= xm + 1e-9) pts.push([x, y]); }
  const u = pts.filter((p, i) => pts.findIndex(q => Math.abs(p[0] - q[0]) + Math.abs(p[1] - q[1]) < 1e-9) === i);
  return u.length >= 2 ? u.slice(0, 2) : null;
}
function recortar(poly, a, b, c) {
  const out = [];
  poly.forEach((P, i) => {
    const Q = poly[(i + 1) % poly.length], fp = a * P[0] + b * P[1] - c, fq = a * Q[0] + b * Q[1] - c;
    if (fp <= 1e-9) out.push(P);
    if ((fp <= 1e-9) !== (fq <= 1e-9)) { const t = fp / (fp - fq); out.push([P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1])]); }
  });
  return out;
}

function prepararRuta(d, cuerpo) {
  const signo = d.sentido === 'min' ? -1 : 1, n = d.variables.length;
  const estados = d.iterations.map(it => {
    const x = Array(n).fill(0);
    it.basis_idx.forEach((j, i) => { if (j < n) x[j] = it.rows[i][it.rows[i].length - 1]; });
    return {x, z: signo * it.rows[it.rows.length - 1][it.rows[it.rows.length - 1].length - 1], label: it.label, explicacion: it.explicacion};
  });
  R = {d, estados, n, k: 0, pos: null, jugando: false, token: 0, dets: [], barras: []};
  R.dibujarZ = dibujarZ;
  dibujarZ();
  const caja = $('path-svg');
  caja.replaceChildren();
  $('path-na').hidden = n === 2;
  caja.style.display = n === 2 ? 'block' : 'none';
  if (n === 2) dibujarPlano(cuerpo);
  irA(0, false);
}

function dibujarZ() {
  const z = $('zchart'), zs = R.estados.map(e => e.z), N = zs.length;
  z.replaceChildren();
  const lo = Math.min(0, ...zs), hi = Math.max(0, ...zs) || 1, rango = (hi - lo) || 1;
  const L = 14, W = 372, T = 24, B = 170, y = v => B - (v - lo) / rango * (B - T), bw = Math.min(54, W / N - 8);
  z.append(svg('line', {x1: L, x2: L + W, y1: y(0), y2: y(0), style: 'stroke:var(--edge);stroke-width:2.5'}));
  R.barras = zs.map((v, i) => {
    const x = L + (W / N) * i + (W / N - bw) / 2, y0 = y(0), y1 = y(v);
    const g = svg('g', {style: 'cursor:pointer'});
    const r = svg('rect', {x, y: Math.min(y0, y1), width: bw, height: Math.max(3, Math.abs(y0 - y1)), rx: 6,
      style: 'stroke:var(--edge);stroke-width:2.5;transition:fill .3s'});
    g.append(r, svg('text', {x: x + bw / 2, y: Math.min(y0, y1) - 6, 'text-anchor': 'middle', 'font-size': 12}, fmt(v)),
      svg('text', {x: x + bw / 2, y: 190, 'text-anchor': 'middle', 'font-size': 11, style: 'fill:var(--muted)'}, `T${i + 1}`));
    g.onclick = () => { detener(); irA(i, true); };
    z.append(g);
    return r;
  });
}

function dibujarPlano(cuerpo) {
  const caja = $('path-svg'), d = R.d;
  const rs = cuerpo.restricciones.map(q => ({a: [num(q.coefs[0]), num(q.coefs[1])], b: num(q.rhs)}));
  const cs = cuerpo.variables.map(v => num(v.costo));
  const maxX = Math.max(...rs.filter(r => r.a[0] > 0).map(r => r.b / r.a[0]), ...R.estados.map(e => e.x[0]));
  const maxY = Math.max(...rs.filter(r => r.a[1] > 0).map(r => r.b / r.a[1]), ...R.estados.map(e => e.x[1]));
  const xm = (isFinite(maxX) && maxX > 0 ? maxX : 10) * 1.2, ym = (isFinite(maxY) && maxY > 0 ? maxY : 10) * 1.2;
  const ml = 54, mr = 20, mt = 18, mb = 42, W = 640, H = 440;
  const sx = x => ml + x / xm * (W - ml - mr), sy = y => H - mb - y / ym * (H - mt - mb);
  R.sx = sx; R.sy = sy; R.xm = xm; R.ym = ym; R.cs = cs;

  const linea = (x1, y1, x2, y2, estilo) => svg('line', {x1, y1, x2, y2, style: estilo});
  for (const [max, esX] of [[xm, true], [ym, false]]) {
    const p = paso(max);
    for (let k = 0; k * p <= max + 1e-9; k++) {
      const v = k * p;
      if (esX) { caja.append(linea(sx(v), mt, sx(v), H - mb, 'stroke:var(--dots);stroke-width:1.5'), svg('text', {x: sx(v), y: H - mb + 20, 'text-anchor': 'middle', 'font-size': 12, style: 'fill:var(--muted)'}, `${+v.toFixed(2)}`)); }
      else { caja.append(linea(ml, sy(v), W - mr, sy(v), 'stroke:var(--dots);stroke-width:1.5'), svg('text', {x: ml - 8, y: sy(v) + 4, 'text-anchor': 'end', 'font-size': 12, style: 'fill:var(--muted)'}, `${+v.toFixed(2)}`)); }
    }
  }
  caja.append(linea(ml, H - mb, W - mr, H - mb, 'stroke:var(--edge);stroke-width:3'), linea(ml, mt, ml, H - mb, 'stroke:var(--edge);stroke-width:3'),
    svg('text', {x: W - mr, y: H - 6, 'text-anchor': 'end', 'font-size': 14, style: 'fill:var(--c1)'}, d.variables[0].nombre || 'x1'),
    svg('text', {x: ml + 8, y: mt + 4, 'font-size': 14, style: 'fill:var(--c1)'}, d.variables[1].nombre || 'x2'));

  let poly = [[0, 0], [xm, 0], [xm, ym], [0, ym]];
  rs.forEach(r => { if (poly.length) poly = recortar(poly, r.a[0], r.a[1], r.b); });
  if (poly.length) caja.append(svg('polygon', {points: poly.map(p => `${sx(p[0])},${sy(p[1])}`).join(' '), style: 'fill:#c8f031;fill-opacity:.55;stroke:var(--edge);stroke-width:3;stroke-linejoin:round'}));
  rs.forEach((r, i) => {
    const s = segmento(r.a[0], r.a[1], r.b, xm, ym);
    if (!s) return;
    caja.append(svg('line', {x1: sx(s[0][0]), y1: sy(s[0][1]), x2: sx(s[1][0]), y2: sy(s[1][1]), stroke: COLORES[i % COLORES.length], 'stroke-width': 4, 'stroke-linecap': 'round'}));
    const e = s[0][1] >= s[1][1] ? s[0] : s[1];
    caja.append(svg('text', {x: Math.min(W - 60, sx(e[0]) + 6), y: Math.max(mt + 12, sy(e[1]) - 6), 'font-size': 12, fill: COLORES[i % COLORES.length], style: 'paint-order:stroke;stroke:var(--field);stroke-width:4px'}, cuerpo.restricciones[i].nombre || `R${i + 1}`));
  });
  R.iso = svg('line', {style: 'stroke:var(--edge);stroke-width:3;stroke-dasharray:9 7'});
  R.isoTxt = svg('text', {'font-size': 13, style: 'fill:var(--edge);paint-order:stroke;stroke:var(--field);stroke-width:4px'});
  R.rastro = svg('polyline', {fill: 'none', style: 'stroke:var(--c2);stroke-width:4;stroke-dasharray:2 9;stroke-linecap:round;stroke-linejoin:round'});
  R.puntos = svg('g');
  R.saltador = svg('g');
  R.saltador.append(svg('circle', {r: 13, style: 'fill:var(--c1);stroke:var(--edge);stroke-width:3.5'}), svg('circle', {r: 4, fill: '#fff'}));
  R.etiqueta = svg('text', {'font-size': 13, style: 'fill:var(--edge);paint-order:stroke;stroke:var(--field);stroke-width:5px'});
  caja.append(R.iso, R.isoTxt, R.rastro, R.puntos, R.saltador, R.etiqueta);
}

function colocar(x, y) {   // mueve al "saltador" y su etiqueta
  if (R.n !== 2) return;
  const px = R.sx(x), py = R.sy(y);
  R.pos = [x, y];
  R.saltador.setAttribute('transform', `translate(${px},${py})`);
  R.etiqueta.setAttribute('x', Math.min(px + 18, 520)); R.etiqueta.setAttribute('y', Math.max(py - 18, 30));
  R.etiqueta.textContent = `(${fmt(x)}, ${fmt(y)})`;
}

function irA(k, animar) {
  const E = R.estados;
  k = Math.max(0, Math.min(E.length - 1, k));
  const dest = E[k], ant = R.k;
  R.k = k;
  const marcar = () => {
    if (R.n === 2) {
      R.rastro.setAttribute('points', E.slice(0, k + 1).map(e => `${R.sx(e.x[0])},${R.sy(e.x[1])}`).join(' '));
      R.puntos.replaceChildren(...E.slice(0, k + 1).map(e => svg('circle', {cx: R.sx(e.x[0]), cy: R.sy(e.x[1]), r: 5, style: 'fill:var(--c2);stroke:var(--edge);stroke-width:2'})));
      const [c1, c2] = R.cs, s = segmento(c1, c2, dest.z, R.xm, R.ym);
      if (s) {
        R.iso.setAttribute('x1', R.sx(s[0][0])); R.iso.setAttribute('y1', R.sy(s[0][1]));
        R.iso.setAttribute('x2', R.sx(s[1][0])); R.iso.setAttribute('y2', R.sy(s[1][1]));
        R.iso.style.display = R.isoTxt.style.display = '';
        const m = s[0][1] >= s[1][1] ? s[0] : s[1];
        R.isoTxt.setAttribute('x', R.sx(m[0]) + 8); R.isoTxt.setAttribute('y', R.sy(m[1]) + 16);
        R.isoTxt.textContent = `Z = ${fmt(dest.z)}`;
      } else R.iso.style.display = R.isoTxt.style.display = 'none';
    }
    R.barras.forEach((b, i) => b.style.fill = i === k ? '#ff5b3a' : (i < k ? '#c8f031' : 'var(--card)'));
    R.dets.forEach((dt, i) => dt.classList.toggle('active', i === k));
    const info = $('p-info');
    info.replaceChildren(el('b', {}, `Tabla ${k + 1} de ${E.length} · Vértice (${dest.x.map(fmt).join(', ')}) · Z = ${fmt(dest.z)}`),
      el('span', {class: 'explica-corta'}, dest.explicacion));
  };
  if (R.n === 2) {
    const [x0, y0] = R.pos || E[ant].x, [x1, y1] = dest.x;
    if (!animar || REDUCIR) colocar(x1, y1);
    else {
      const tk = ++R.token, t0 = performance.now(), dur = 650;
      R.enVuelo = true;
      (function frame(t) {
        if (tk !== R.token) return;
        const p = Math.min(1, (t - t0) / dur), e = p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
        colocar(x0 + (x1 - x0) * e, y0 + (y1 - y0) * e - Math.sin(Math.PI * p) * R.ym * .05);
        if (p < 1) requestAnimationFrame(frame); else { colocar(x1, y1); R.enVuelo = false; }
      })(t0);
    }
  }
  marcar();
}

function reproducir() {
  if (!R) return;
  if (R.jugando) return detener();
  if (R.k >= R.estados.length - 1) irA(0, false);
  R.jugando = true; $('p-play').textContent = '⏸';
  const tk = ++R.token;
  (function siguiente() {
    setTimeout(() => {
      if (tk !== R.token || !R.jugando) return;
      if (R.k >= R.estados.length - 1) { R.jugando = false; $('p-play').textContent = '▶'; return; }
      irA(R.k + 1, true); siguiente();
    }, R.k === 0 ? 500 : 1000);
  })();
}
$('p-play').onclick = reproducir;
$('p-next').onclick = () => { if (R) { detener(); irA(R.k + 1, true); } };
$('p-prev').onclick = () => { if (R) { detener(); irA(R.k - 1, true); } };
$('p-reset').onclick = () => { if (R) { detener(); irA(0, true); } };

/* ───────── el dual ───────── */
function mostrarDual(d) {
  const D = d.dual, esMin = D.signo === -1;
  $('dual-intro').textContent =
    'Cada restricción del problema original se vuelve una variable del dual (yᵢ: lo que vale una unidad extra de ese recurso) y cada variable ' +
    'se vuelve una restricción. El dual minimiza el valor total de los recursos y, en el óptimo, da el mismo resultado.' +
    (esMin ? ' Como el problema original se minimiza, el método trabaja con −Z; por eso aparece como max Z′ y W* = −Z*.' : '');
  $('d-primal').textContent = D.primal_modelo.join('\n');
  $('d-dual').textContent = D.dual_modelo.join('\n');
  const ok = D.fuerte;
  $('d-banner').replaceChildren(
    el('span', {class: 'dw'}, `W* = ${fmt(D.w)}`), el('span', {class: 'ig'}, '='), el('span', {class: 'dw'}, `${esMin ? '−' : ''}Z* = ${fmt(D.signo * d.z)}`),
    el('span', {class: 'badge' + (ok ? '' : ' warn')}, ok ? '✔ dualidad fuerte' : '✗ no coincide'));
  const marca = b => b ? '✔' : '✗';
  tabla($('d-y'), ['Variable', 'Recurso', 'y*', 'Holgura del recurso', 'y* · holgura', 'Complementaria'],
    D.y.map(y => [y.nombre, y.recurso, fmt(y.valor), fmt(y.holgura), fmt(y.valor * y.holgura), marca(y.complementaria)]),
    i => D.y[i].valor !== 0);
  tabla($('d-v'), ['Variable', 'x*', 'Exceso del dual (zⱼ − cⱼ)', 'x* · exceso', 'Complementaria'],
    D.restricciones.map(r => [r.variable, fmt(r.x), fmt(r.exceso), fmt(r.x * r.exceso), marca(r.complementaria)]));
}

/* ───────── modo "¿y si…?" ───────── */
let QS = null;   // recurso seleccionado y verificación pendiente

function prepararQueSi(d, cuerpo) {
  const pills = $('wi-pills');
  pills.replaceChildren(...d.sens_restricciones.map((r, i) => {
    const b = el('button', {type: 'button', class: 'pill', role: 'tab'}, r.restriccion || `R${i + 1}`);
    b.onclick = () => elegirRecurso(d, cuerpo, i);
    return b;
  }));
  // por defecto, el recurso limitante con mayor precio sombra (el más interesante para mover)
  let mejor = 0;
  d.sens_restricciones.forEach((r, i) => { if (Math.abs(r.precio_sombra) > Math.abs(d.sens_restricciones[mejor].precio_sombra)) mejor = i; });
  elegirRecurso(d, cuerpo, mejor);
}

function elegirRecurso(d, cuerpo, i) {
  [...$('wi-pills').children].forEach((b, k) => { b.classList.toggle('on', k === i); b.setAttribute('aria-selected', k === i); });
  const r = d.sens_restricciones[i], unidad = d.restricciones[i].unidad;
  const lo = Math.max(0, r.minimo ?? 0);
  const topeVisual = r.maximo === null || r.maximo === undefined;
  const hi = topeVisual ? Math.max(r.rhs * 2, r.rhs + 10) : r.maximo;
  const fijo = hi - lo < 1e-9;
  const rango = el('input', {type: 'range', min: lo, max: hi, step: fijo ? 1 : (hi - lo) / 400, value: r.rhs, 'aria-label': `Límite de ${r.restriccion}`});
  const numero = el('input', {type: 'number', min: lo, max: hi, step: 'any', value: fmt(r.rhs), class: 'wi-num', 'aria-label': 'Valor exacto'});
  if (fijo) rango.disabled = numero.disabled = true;
  const salida = el('div', {class: 'wi-out'}), frase = el('p', {class: 'wi-frase'}), verif = el('p', {class: 'wi-verif'});
  const reset = el('button', {type: 'button', class: 'btn sm'}, '↺ Original');

  const mover = v => {
    v = Math.min(hi, Math.max(lo, v));
    const delta = v - r.rhs, zNuevo = d.z + r.precio_sombra * delta;
    const tarjeta = (titulo, antes, ahora, clase = '') => {
      const dif = ahora - antes, hay = Math.abs(dif) > 1e-9;
      return el('div', {class: 'stat ' + clase}, el('small', {}, titulo),
        el('strong', {}, hay ? `${fmt(antes)} → ${fmt(ahora)}` : fmt(ahora)),
        el('span', {class: 'delta ' + (hay ? (dif > 0 ? 'up' : 'down') : 'igual')}, hay ? `${dif > 0 ? '▲ +' : '▼ '}${fmt(dif)}` : 'sin cambio'));
    };
    salida.replaceChildren(tarjeta(`Z* ${d.unidad_z}`.trim(), d.z, zNuevo, 'big'),
      ...d.variables.map((x, j) => tarjeta(x.nombre + (x.unidad ? ` (${x.unidad})` : ''), d.x[j], d.x[j] + r.efecto_variables[j] * delta)));
    const u = unidad ? ` (${unidad})` : '';
    frase.textContent = `«${r.restriccion}» pasa de ${fmt(r.rhs)} a ${fmt(v)}${unidad ? ' ' + unidad : ''} (${delta >= 0 ? '+' : ''}${fmt(delta)}). ` +
      (r.precio_sombra === 0 ? 'Este recurso sobra: moverlo dentro de este rango no cambia Z.'
        : `Cada unidad adicional${u} ${r.precio_sombra > 0 ? 'sube' : 'baja'} Z en ${fmt(Math.abs(r.precio_sombra))}${d.unidad_z ? ' ' + d.unidad_z : ''}.`);
    rango.value = v;
    return {v, zNuevo};
  };
  const comprobar = async ({v, zNuevo}) => {
    const tk = QS = {};
    verif.className = 'wi-verif'; verif.textContent = 'Comprobando con el Simplex…';
    const c = copiar(cuerpo); c.restricciones[i].rhs = String(+v.toFixed(9));
    try {
      const resp = await fetch(main.dataset.apiUrl, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(c)});
      const data = await resp.json();
      if (tk !== QS) return;
      const ok = resp.ok && data.estado === 'optimo' && Math.abs(data.z - zNuevo) <= 1e-6 * Math.max(1, Math.abs(zNuevo));
      verif.className = 'wi-verif ' + (ok ? 'ok' : 'mal');
      verif.textContent = ok ? `✔ Verificado: al resolver de nuevo el problema, Z = ${fmt(data.z)}.`
        : `La comprobación dio otro valor (Z = ${resp.ok ? fmt(data.z) : '—'}); el valor está fuera del rango de validez.`;
    } catch (e) { if (tk === QS) { verif.className = 'wi-verif mal'; verif.textContent = 'No se pudo comprobar.'; } }
  };

  let ultimo = mover(r.rhs);
  verif.textContent = 'Este es el óptimo original.';
  rango.oninput = () => { ultimo = mover(Number(rango.value)); numero.value = fmt(ultimo.v); };
  rango.onchange = () => comprobar(ultimo);
  numero.onchange = () => { ultimo = mover(Number(numero.value)); numero.value = fmt(ultimo.v); comprobar(ultimo); };
  reset.onclick = () => { ultimo = mover(r.rhs); numero.value = fmt(r.rhs); QS = {}; verif.className = 'wi-verif'; verif.textContent = 'Este es el óptimo original.'; };

  $('wi-body').replaceChildren(
    el('div', {class: 'wi-control'},
      el('div', {class: 'wi-rango'}, el('span', {}, `mín ${fmt(lo)}`), rango, el('span', {}, topeVisual ? `${fmt(hi)}+` : `máx ${fmt(hi)}`)),
      el('div', {class: 'wi-valor'}, numero, el('span', {}, unidad || ''), reset)),
    fijo ? el('p', {class: 'muted'}, 'Este recurso no admite cambios sin alterar la base óptima.') : '',
    topeVisual ? el('p', {class: 'muted'}, 'Sin límite superior: el deslizador muestra hasta el doble del valor actual.') : '',
    salida, frase, verif);
}

/* ───────── mostrar resultados ───────── */
function mostrar(d, cuerpo) {
  detener();
  const optimo = d.estado === 'optimo';
  $('result').hidden = $('interp').hidden = $('steps').hidden = false;
  $('sens').hidden = !optimo;
  $('path').hidden = !optimo;
  $('whatif').hidden = !optimo;
  $('dual').hidden = !optimo;
  if (optimo) { prepararQueSi(d, cuerpo); mostrarDual(d); }
  const stats = $('stats');
  stats.replaceChildren();
  let confetiEn = null;
  if (optimo) {
    const fuerte = el('strong', {}, '0');
    const big = el('div', {class: 'stat big'}, el('small', {}, `Z* ${d.unidad_z}`.trim()), fuerte);
    stats.append(big);
    contar(fuerte, d.z);
    confetiEn = big;
  }
  stats.append(el('div', {class: 'stat'}, el('small', {}, 'Estado'), el('span', {class: 'badge' + (optimo ? '' : ' warn')}, optimo ? '● ÓPTIMO' : '● NO ACOTADO')));
  if (optimo) {
    d.variables.forEach((x, j) => stats.append(el('div', {class: 'stat'}, el('small', {}, x.nombre + (x.unidad ? ` (${x.unidad})` : '')), el('strong', {}, fmt(d.x[j])))));
    stats.append(el('div', {class: 'stat'}, el('small', {}, 'Iteraciones'), el('strong', {}, String(d.iterations.length - 1))));
  }
  $('interp-body').replaceChildren(...d.interpretacion.map((s, k) => {
    const esUltima = k === d.interpretacion.length - 1 && optimo;
    return el('div', {class: 'interp-sec' + (esUltima ? ' concl' : '')}, el('h3', {}, s.titulo),
      el('ul', {}, ...s.items.map(t => el('li', {}, t))));
  }));
  if (optimo) {
    tabla($('t-res'), ['Restricción', 'b', 'Holgura', 'Precio sombra', 'b mín', 'b máx'],
      d.sens_restricciones.map((s, i) => [s.restriccion, fmt(s.rhs), fmt(d.holguras[i]), fmt(s.precio_sombra), lim(s.minimo, '−∞'), lim(s.maximo, '∞')]),
      i => d.sens_restricciones[i].precio_sombra !== 0);
    tabla($('t-var'), ['Variable', 'Tipo', 'c', 'c mín', 'c máx', 'Costo reducido'],
      d.sens_variables.map(s => [s.variable, s.tipo, fmt(s.coeficiente), lim(s.minimo, '−∞'), lim(s.maximo, '∞'), fmt(s.costo_reducido)]));
  }
  $('modelo').textContent = d.modelo;
  const dets = d.iterations.map((paso, k) => {
    const det = el('details', {}, el('summary', {}, `Tabla ${k + 1} · ${paso.label}`));
    if (k === 0 || k === d.iterations.length - 1) det.open = true;
    const conRazon = !!paso.ratios;
    const t = el('table', {class: 'tableau'}, el('tr', {}, ...['Base', ...paso.columns, ...(conRazon ? ['LD ÷ col.'] : [])].map(n => el('th', {}, n))));
    const minimo = conRazon && paso.pivot ? paso.ratios[paso.pivot[0]] : null;
    paso.rows.forEach((fila, r) => {
      const ultima = r === paso.rows.length - 1;
      const celdas = fila.map((v, c) => el('td', {class: paso.pivot && paso.pivot[0] === r && paso.pivot[1] === c ? 'pivot' : ''}, fmt(v)));
      if (conRazon) {
        const q = ultima ? null : paso.ratios[r];
        celdas.push(el('td', {class: 'razon' + (q !== null && paso.pivot && paso.pivot[0] === r ? ' minima' : '')}, q === null ? '—' : fmt(q)));
      }
      t.append(el('tr', {}, el('th', {}, ultima ? 'Z' : paso.basis[r]), ...celdas));
    });
    if (paso.explicacion) det.append(el('p', {class: 'explica'}, el('b', {}, '¿Por qué? '), paso.explicacion));
    det.append(el('div', {class: 'scroll'}, t));
    return det;
  });
  $('tables').replaceChildren(...dets);
  if (optimo) { prepararRuta(d, cuerpo); R.dets = dets; irA(0, false); }
  else R = null;
  $('result').scrollIntoView({behavior: REDUCIR ? 'auto' : 'smooth', block: 'start'});
  if (confetiEn) setTimeout(() => confeti(confetiEn), 450);
}

$('solve').onclick = async () => {
  mostrarError('');
  const cuerpo = {
    sentido: model.sentido, unidad_z: model.unidad_z, contexto: model.contexto,
    variables: model.variables.map(x => ({nombre: x.nombre, unidad: x.unidad, costo: x.costo})),
    restricciones: model.restricciones.map(q => ({nombre: q.nombre, unidad: q.unidad, coefs: [...q.coefs], tipo: '<=', rhs: q.rhs})),
  };
  try {
    const resp = await fetch(main.dataset.apiUrl, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cuerpo)});
    const data = await resp.json();
    if (!resp.ok) throw Error(data.error || 'No se pudo calcular.');
    mostrar(data, cuerpo);
  } catch (e) { mostrarError(e.message); }
};

/* ───────── informe en PDF (impresión del navegador) ───────── */
let abiertos = null, pasoAntes = null, tituloOriginal = document.title;
$('print').onclick = () => window.print();
window.addEventListener('beforeprint', () => {
  const hoy = new Date();
  const grande = document.querySelector('#stats .stat.big strong');
  if (grande && grande.dataset.final) grande.textContent = grande.dataset.final;   // por si el contador seguía animando
  pasoAntes = null;
  if (R) {                                  // el informe muestra la ruta completa, hasta el óptimo
    detener(); pasoAntes = R.k; irA(R.estados.length - 1, false);
    if (R.n !== 2) $('path-box').style.display = 'none';
  }
  $('print-head').replaceChildren(el('h1', {}, 'Informe · Método Simplex'),
    el('p', {}, `Generado el ${hoy.toLocaleDateString('es-CO', {year: 'numeric', month: 'long', day: 'numeric'})} · OptiLab / USTA`));
  $('print-contexto').textContent = model.contexto.trim() || '(sin contexto)';
  const dets = [...document.querySelectorAll('#tables details')];
  abiertos = dets.map(d => d.open);
  dets.forEach(d => d.open = true);
  tituloOriginal = document.title;
  document.title = `Informe Simplex ${hoy.toISOString().slice(0, 10)}`;   // nombre sugerido del PDF
});
window.addEventListener('afterprint', () => {
  document.title = tituloOriginal;
  if (R && pasoAntes !== null) { $('path-box').style.display = ''; irA(pasoAntes, false); }
  if (abiertos) [...document.querySelectorAll('#tables details')].forEach((d, i) => d.open = abiertos[i]);
});

render();

/* ───────── enlaces directos: ?ejemplo=muebles&resolver=1 ───────── */
(function enlaceDirecto() {
  const q = new URLSearchParams(location.search), id = q.get('ejemplo');
  if (id && EJEMPLOS.some(e => e.id === id)) {
    $('ejemplos').value = id;
    $('ejemplos').dispatchEvent(new Event('change'));
    if (q.get('resolver') === '1') $('solve').click();
  }
})();
