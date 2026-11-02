# blueprints/grafico_solver.py
"""
Lógica del Método Gráfico (2 variables) con aritmética exacta (Fraction).

No depende de Flask ni de matplotlib: recibe el problema ya validado y devuelve
un diccionario `Solucion` con todo lo necesario para explicar el procedimiento
paso a paso (cortes con los ejes, semiplanos, vértices, evaluación de Z, etc.).
"""
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

MAX_RESTRICCIONES = 12
OPERADORES = ('<=', '>=', '=')
SIMBOLO = {'<=': '≤', '>=': '≥', '=': '='}

_NUMERO = re.compile(r'^[+-]?(\d+([.]\d+)?|[.]\d+)(/\d+)?$')


class EntradaInvalida(ValueError):
    """Error de validación con un mensaje pensado para mostrarse al usuario."""


def parse_numero(texto, campo):
    """Convierte '2.5', '2,5' o '5/2' en Fraction; rechaza cualquier otra cosa."""
    limpio = (texto or '').strip().replace(',', '.')
    if not limpio:
        raise EntradaInvalida(f'Falta un valor en {campo}.')
    if len(limpio) > 15 or not _NUMERO.match(limpio):
        raise EntradaInvalida(f'«{texto}» no es un número válido en {campo}.')
    try:
        valor = Fraction(limpio)
    except ZeroDivisionError:
        raise EntradaInvalida(f'División entre cero en {campo}.')
    if abs(valor) > 10**9:
        raise EntradaInvalida(f'El valor de {campo} es demasiado grande.')
    return valor


# ── Formato de números ──────────────────────────────────────────────────────
def fmt(valor, decimales=4):
    """Entero si es exacto; si no, decimal recortado (sin ceros sobrantes)."""
    valor = Fraction(valor)
    if valor.denominator == 1:
        return str(valor.numerator)
    texto = f'{float(valor):.{decimales}f}'.rstrip('0').rstrip('.')
    return '0' if texto in ('-0', '') else texto


def fmt_exacto(valor):
    """'7/3 ≈ 2.3333' para fracciones no enteras; entero en otro caso."""
    valor = Fraction(valor)
    if valor.denominator == 1:
        return str(valor.numerator)
    return f'{valor.numerator}/{valor.denominator} ≈ {fmt(valor)}'


def _coef(valor, variable, primero):
    """Término 'a·X' bien escrito: '+ 3X1', '- X2', omite coeficientes 0."""
    if valor == 0:
        return ''
    signo = '-' if valor < 0 else '+'
    absoluto = abs(valor)
    cuerpo = variable if absoluto == 1 else f'{fmt(absoluto)}{variable}'
    if primero:
        return f'-{cuerpo}' if valor < 0 else cuerpo
    return f' {signo} {cuerpo}'


def expresion(a, b, k=0):
    """'3X1 + 2X2 + 5' (o '0' si todo es 0)."""
    texto = _coef(a, 'X1', True)
    texto += _coef(b, 'X2', texto == '')
    if k:
        texto += f' {"-" if k < 0 else "+"} {fmt(abs(k))}' if texto else fmt(k)
    return texto or '0'


# ── Modelo ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Restriccion:
    nombre: str
    a: Fraction
    b: Fraction
    op: str
    c: Fraction
    implicita: bool = False  # True para X1 ≥ 0 y X2 ≥ 0
    rotulo: str = ''         # qué limita (p. ej. «horas de carpintería»); opcional

    @property
    def texto(self):
        return f'{expresion(self.a, self.b)} {SIMBOLO[self.op]} {fmt(self.c)}'

    @property
    def ecuacion(self):
        return f'{expresion(self.a, self.b)} = {fmt(self.c)}'

    def valor(self, x, y):
        return self.a * x + self.b * y

    def cumple(self, x, y):
        v = self.valor(x, y)
        if self.op == '<=':
            return v <= self.c
        if self.op == '>=':
            return v >= self.c
        return v == self.c

    def cumple_direccion(self, dx, dy):
        """¿La dirección (dx, dy) mantiene factible a lo largo de un rayo?"""
        v = self.a * dx + self.b * dy
        if self.op == '<=':
            return v <= 0
        if self.op == '>=':
            return v >= 0
        return v == 0


def leer_problema(form):
    """
    Lee y valida el formulario. Devuelve un dict con tipo, objetivo y
    restricciones; lanza EntradaInvalida con un mensaje claro si algo falla.
    """
    tipo = form.get('tipo_opt', 'max')
    if tipo not in ('max', 'min'):
        raise EntradaInvalida('El tipo de optimización debe ser maximizar o minimizar.')

    zx = parse_numero(form.get('z_x'), 'la función objetivo (X1)')
    zy = parse_numero(form.get('z_y'), 'la función objetivo (X2)')
    zk = parse_numero(form.get('z_k') or '0', 'la constante de la función objetivo')

    xs, ys = form.getlist('r_x[]'), form.getlist('r_y[]')
    ops, cs = form.getlist('r_op[]'), form.getlist('r_c[]')
    if not (len(xs) == len(ys) == len(ops) == len(cs)):
        raise EntradaInvalida('Las restricciones llegaron incompletas.')
    if not xs:
        raise EntradaInvalida('Agrega al menos una restricción.')
    if len(xs) > MAX_RESTRICCIONES:
        raise EntradaInvalida(f'El máximo es {MAX_RESTRICCIONES} restricciones.')

    rotulos = form.getlist('r_n[]')
    rotulos += [''] * (len(xs) - len(rotulos))
    restricciones = []
    for i, (x, y, op, c) in enumerate(zip(xs, ys, ops, cs), start=1):
        if op not in OPERADORES:
            raise EntradaInvalida(f'Operador inválido en la restricción R{i}.')
        restricciones.append(Restriccion(
            f'R{i}',
            parse_numero(x, f'R{i} (coeficiente de X1)'),
            parse_numero(y, f'R{i} (coeficiente de X2)'),
            op,
            parse_numero(c, f'R{i} (lado derecho)'),
            rotulo=' '.join((rotulos[i - 1] or '').split())[:80],
        ))

    return {
        'tipo': tipo,
        'zx': zx,
        'zy': zy,
        'zk': zk,
        'nombres': [' '.join((form.get(f'nombre_x{i}') or '').split())[:60] for i in (1, 2)],
        'objetivo_nombre': ' '.join((form.get('objetivo_nombre') or '').split())[:80],
        'contexto': (form.get('contexto') or '').strip()[:8000],
        'restricciones': restricciones,
    }


# ── Geometría exacta ────────────────────────────────────────────────────────
def interseccion(r1, r2):
    """Punto donde se cortan dos rectas, o None si son paralelas/coincidentes."""
    det = r1.a * r2.b - r2.a * r1.b
    if det == 0:
        return None, det
    x = (r1.c * r2.b - r2.c * r1.b) / det
    y = (r1.a * r2.c - r2.a * r1.c) / det
    return (x, y), det


def cortes_con_ejes(r):
    """Cortes de a·X1 + b·X2 = c con X1 (X2=0) y con X2 (X1=0); None si no hay."""
    corte_x1 = (r.c / r.a, Fraction(0)) if r.a != 0 else None
    corte_x2 = (Fraction(0), r.c / r.b) if r.b != 0 else None
    return corte_x1, corte_x2


def _direcciones_candidatas(restricciones):
    """Direcciones donde puede estar un rayo extremo de la región factible."""
    dirs = {(Fraction(1), Fraction(0)), (Fraction(0), Fraction(1))}
    for r in restricciones:
        if r.a == 0 and r.b == 0:
            continue
        dirs.add((r.b, -r.a))
        dirs.add((-r.b, r.a))
    return [
        d for d in dirs
        if d[0] >= 0 and d[1] >= 0 and (d[0] > 0 or d[1] > 0)
    ]


def _rayos_validos(restricciones):
    return [
        d for d in _direcciones_candidatas(restricciones)
        if all(r.cumple_direccion(*d) for r in restricciones)
    ]


def _poligono_ordenado(puntos):
    """Ordena los vértices (región convexa) en sentido antihorario."""
    if len(puntos) < 3:
        return list(puntos)
    cx = sum(float(p[0]) for p in puntos) / len(puntos)
    cy = sum(float(p[1]) for p in puntos) / len(puntos)
    return sorted(puntos, key=lambda p: math.atan2(float(p[1]) - cy, float(p[0]) - cx))


# ── Resolución ──────────────────────────────────────────────────────────────
def resolver(problema):
    """Ejecuta el método gráfico completo y devuelve todos los datos de cada paso."""
    tipo, zx, zy, zk = problema['tipo'], problema['zx'], problema['zy'], problema['zk']
    usuario = problema['restricciones']

    # Restricciones triviales (0·X1 + 0·X2 ? c): no son rectas.
    triviales, rectas = [], []
    for r in usuario:
        (triviales if r.a == 0 and r.b == 0 else rectas).append(r)
    contradiccion = next((r for r in triviales if not r.cumple(0, 0)), None)

    no_neg = [
        Restriccion('X1 ≥ 0', Fraction(1), Fraction(0), '>=', Fraction(0), True),
        Restriccion('X2 ≥ 0', Fraction(0), Fraction(1), '>=', Fraction(0), True),
    ]
    todas = rectas + no_neg

    # Todas las intersecciones entre pares de rectas
    candidatos = []
    paralelas = []
    for r1, r2 in combinations(todas, 2):
        punto, det = interseccion(r1, r2)
        if punto is None:
            paralelas.append((r1, r2))
            continue
        violadas = [r.nombre for r in todas if not r.cumple(*punto)]
        candidatos.append({
            'r1': r1, 'r2': r2, 'det': det, 'x': punto[0], 'y': punto[1],
            'factible': not violadas and contradiccion is None,
            'violadas': violadas,
        })

    # Vértices factibles únicos (varias parejas pueden dar el mismo punto)
    vertices = []
    for cand in candidatos:
        if not cand['factible']:
            continue
        p = (cand['x'], cand['y'])
        existente = next((v for v in vertices if v['punto'] == p), None)
        if existente:
            existente['rectas'].update((cand['r1'].nombre, cand['r2'].nombre))
        else:
            vertices.append({'punto': p, 'rectas': {cand['r1'].nombre, cand['r2'].nombre}})
    vertices.sort(key=lambda v: (v['punto'][0], v['punto'][1]))

    rayos = _rayos_validos(rectas) if contradiccion is None else []
    factible = bool(vertices)
    acotada = factible and not rayos

    # ¿Z mejora indefinidamente? ¿hay rayo con Z constante?
    signo = 1 if tipo == 'max' else -1
    rayo_mejora = next((d for d in rayos if signo * (zx * d[0] + zy * d[1]) > 0), None)
    rayo_neutro = next((d for d in rayos if zx * d[0] + zy * d[1] == 0), None)

    evaluaciones = []
    for v in vertices:
        x, y = v['punto']
        evaluaciones.append({
            'x': x, 'y': y, 'z': zx * x + zy * y + zk,
            'rectas': sorted(v['rectas']),
        })

    estado = 'optimo'
    optimos = []
    if not factible:
        estado = 'infactible'
    elif rayo_mejora is not None:
        estado = 'no_acotado'
    else:
        mejor = max(e['z'] for e in evaluaciones) if tipo == 'max' else min(e['z'] for e in evaluaciones)
        optimos = [e for e in evaluaciones if e['z'] == mejor]
        for e in evaluaciones:
            e['optimo'] = e['z'] == mejor
    for e in evaluaciones:
        e.setdefault('optimo', False)

    # Rango de valores de Z que alcanza la región (None = sin límite por ese lado)
    z_lo = z_hi = None
    if factible:
        zs = [e['z'] for e in evaluaciones]
        con_signo = [zx * d[0] + zy * d[1] for d in rayos]
        z_hi = None if any(v > 0 for v in con_signo) else max(zs)
        z_lo = None if any(v < 0 for v in con_signo) else min(zs)

    multiples = estado == 'optimo' and (len(optimos) > 1 or rayo_neutro is not None)

    return {
        'tipo': tipo, 'zx': zx, 'zy': zy, 'zk': zk,
        'nombres': problema['nombres'],
        'objetivo_nombre': problema.get('objetivo_nombre', ''),
        'contexto': problema['contexto'],
        'usuario': usuario,
        'rectas': rectas,
        'triviales': triviales,
        'contradiccion': contradiccion,
        'no_neg': no_neg,
        'todas': todas,
        'candidatos': candidatos,
        'paralelas': paralelas,
        'vertices': evaluaciones,
        'poligono': _poligono_ordenado([(e['x'], e['y']) for e in evaluaciones]),
        'rayos': rayos,
        'rayo_mejora': rayo_mejora,
        'rayo_neutro': rayo_neutro,
        'factible': factible,
        'acotada': acotada,
        'estado': estado,
        'optimos': optimos,
        'multiples': multiples,
        'z_lo': z_lo,
        'z_hi': z_hi,
    }
