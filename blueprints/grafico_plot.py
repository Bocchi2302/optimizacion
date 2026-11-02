# blueprints/grafico_plot.py
"""
Gráficas SVG del Método Gráfico, una por etapa del procedimiento.

Se dibuja en SVG para que la gráfica sea nítida, use los mismos colores que las
tablas y tarjetas, y se pueda animar e interactuar con CSS/JS:

* cada elemento de una restricción lleva `data-r="R1"` (resaltado al pasar el mouse),
* cada vértice lleva `data-p="x,y"` (se ilumina al señalarlo en una tabla),
* el <svg> expone los datos que necesita la recta de Z interactiva.
"""
import json
import math
from html import escape

from markupsafe import Markup

from .grafico_solver import cortes_con_ejes, fmt

# Los colores son variables CSS (--r0…--r11, --verde, --rosa, --tinta…): así las gráficas
# cambian solas entre modo claro y modo oscuro.
PALETA = [f'var(--r{i})' for i in range(12)]
COLOR_REGION = 'var(--verde)'
COLOR_OPTIMO = 'var(--rosa)'
COLOR_TINTA = 'var(--tinta)'

W, H = 680, 484
ML, MR, MT, MB = 58, 24, 36, 52

ETAPAS = ('rectas', 'semiplanos', 'semiplano', 'region', 'vertices', 'optimo')


def color_de(indice):
    return PALETA[indice % len(PALETA)]


def clave_punto(x, y):
    """Identificador de un vértice compartido por tablas y gráficas."""
    return f'{fmt(x)},{fmt(y)}'


# ── Utilidades ──────────────────────────────────────────────────────────────
def _paso_bonito(maximo, objetivo=6):
    """Paso 1·2·5×10ⁿ para que la cuadrícula tenga ~`objetivo` marcas."""
    bruto = maximo / objetivo
    magnitud = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * magnitud:
            return m * magnitud
    return 10 * magnitud


def _ventana(sol):
    """Rango visible (X, Y) que deja ver todos los vértices y las rectas."""
    vx = [float(e['x']) for e in sol['vertices']]
    vy = [float(e['y']) for e in sol['vertices']]
    base_x, base_y = max(vx, default=0.0), max(vy, default=0.0)

    cx, cy = [], []
    for r in sol['rectas']:
        c1, c2 = cortes_con_ejes(r)
        if c1 and c1[0] > 0:
            cx.append(float(c1[0]))
        if c2 and c2[1] > 0:
            cy.append(float(c2[1]))

    def elegir(base, cortes):
        if sol['acotada'] and base > 0:
            extra = [v for v in cortes if v <= 2 * base]
        else:
            extra = cortes
        return max([base] + extra) if (base or extra) else 10.0

    X, Y = elegir(base_x, cx), elegir(base_y, cy)
    return max(X, 1e-6) * 1.2, max(Y, 1e-6) * 1.2


class _Lienzo:
    def __init__(self, X, Y):
        self.X, self.Y = X, Y
        self.pw, self.ph = W - ML - MR, H - MT - MB

    def px(self, x):
        return ML + x / self.X * self.pw

    def py(self, y):
        return MT + self.ph - y / self.Y * self.ph

    def p(self, punto):
        return self.px(punto[0]), self.py(punto[1])


def _segmento_en_caja(a, b, c, X, Y):
    """Tramo visible de la recta ax+by=c dentro de [0,X]×[0,Y] (o None)."""
    puntos = []
    eps = 1e-9 * max(X, Y)
    if b != 0:
        for x in (0.0, X):
            y = (c - a * x) / b
            if -eps <= y <= Y + eps:
                puntos.append((x, min(max(y, 0.0), Y)))
    if a != 0:
        for y in (0.0, Y):
            x = (c - b * y) / a
            if -eps <= x <= X + eps:
                puntos.append((min(max(x, 0.0), X), y))
    if len(puntos) < 2:
        return None
    mejor = max(
        ((p, q) for i, p in enumerate(puntos) for q in puntos[i + 1:]),
        key=lambda pq: (pq[0][0] - pq[1][0]) ** 2 + (pq[0][1] - pq[1][1]) ** 2,
    )
    if mejor[0] == mejor[1]:
        return None
    return mejor


def _recortar(poligono, a, b, c, op, eps):
    """Sutherland–Hodgman: recorta un polígono con a·x+b·y (op) c."""
    def dentro(p):
        v = a * p[0] + b * p[1] - c
        return v <= eps if op == '<=' else v >= -eps

    def cruce(p, q):
        vp, vq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        t = vp / (vp - vq)
        return p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])

    salida = []
    for i, p in enumerate(poligono):
        q = poligono[(i + 1) % len(poligono)]
        if dentro(p):
            salida.append(p)
            if not dentro(q):
                salida.append(cruce(p, q))
        elif dentro(q):
            salida.append(cruce(p, q))
    return salida


def _region(sol, X, Y, solo=None):
    """Polígono factible (o del semiplano de `solo`) recortado a la ventana."""
    poligono = [(0.0, 0.0), (X, 0.0), (X, Y), (0.0, Y)]
    restricciones = [solo] if solo else sol['rectas']
    for r in restricciones:
        if not poligono:
            break
        a, b, c = float(r.a), float(r.b), float(r.c)
        eps = 1e-7 * (1 + abs(c))
        if r.op == '=':
            poligono = _recortar(poligono, a, b, c, '<=', eps)
            poligono = _recortar(poligono, a, b, c, '>=', eps) if poligono else []
        else:
            poligono = _recortar(poligono, a, b, c, r.op, eps)
    return poligono


def _dir_pantalla(lz, dx, dy):
    """Dirección unitaria en pantalla (eje Y invertido) de un vector de datos."""
    sx, sy = dx / lz.X * lz.pw, -dy / lz.Y * lz.ph
    norma = math.hypot(sx, sy)
    return (sx / norma, sy / norma) if norma else (0.0, 0.0)


def _flecha(lz, origen, dx, dy, color, largo=26, grosor=2.2, extra=''):
    """Flecha en pantalla que parte de `origen` (px) hacia (dx, dy) de datos."""
    ux, uy = _dir_pantalla(lz, dx, dy)
    if ux == uy == 0:
        return ''
    x0, y0 = origen
    x1, y1 = x0 + ux * largo, y0 + uy * largo
    ang = math.atan2(uy, ux)
    barbas = ''.join(
        f'M{x1:.1f},{y1:.1f}L{x1 - 7 * math.cos(ang + s):.1f},{y1 - 7 * math.sin(ang + s):.1f}'
        for s in (0.5, -0.5)
    )
    return (f'<path {extra} d="M{x0:.1f},{y0:.1f}L{x1:.1f},{y1:.1f}{barbas}" fill="none" '
            f'stroke="{color}" stroke-width="{grosor}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')


def _marca(valor):
    """Texto de una marca del eje sin errores de redondeo (0.075, no «0.08»; 0.3, no «0.30000000000000004»)."""
    valor = round(valor, 9)
    if abs(valor) >= 1e6:            # 2500000 → 2.5M: cabe en el margen del eje
        return f'{fmt(round(valor / 1e6, 6), 6)}M'
    if abs(valor) >= 1e5:
        return f'{fmt(round(valor / 1e3, 6), 6)}k'
    return fmt(valor, 6)


# ── Dibujo por capas ────────────────────────────────────────────────────────
def _fondo(lz):
    out = ['<g class="rejilla">']
    px_, py_ = _paso_bonito(lz.X), _paso_bonito(lz.Y)
    k = 0
    while k * px_ <= lz.X * 1.0001:
        x = lz.px(k * px_)
        out.append(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{MT + lz.ph}"/>')
        out.append(f'<text class="mx" x="{x:.1f}" y="{MT + lz.ph + 18}" text-anchor="middle">{_marca(k * px_)}</text>')
        k += 1
    k = 0
    while k * py_ <= lz.Y * 1.0001:
        y = lz.py(k * py_)
        out.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML + lz.pw}" y2="{y:.1f}"/>')
        out.append(f'<text class="my" x="{ML - 8}" y="{y + 4:.1f}" text-anchor="end">{_marca(k * py_)}</text>')
        k += 1
    out.append('</g>')
    out.append(
        f'<g class="ejes"><line x1="{ML}" y1="{MT + lz.ph}" x2="{ML + lz.pw}" y2="{MT + lz.ph}"/>'
        f'<line x1="{ML}" y1="{MT}" x2="{ML}" y2="{MT + lz.ph}"/>'
        f'<text class="et" x="{ML + lz.pw}" y="{MT + lz.ph + 38}" text-anchor="end">X1</text>'
        f'<text class="et" x="{ML + 10}" y="{MT - 12}" text-anchor="start">X2</text></g>'
    )
    return ''.join(out)


def _poligono_svg(lz, puntos, color, opacidad, clase='', borde=True, extra='', relleno=None):
    if len(puntos) < 2:
        return ''
    pts = ' '.join(f'{lz.px(x):.1f},{lz.py(y):.1f}' for x, y in puntos)
    trazo = f'stroke="{color}" stroke-width="3" stroke-linejoin="round"' if borde else 'stroke="none"'
    return (f'<polygon class="{clase}" {extra} points="{pts}" fill="{relleno or color}" '
            f'fill-opacity="{opacidad}" {trazo}/>')


def _rectas_svg(sol, lz, atenuar=False, solo=None):
    out = []
    for i, r in enumerate(sol['rectas']):
        if solo is not None and i != solo:
            continue
        seg = _segmento_en_caja(float(r.a), float(r.b), float(r.c), lz.X, lz.Y)
        if not seg:
            continue
        col = color_de(i)
        (x0, y0), (x1, y1) = lz.p(seg[0]), lz.p(seg[1])
        # Las igualdades van punteadas (y sin pathLength, que deformaría el punteado)
        dash = ' stroke-dasharray="7 5"' if r.op == '=' else ''
        clase = 'recta igual' if r.op == '=' else 'recta'
        largo = '' if r.op == '=' else ' pathLength="1"'
        coords = f'x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}"'
        out.append(
            f'<g data-r="{escape(r.nombre)}"><title>{escape(r.nombre)}: {escape(r.texto)}</title>'
            f'<line class="{clase}"{largo} style="animation-delay:{i * 0.12:.2f}s" {coords} stroke="{col}" '
            f'stroke-width="2.6" stroke-linecap="round" opacity="{0.55 if atenuar else 1}"{dash}/>'
            f'<line class="zona-toque" {coords} stroke="transparent" stroke-width="16"/></g>'
        )
    return ''.join(out)


def _etiquetas_svg(sol, lz, solo=None):
    out = []
    for i, r in enumerate(sol['rectas']):
        if solo is not None and i != solo:
            continue
        seg = _segmento_en_caja(float(r.a), float(r.b), float(r.c), lz.X, lz.Y)
        if not seg:
            continue
        col = color_de(i)
        (x0, y0), (x1, y1) = lz.p(seg[0]), lz.p(seg[1])
        t = 0.86 - 0.14 * (i % 3) if solo is None else 0.7
        lx, ly = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        ancho = 28 if len(r.nombre) <= 2 else 34
        # La píldora se dibuja alrededor de (0, 0) y se traslada: así el CSS puede agrandarla en celulares
        out.append(
            f'<g class="etiqueta" data-r="{escape(r.nombre)}" style="animation-delay:{0.5 + i * 0.12:.2f}s">'
            f'<g transform="translate({lx:.1f},{ly:.1f})"><g class="pildora">'
            f'<rect x="{-ancho / 2:.0f}" y="-20" width="{ancho}" height="17" rx="8.5" fill="{col}"/>'
            f'<text x="0" y="-7.5" text-anchor="middle" fill="var(--on-color)">{escape(r.nombre)}</text></g></g></g>'
        )
    return ''.join(out)


def _tinte_semiplano(sol, lz, indice, uid, fuerte=False):
    """Zona factible de una restricción: tinte de su color (rayado si `fuerte`)."""
    r = sol['rectas'][indice]
    if r.op == '=':
        return ''
    col = color_de(indice)
    zona = _region(sol, lz.X, lz.Y, solo=r)
    nombre = escape(r.nombre)
    capa = _poligono_svg(lz, zona, col, 0.16 if fuerte else 0.08, 'semiplano', borde=False,
                         extra=f'data-r="{nombre}"')
    if fuerte:
        capa += _poligono_svg(lz, zona, col, 1, 'semiplano rayado', borde=False,
                              extra=f'data-r="{nombre}"', relleno=f'url(#rayas-{uid}-{indice})')
    return capa


def _flechas_semiplano(sol, lz, solo=None):
    out = []
    for i, r in enumerate(sol['rectas']):
        if (solo is not None and i != solo) or r.op == '=':
            continue
        seg = _segmento_en_caja(float(r.a), float(r.b), float(r.c), lz.X, lz.Y)
        if not seg:
            continue
        signo = -1 if r.op == '<=' else 1
        for t in ((0.5,) if solo is None else (0.25, 0.5, 0.75)):
            mx = seg[0][0] + (seg[1][0] - seg[0][0]) * t
            my = seg[0][1] + (seg[1][1] - seg[0][1]) * t
            out.append(_flecha(lz, lz.p((mx, my)), signo * float(r.a), signo * float(r.b),
                               color_de(i), largo=24, grosor=2.4,
                               extra=f'class="flecha-semi" data-r="{escape(r.nombre)}"'))
    return ''.join(out)


def _definiciones(sol, lz, uid, indices):
    """Recorte al área de dibujo y tramas rayadas por color."""
    rayas = ''.join(
        f'<pattern id="rayas-{uid}-{i}" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="9" stroke="{color_de(i)}" stroke-width="2.2" stroke-opacity=".45"/></pattern>'
        for i in indices
    )
    return (f'<defs><clipPath id="{uid}"><rect x="{ML}" y="{MT}" width="{lz.pw}" height="{lz.ph}"/></clipPath>'
            f'{rayas}</defs>')


def _pos_etiqueta(lz, x, y, sep=8):
    """Posición y anclaje de la etiqueta de un punto: se voltea cerca del borde derecho o superior."""
    derecha = x > ML + lz.pw * 0.8
    arriba = y < MT + 22
    tx = x - sep if derecha else x + sep
    ty = y + sep + 12 if arriba else y - sep
    return tx, ty, 'end' if derecha else 'start'


def _vertices_svg(sol, lz, optimos=()):
    out = []
    for n, e in enumerate(sol['vertices']):
        if any(e is o for o in optimos):
            continue
        x, y = lz.px(float(e['x'])), lz.py(float(e['y']))
        tx, ty, ancla = _pos_etiqueta(lz, x, y)
        out.append(
            f'<g class="vertice" data-p="{clave_punto(e["x"], e["y"])}" style="animation-delay:{0.15 * n:.2f}s">'
            f'<title>Vértice ({fmt(e["x"])}, {fmt(e["y"])}) · Z = {fmt(e["z"])}</title>'
            f'<circle class="anillo" cx="{x:.1f}" cy="{y:.1f}" r="11" fill="none"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="var(--tarjeta)" stroke="{COLOR_TINTA}" stroke-width="2"/>'
            f'<text class="coord" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{ancla}">({fmt(e["x"], 2)}, {fmt(e["y"], 2)})</text></g>'
        )
    return ''.join(out)


def _estrella(cx, cy, radio=11):
    pts = []
    for k in range(10):
        r = radio if k % 2 == 0 else radio * 0.45
        ang = -math.pi / 2 + k * math.pi / 5
        pts.append(f'{cx + r * math.cos(ang):.1f},{cy + r * math.sin(ang):.1f}')
    return ' '.join(pts)


def _optimos_svg(sol, lz):
    out = []
    for n, e in enumerate(sol['optimos']):
        x, y = lz.px(float(e['x'])), lz.py(float(e['y']))
        tx, ty, ancla = _pos_etiqueta(lz, x, y, sep=13)
        out.append(
            f'<g class="optimo" data-p="{clave_punto(e["x"], e["y"])}" style="animation-delay:{0.2 * n:.2f}s">'
            f'<title>Óptimo ({fmt(e["x"])}, {fmt(e["y"])}) · Z = {fmt(e["z"])}</title>'
            f'<circle class="pulso" cx="{x:.1f}" cy="{y:.1f}" r="12" fill="none" stroke="var(--dorado)" stroke-width="2.4"/>'
            f'<polygon class="estrella" points="{_estrella(x, y)}" fill="var(--dorado)" stroke="{COLOR_TINTA}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<text class="coord fuerte" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{ancla}">({fmt(e["x"], 2)}, {fmt(e["y"], 2)})</text></g>'
        )
    return ''.join(out)


def _isolineas_svg(sol, lz):
    """Rectas de nivel Z = k: la del óptimo resaltada (con barrido) y las demás tenues."""
    zx, zy = float(sol['zx']), float(sol['zy'])
    if zx == 0 and zy == 0:
        return ''
    out = []
    optimos_z = {e['z'] for e in sol['optimos']}
    signo = 1 if sol['tipo'] == 'max' else -1
    ux, uy = _dir_pantalla(lz, signo * zx, signo * zy)
    for z in sorted({e['z'] for e in sol['vertices']}):
        es_opt = z in optimos_z
        seg = _segmento_en_caja(zx, zy, float(z - sol['zk']), lz.X, lz.Y)
        if not seg:
            continue
        (x0, y0), (x1, y1) = lz.p(seg[0]), lz.p(seg[1])
        if es_opt:
            # La recta entra desde el lado «peor» y se desliza hasta el óptimo
            out.append(
                f'<g class="iso-barrido" style="--dx:{-ux * 170:.0f}px;--dy:{-uy * 170:.0f}px">'
                f'<line class="iso fuerte" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                f'stroke="{COLOR_OPTIMO}" stroke-width="2.6" stroke-dasharray="3 6" stroke-linecap="round"/></g>')
        else:
            out.append(f'<line class="iso" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
                       f'stroke="{COLOR_TINTA}" stroke-opacity=".28" stroke-width="1.4" stroke-dasharray="3 6"/>')
    return ''.join(out)


def _leyenda_mejora(sol, lz):
    zx, zy = float(sol['zx']), float(sol['zy'])
    if zx == 0 and zy == 0:
        return ''
    signo = 1 if sol['tipo'] == 'max' else -1
    # En el margen superior derecho, fuera del área de dibujo: no tapa vértices ni rectas
    ux, uy = _dir_pantalla(lz, signo * zx, signo * zy)
    cx, cy, largo = ML + lz.pw - 14, MT / 2, 24
    origen = (cx - ux * largo / 2, cy - uy * largo / 2)
    return (f'<g class="leyenda-mejora"><text class="leyenda-z" x="{cx - 22:.1f}" y="{cy + 4:.1f}" '
            f'text-anchor="end" fill="{COLOR_OPTIMO}">mejora de Z</text>'
            + _flecha(lz, origen, signo * zx, signo * zy, COLOR_OPTIMO, largo=largo, grosor=3) + '</g>')


def _datos_z(sol, lz):
    """Atributos data-* para la recta de Z interactiva."""
    esquinas = [sol['zx'] * x + sol['zy'] * y + sol['zk']
                for x in (0, lz.X) for y in (0, lz.Y)]
    # lz.X/lz.Y son float; Fraction*float da float, suficiente para el deslizador
    lo = '' if sol['z_lo'] is None else f'{float(sol["z_lo"]):.10g}'
    hi = '' if sol['z_hi'] is None else f'{float(sol["z_hi"]):.10g}'
    optimo = f'{float(sol["optimos"][0]["z"]):.10g}' if sol['optimos'] else ''
    return (f'data-xmax="{lz.X:.10g}" data-ymax="{lz.Y:.10g}" data-zx="{float(sol["zx"]):.10g}" '
            f'data-zy="{float(sol["zy"]):.10g}" data-zk="{float(sol["zk"]):.10g}" '
            f'data-zlo="{lo}" data-zhi="{hi}" data-zopt="{optimo}" '
            f'data-zmin="{float(min(esquinas)):.10g}" data-zmax="{float(max(esquinas)):.10g}" '
            f'data-tipo="{sol["tipo"]}"')


def _geometria(sol, lz, etapa, solo):
    """
    Datos para el explorador de la gráfica (JS): escala, restricciones y vértices.
    Con ellos el navegador dice, para cualquier punto que se señale, si es factible y cuánto vale Z.
    """
    rectas = [[float(r.a), float(r.b), r.op, float(r.c), r.nombre, i]
              for i, r in enumerate(sol['rectas'])]
    datos = {
        'etapa': etapa, 'X': lz.X, 'Y': lz.Y, 'ml': ML, 'mt': MT, 'pw': lz.pw, 'ph': lz.ph,
        'rectas': rectas if solo is None else [rectas[solo]],
        'contradiccion': sol['contradiccion'] is not None,
        'z': [float(sol['zx']), float(sol['zy']), float(sol['zk'])], 'tipo': sol['tipo'],
        'vertices': [[float(e['x']), float(e['y']), fmt(e['x']), fmt(e['y']), fmt(e['z']), e['optimo']]
                     for e in sol['vertices']] if etapa in ('vertices', 'optimo') else [],
    }
    return json.dumps(datos, ensure_ascii=False, separators=(',', ':'))


# ── API pública ─────────────────────────────────────────────────────────────
def graficar(sol, etapa, descripcion='', solo=None):
    """
    SVG de una etapa del procedimiento (Markup listo para plantilla).
    `solo` (índice de restricción) se usa en la etapa «semiplano».
    """
    if etapa not in ETAPAS:
        raise ValueError(etapa)
    X, Y = _ventana(sol)
    lz = _Lienzo(X, Y)
    uid = f'recorte-{etapa}-{"x" if solo is None else solo}'
    indices = range(len(sol['rectas'])) if solo is None else [solo]
    region = _region(sol, X, Y) if sol['factible'] else []

    # Capas recortadas al área de dibujo
    dentro = []
    if etapa == 'semiplanos':
        dentro += [_tinte_semiplano(sol, lz, i, uid) for i in indices]
    if etapa == 'semiplano':
        dentro.append(_tinte_semiplano(sol, lz, solo, uid, fuerte=True))
    if etapa in ('region', 'vertices', 'optimo') and region:
        dentro.append(_poligono_svg(lz, region, COLOR_REGION, 0.22, 'region'))
    dentro.append(_rectas_svg(sol, lz, atenuar=etapa in ('vertices', 'optimo'), solo=solo))
    if etapa in ('semiplanos', 'semiplano'):
        dentro.append(_flechas_semiplano(sol, lz, solo=solo))
    if etapa == 'optimo':
        dentro.append(_isolineas_svg(sol, lz))
        dentro.append('<line class="iso-movil" id="iso-movil" x1="0" y1="0" x2="0" y2="0" '
                      f'stroke="{COLOR_TINTA}" stroke-width="3" stroke-linecap="round" opacity="0"/>')

    # Capas que pueden salirse un poco (etiquetas, puntos)
    fuera = [_etiquetas_svg(sol, lz, solo=solo)]
    if etapa in ('vertices', 'optimo'):
        fuera.append(_vertices_svg(sol, lz, sol['optimos'] if etapa == 'optimo' else ()))
    if etapa == 'optimo':
        fuera.append(_optimos_svg(sol, lz))
        fuera.append(_leyenda_mejora(sol, lz))

    extra = _datos_z(sol, lz) if etapa == 'optimo' else ''
    extra += f' data-geo="{escape(_geometria(sol, lz, etapa, solo), quote=True)}"'
    titulo = escape(descripcion or f'Gráfica: {etapa}')
    clase = 'grafica-svg mini' if etapa == 'semiplano' else 'grafica-svg'
    return Markup(
        f'<svg class="{clase}" viewBox="0 0 {W} {H}" role="img" aria-label="{titulo}" {extra} '
        f'xmlns="http://www.w3.org/2000/svg">{_definiciones(sol, lz, uid, indices)}{_fondo(lz)}'
        f'<g clip-path="url(#{uid})">{"".join(dentro)}</g>{"".join(fuera)}</svg>'
    )
