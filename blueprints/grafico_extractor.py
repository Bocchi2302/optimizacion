# blueprints/grafico_extractor.py
"""
Lee el enunciado de un ejercicio de programación lineal y saca de él el modelo:
variables, función objetivo y restricciones.

Funciona sin internet y de forma determinista: entiende modelos escritos en texto
plano, Unicode o LaTeX («Maximizar Z = 3x + 5y, sujeto a 2x + y \\leq 8 …»).
Todo lo extraído se valida con las mismas reglas que el formulario, y la persona
lo revisa antes de resolver.
"""
import re
from fractions import Fraction

from .grafico_solver import (
    OPERADORES, SIMBOLO, EntradaInvalida, expresion, fmt, parse_numero,
)

MAX_TEXTO = 8000


class ErrorExtraccion(Exception):
    """No se pudo entender el enunciado; el mensaje se muestra a la persona."""


# ═══════════════════════════════════════════════════════════════════════════
#  Normalización de texto (plano, Unicode y LaTeX → una sola notación)
# ═══════════════════════════════════════════════════════════════════════════
_UNICODE = str.maketrans({
    '−': '-', '–': '-', '—': '-', '‒': '-', '➖': '-',
    '×': '*', '·': '*', '⋅': '*', '∙': '*', '✕': '*',
    '≤': '<=', '⩽': '<=', '≦': '<=', '≥': '>=', '⩾': '>=', '≧': '>=',
    '＝': '=', '＋': '+', '（': '(', '）': ')',
    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
    '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
    '½': '(1/2)', '¼': '(1/4)', '¾': '(3/4)', '⅓': '(1/3)', '⅔': '(2/3)',
})

_MARCADORES = re.compile(
    r'(sujeto\s+a(?:\s+las\s+siguientes\s+restricciones)?|subject\s+to|such\s+that|'
    r'tal(?:es)?\s+que|con\s+las\s+(?:siguientes\s+)?restricciones|'
    r'restricciones|constraints|\bs\s*\.\s*a\s*\.?(?=\s|:|$)|\bs\s*\.\s*t\s*\.?(?=\s|:|$)|'
    # «st» / «sa» sin puntos, solo si les sigue una expresión («max 3a+2b st a+b<=4»)
    r'\b(?:st|sa)\b(?=\s*:?\s*[-+(]?\s*(?:\d+(?:\.\d+)?\s*\*?\s*)?[A-Za-z]\d*\s*[-+*/<>=]))\s*:?',
    re.I,
)
_PREFIJO_LINEA = re.compile(
    r'^\s*(?:[-•*▪●]\s+|\(?\d{1,2}[\).:]\s+|\(?[A-Za-z][\)]\s+|'
    r'(?:[Rr]\s?\d+|restricci[oó]n\s*\d*)\s*[:.)]\s*)'
)


def _llaves_latex(s):
    # \frac{a}{b} → ((a)/(b)), repetido para fracciones anidadas
    previo = None
    while previo != s:
        previo = s
        s = re.sub(r'\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'((\1)/(\2))', s)
    return s


def normalizar(texto):
    s = texto.translate(_UNICODE)

    # ── LaTeX ──
    s = re.sub(r'\\begin\{[^}]*\}|\\end\{[^}]*\}', ' ', s)
    s = s.replace('\\\\', '\n')
    s = re.sub(r'\\\(|\\\)|\\\[|\\\]|\$', ' ', s)
    s = re.sub(r'\\left|\\right|\\displaystyle', '', s)
    s = _llaves_latex(s)
    s = re.sub(r'\\(?:text|textbf|mathrm|mathbf|operatorname)\s*\{([^{}]*)\}', r' \1 ', s)
    s = re.sub(r'\\le(?:q|qslant)?(?![A-Za-z])', '<=', s)
    s = re.sub(r'\\ge(?:q|qslant)?(?![A-Za-z])', '>=', s)
    s = re.sub(r'\\(?:cdot|times|ast)(?![A-Za-z])', '*', s)
    s = re.sub(r'_\{(\w+)\}', r'\1', s)
    s = re.sub(r'_(\w)', r'\1', s)
    s = re.sub(r'\\(?:quad|qquad|,|;|:|!| )', ' ', s)
    s = re.sub(r'\\(max|min)(?![A-Za-z])', r' \1 ', s)
    s = re.sub(r'\\[A-Za-z]+', ' ', s)          # cualquier otro comando
    s = s.replace('{', '').replace('}', '').replace('&', ' ')

    # ── Relaciones escritas de otras formas ──
    s = s.replace('=<', '<=').replace('=>', '>=').replace('==', '=')
    s = re.sub(r'menor\s+o\s+igual\s+(?:a|que)?', ' <= ', s, flags=re.I)
    s = re.sub(r'mayor\s+o\s+igual\s+(?:a|que)?', ' >= ', s, flags=re.I)
    s = re.sub(r'less\s+than\s+or\s+equal\s+to', ' <= ', s, flags=re.I)
    s = re.sub(r'greater\s+than\s+or\s+equal\s+to', ' >= ', s, flags=re.I)
    s = re.sub(r'\bigual\s+a\b', ' = ', s, flags=re.I)
    numero_siguiente = r'(?=\s*[-+(]?\s*\.?\d)'
    s = re.sub(r'(?:como\s+m[aá]ximo|a\s+lo\s+sumo|no\s+m[aá]s\s+de|no\s+(?:excede|supera)\s+(?:de|a)?|m[aá]ximo\s+de)\s*' + numero_siguiente, ' <= ', s, flags=re.I)
    s = re.sub(r'(?:al\s+menos|por\s+lo\s+menos|como\s+m[ií]nimo|no\s+menos\s+de|m[ií]nimo\s+de)\s*' + numero_siguiente, ' >= ', s, flags=re.I)
    s = re.sub(r'\bexactamente\s*' + numero_siguiente, ' = ', s, flags=re.I)
    s = re.sub(r'<(?![=])', '<=', s)             # estrictas → no estrictas (se avisa)
    s = re.sub(r'(?<![<])>(?![=])', '>=', s)
    s = re.sub(r'(?<=\d),(?=\d)', '.', s)         # coma decimal
    return s


# ═══════════════════════════════════════════════════════════════════════════
#  Expresiones lineales exactas
# ═══════════════════════════════════════════════════════════════════════════
class Lineal:
    """a·v1 + b·v2 + … + k con coeficientes exactos."""

    def __init__(self, coefs=None, k=Fraction(0)):
        self.c = {v: q for v, q in (coefs or {}).items() if q != 0}
        self.k = Fraction(k)

    @property
    def constante(self):
        return not self.c

    def mas(self, otro, signo=1):
        c = dict(self.c)
        for v, q in otro.c.items():
            c[v] = c.get(v, Fraction(0)) + signo * q
        return Lineal(c, self.k + signo * otro.k)

    def por(self, otro):
        if self.constante:
            return Lineal({v: q * self.k for v, q in otro.c.items()}, otro.k * self.k)
        if otro.constante:
            return Lineal({v: q * otro.k for v, q in self.c.items()}, self.k * otro.k)
        raise ErrorExtraccion('Hay un producto entre variables (por ejemplo x·y o x²): el modelo no es lineal.')

    def entre(self, otro):
        if not otro.constante or otro.k == 0:
            raise ErrorExtraccion('Solo se puede dividir entre un número distinto de cero.')
        return Lineal({v: q / otro.k for v, q in self.c.items()}, self.k / otro.k)


_TOKEN = re.compile(r'\s*(?:(\d+\.\d+|\d+|\.\d+)|([A-Za-z]\d*)(?![A-Za-z])|([-+*/()]))')


def _tokenizar(texto):
    pos, tokens, texto = 0, [], texto.strip()
    while pos < len(texto):
        m = _TOKEN.match(texto, pos)
        if not m:
            raise ErrorExtraccion(f'No entendí «{texto[pos:pos + 12].strip()}» dentro de una expresión.')
        num, var, op = m.groups()
        tokens.append(('n', Fraction(num)) if num else ('v', var) if var else ('o', op))
        pos = m.end()
    return tokens


def parsear_lineal(texto):
    tokens = _tokenizar(texto)
    if not tokens:
        raise ErrorExtraccion('Expresión vacía.')
    pos = 0

    def ver():
        return tokens[pos] if pos < len(tokens) else (None, None)

    def expr():
        nonlocal pos
        valor = termino()
        while ver() in (('o', '+'), ('o', '-')):
            signo = 1 if tokens[pos][1] == '+' else -1
            pos += 1
            valor = valor.mas(termino(), signo)
        return valor

    def termino():
        nonlocal pos
        valor = factor()
        while True:
            tipo, dato = ver()
            if (tipo, dato) == ('o', '*'):
                pos += 1
                valor = valor.por(factor())
            elif (tipo, dato) == ('o', '/'):
                pos += 1
                valor = valor.entre(factor())
            elif tipo in ('n', 'v') or (tipo, dato) == ('o', '('):
                valor = valor.por(factor())          # multiplicación implícita: 3x, 2(x+y)
            else:
                return valor

    def factor():
        nonlocal pos
        tipo, dato = ver()
        if (tipo, dato) in (('o', '+'), ('o', '-')):
            pos += 1
            f = factor()
            return f.por(Lineal(k=-1)) if dato == '-' else f
        if tipo == 'n':
            pos += 1
            return Lineal(k=dato)
        if tipo == 'v':
            pos += 1
            return Lineal({dato.lower(): Fraction(1)})
        if (tipo, dato) == ('o', '('):
            pos += 1
            v = expr()
            if ver() != ('o', ')'):
                raise ErrorExtraccion('Falta cerrar un paréntesis.')
            pos += 1
            return v
        raise ErrorExtraccion('La expresión está incompleta.')

    resultado = expr()
    if pos != len(tokens):
        raise ErrorExtraccion('Sobra algo al final de la expresión.')
    return resultado


# ═══════════════════════════════════════════════════════════════════════════
#  Del texto a las piezas del modelo
# ═══════════════════════════════════════════════════════════════════════════
_TOKEN_MATEMATICO = re.compile(
    r'^(?:\d+(?:\.\d+)?|\.\d+|[A-Za-z]\d*(?![A-Za-z])|[-+*/()<>=])+$'
)
_REL = re.compile(r'(<=|>=|=)')
_LISTA_VARS = re.compile(r'^\s*[A-Za-z]\d*(?:\s*(?:,|y|and|e)\s*[A-Za-z]\d*)+\s*$')
_CONJ = {'y', 'and', 'e'}


def _corridas(texto):
    """Trozos consecutivos de «matemática» dentro de una línea con palabras."""
    corridas, actual = [], []

    def cerrar():
        nonlocal actual
        if actual:
            corridas.append(' '.join(actual))
        actual = []

    for token in texto.replace(',', ' , ').split():
        if token == ',':
            cerrar()          # la coma separa condiciones o forma listas («x1, x2 >= 0»)
            continue
        limpio = token.rstrip('.;:')
        if limpio and _TOKEN_MATEMATICO.match(limpio):
            actual.append(limpio)
        else:
            cerrar()
    cerrar()
    return [c for c in corridas if c.strip()]


_LISTA_CON_RELACION = re.compile(r'^\s*((?:\band\b|[A-Za-z]\d*|,|\s)+?)\s*(<=|>=|=)\s*(.+)$', re.I)


def _variables_de_lista(texto):
    """
    'x, y' · 'x e y' · 'x, y y z' → ['x', 'y', ...]; None si no es una lista de variables.
    «y», «e» y «and» son conjunciones solo entre dos variables (si no, «y» es la variable y).
    """
    esperando, variables = True, []
    for token in re.findall(r'\band\b|[A-Za-z]\d*|,', texto, flags=re.I):
        if token == ',':
            esperando = True
        elif esperando:
            variables.append(token)
            esperando = False
        elif token.lower() in ('y', 'e', 'and'):
            esperando = True
        else:
            return None
    return variables if not esperando and len(variables) >= 2 else None


def _relacion(texto):
    """'3x+2y<=18' → [(Lineal lhs−rhs, op)]; cadenas a<=b<=c dan dos relaciones."""
    lista = _LISTA_CON_RELACION.match(texto)
    variables = _variables_de_lista(lista.group(1)) if lista else None
    if variables and not re.search(r'[A-Za-z]', lista.group(3)):        # «x, y >= 2», «x e y >= 0»
        resultado = []
        for v in variables:
            resultado += _relacion(f'{v} {lista.group(2)} {lista.group(3)}')
        return resultado
    partes = _REL.split(texto)
    if len(partes) < 3:
        raise ErrorExtraccion('No hay una desigualdad.')
    expresiones = [parsear_lineal(p) for p in partes[0::2]]
    ops = partes[1::2]
    return [(expresiones[i].mas(expresiones[i + 1], -1), ops[i]) for i in range(len(ops))]


def _relaciones_de_corrida(corrida):
    """Interpreta una corrida; si trae varias restricciones unidas por «y», las separa."""
    tokens = corrida.split()
    try:
        return _relacion(corrida)
    except ErrorExtraccion as primero:
        for i, t in enumerate(tokens):
            if t.lower() in _CONJ and 0 < i < len(tokens) - 1:
                izq, der = ' '.join(tokens[:i]), ' '.join(tokens[i + 1:])
                if _REL.search(izq) and _REL.search(der):
                    try:
                        return _relacion(izq) + _relaciones_de_corrida(der)
                    except ErrorExtraccion:
                        continue
        raise primero


_VERBO_MAX = re.compile(r'maximi[zc]\w*|maximize|\bmax\b|maximice\w*', re.I)
_VERBO_MIN = re.compile(r'minimi[zc]\w*|minimize|\bmin\b|minimice\w*', re.I)
_NOMBRE_MAX = re.compile(r'm[aá]xim[oa]s?\b|maximaci[oó]n|maximum', re.I)
_NOMBRE_MIN = re.compile(r'm[ií]nim[oa]s?\b|minimizaci[oó]n|minimum', re.I)
_LADO_IZQ_OBJETIVO = re.compile(
    r'^\s*(?:[zZfFgGcCuUwWpP](?:\s*\([^)]*\))?|[A-Za-zÁÉÍÓÚáéíóúñÑ]{2,}(?:\s*\([^)]*\))?)\s*=(?!=)'
)


def _tipo_en(texto, incluir_nombres):
    mx = bool(_VERBO_MAX.search(texto)) or (incluir_nombres and bool(_NOMBRE_MAX.search(texto)))
    mn = bool(_VERBO_MIN.search(texto)) or (incluir_nombres and bool(_NOMBRE_MIN.search(texto)))
    if mx and not mn:
        return 'max'
    if mn and not mx:
        return 'min'
    return None


_PALABRAS = r'A-Za-zÁÉÍÓÚÜáéíóúüñÑ'
_UNIDADES_SUELTAS = {
    'unidades', 'unidad', 'horas', 'hora', 'kg', 'kilos', 'litros', 'pesos', 'dólares', 'dolares',
    'minutos', 'toneladas', 'metros', 'gramos', 'mg', 'euros', 'cm', 'm',
}
_ROTULO_PREFIJO = re.compile(rf'^\s*(?P<rot>[{_PALABRAS}][{_PALABRAS}0-9 ]{{1,40}}?)\s*:\s*(?P<resto>.+)$')
_ROTULO_PARENTESIS = re.compile(rf'\(\s*(?P<rot>[{_PALABRAS}][{_PALABRAS}0-9 ,.-]{{2,50}})\s*\)\s*\.?\s*$')
_ROTULO_COLA = re.compile(rf'(?:<=|>=|=)\s*-?[\d./]+\s+(?P<rot>[{_PALABRAS}][{_PALABRAS} ]{{2,40}}?)\s*\.?\s*$')


def _limpiar_rotulo(rot):
    rot = ' '.join(rot.split()).strip(' .,;')
    if len(re.findall(rf'[{_PALABRAS}]', rot)) < 3 or rot.lower() in _UNIDADES_SUELTAS or re.search(r'[<>=]', rot):
        return ''
    return rot[:60]


def _lineas_con_rotulo(norm):
    """Líneas del enunciado con, si lo traen, el nombre de la restricción («Proteína», «horas de…»)."""
    texto = _MARCADORES.sub('\n', norm)
    pares = []
    for cruda in re.split(r'[\n;]|(?<=[\w)])\.\s+(?=[A-ZÁÉÍÓÚÑ¿¡])', texto):
        linea = _PREFIJO_LINEA.sub('', cruda).strip()
        rotulo = ''
        m = _ROTULO_PREFIJO.match(linea)
        if m and _REL.search(m.group('resto')):
            rotulo, linea = _limpiar_rotulo(m.group('rot')), m.group('resto')
        if _REL.search(linea):
            m = _ROTULO_PARENTESIS.search(linea)
            if m and not rotulo and not _REL.search(m.group('rot')):
                rotulo = _limpiar_rotulo(m.group('rot'))
            m = _ROTULO_COLA.search(linea)
            if m and not rotulo and len(m.group('rot').split()) >= 2:
                rotulo = _limpiar_rotulo(m.group('rot'))
        linea = linea.replace(':', ' ').strip()
        if linea:
            pares.append((linea, rotulo))
    return pares


def _lineas(norm):
    return [linea for linea, _ in _lineas_con_rotulo(norm)]


# ── ¿Qué representa cada variable y qué mide Z? ─────────────────────────────
_STOP_ATRAS = {
    'produce', 'producen', 'produciendo', 'fabrica', 'fabrican', 'vende', 'venden', 'compra', 'compran',
    'tiene', 'tienen', 'hay', 'y', 'e', 'con', 'que', 'se', 'cada', 'dos', 'tres', 'unas', 'unos',
    'una', 'un', 'el', 'la', 'los', 'las', 'si', 'donde', 'sea', 'sean', 'siendo', 'llamado', 'llamada',
    'como', 'son', 'es', 'para', 'por', 'ni', 'o',
}
_NO_NOMBRE = {'mayor', 'menor', 'igual', 'positivo', 'positiva', 'negativo', 'entero', 'entera', 'no', 'al', 'a'}
_PREFIJO_CANTIDAD = re.compile(
    r'^(?:(?:el|la|los|las|un|una)\s+)?(?:(?:n[uú]mero|cantidad|total)\s+(?:total\s+)?de\s+)?', re.I)


def _limpiar_nombre(nombre):
    n = ' '.join(nombre.split()).strip(' .,;:-')
    n = _PREFIJO_CANTIDAD.sub('', n).strip()
    palabras = n.split()
    if not palabras or palabras[0].lower() in _NO_NOMBRE or any(re.fullmatch(r'[a-z]\d*|[A-Z]\d+', w) for w in palabras):
        return ''
    if re.search(r'\d|[<>=]', n) or not 2 < len(n) <= 40:
        return ''
    return n


def _nombre_de_variable(norm, simbolo):
    s = re.escape(simbolo)
    aislada = rf'(?<![A-Za-z0-9]){s}(?![A-Za-z0-9])'
    definicion = re.search(
        aislada + rf'\s*(?:=|:|representa(?:n)?|denota|es|son|ser[aá]n?)\s*(?P<n>[{_PALABRAS}][{_PALABRAS} ]{{1,48}})',
        norm, re.I) or re.search(
        aislada + rf'\s+(?:el|la|los|las)\s+(?P<n>(?:n[uú]mero|cantidad|total)\s+de\s+[{_PALABRAS}][{_PALABRAS} ]{{1,48}})',
        norm, re.I)
    if definicion:
        crudo = re.split(r'\s+(?:y|e|que|donde|con|si)\s+|[,.;(]', definicion.group('n'), maxsplit=1)[0]
        nombre = _limpiar_nombre(crudo)
        if nombre:
            return nombre
    for m in re.finditer(rf'(?P<n>(?:[{_PALABRAS}]+\s+){{0,3}}[{_PALABRAS}]+)\s*\(\s*{s}\s*\)', norm, re.I):
        palabras = m.group('n').split()
        elegidas = []
        for palabra in reversed(palabras):
            if palabra.lower() in _STOP_ATRAS:
                break
            elegidas.append(palabra)
        nombre = _limpiar_nombre(' '.join(reversed(elegidas)))
        if nombre:
            return nombre
    return ''


_CORTE_OBJETIVO = re.compile(r'\s+(?:sujeto|sabiendo|donde|si|cuando|para|con|dado|seg[uú]n|de acuerdo|s\.?a)\b|[,.;:(=\n]', re.I)


def _nombre_del_objetivo(norm):
    articulo = r'(?:el|la|los|las)'
    patrones = [
        rf'(?:maximi[zc]\w*|minimi[zc]\w*|maximice|minimice)\s+(?:de\s+)?(?P<n>{articulo}\s+[{_PALABRAS}][{_PALABRAS} ]{{2,40}})',
        rf'(?:maximizaci[oó]n|minimizaci[oó]n)\s+de(?:l|\s+{articulo})\s+(?P<n>[{_PALABRAS}][{_PALABRAS} ]{{2,40}})',
        rf'(?<![A-Za-z0-9])[zZ](?![A-Za-z0-9])\s*(?:=|es|representa)\s*(?P<n>{articulo}\s+[{_PALABRAS}][{_PALABRAS} ]{{2,40}})',
    ]
    for patron in patrones:
        m = re.search(patron, norm, re.I)
        if not m:
            continue
        crudo = _CORTE_OBJETIVO.split(m.group('n'), maxsplit=1)[0]
        palabras = [w for w in crudo.split()]
        while palabras and re.fullmatch(r'[A-Za-z]\d*', palabras[-1]):    # «… total Z»
            palabras.pop()
        nombre = ' '.join(palabras).strip()
        if m.re is not None and patron is patrones[1]:
            nombre = f'el {nombre}'
        if 3 < len(nombre) <= 50 and not re.search(r'\d|[<>=]', nombre):
            return nombre
    return ''


def _objetivo_de(linea):
    """Lineal de la función objetivo escrita en `linea`, o None."""
    if '<=' in linea or '>=' in linea:
        return None
    zona = linea.split('=', 1)[1] if '=' in linea else _despues_del_verbo(linea)
    for corrida in _corridas(zona):
        try:
            lin = parsear_lineal(corrida)
        except ErrorExtraccion:
            continue
        if lin.c:
            return lin
    return None


def _despues_del_verbo(linea):
    m = _VERBO_MAX.search(linea) or _VERBO_MIN.search(linea) or _NOMBRE_MAX.search(linea) or _NOMBRE_MIN.search(linea)
    return linea[m.end():] if m else linea


def _buscar_objetivo(lineas, norm):
    # 1) línea con «maximizar/minimizar/max/min…»
    for i, linea in enumerate(lineas):
        tipo = _tipo_en(linea, incluir_nombres=True)
        if tipo:
            lin = _objetivo_de(linea)
            if lin:
                return i, tipo, lin
    # 2) línea «Z = …» y el verbo en cualquier parte del texto
    for i, linea in enumerate(lineas):
        if _LADO_IZQ_OBJETIVO.match(linea):
            lin = _objetivo_de(linea)
            if lin:
                return i, _tipo_en(norm, incluir_nombres=False), lin
    return None, None, None


def _nombres_ordenados(variables):
    def clave(v):
        m = re.fullmatch(r'([a-z]+)(\d*)', v)
        return (m.group(1), int(m.group(2) or 0))
    return sorted(variables, key=clave)


def _fmt_num(q):
    """Decimal exacto cuando termina (0.5, 6.25, 120.5); fracción si no (1/3)."""
    q = Fraction(q)
    if q.denominator == 1:
        return str(q.numerator)
    d = q.denominator
    for primo in (2, 5):
        while d % primo == 0:
            d //= primo
    if d != 1:
        return f'{q.numerator}/{q.denominator}'
    decimales = 0
    while (q * 10 ** decimales).denominator != 1:
        decimales += 1
    texto = f'{float(q):.{decimales}f}'
    return texto if Fraction(texto) == q else f'{q.numerator}/{q.denominator}'


def extraer_por_reglas(texto):
    norm = normalizar(texto)
    estrictas = bool(re.search(r'(?<![<>=])[<>](?!=)', texto.translate(_UNICODE)))
    pares = _lineas_con_rotulo(norm)
    lineas = [p[0] for p in pares]
    rotulos = [p[1] for p in pares]

    idx_obj, tipo, objetivo = _buscar_objetivo(lineas, norm)
    if objetivo is None:
        raise ErrorExtraccion(
            'No encontré la función objetivo. Escríbela así: «Maximizar Z = 3x + 5y» '
            '(o «Minimizar …»). Debe ser lineal (sin productos como x·y). '
            'Si el ejercicio viene redactado en palabras, primero plantéalo como modelo '
            '(variables, función objetivo y restricciones) y pégalo aquí.')

    advertencias, ignoradas, relaciones, pendientes = [], [], [], []
    for i, linea in enumerate(lineas):
        if i == idx_obj:
            continue
        con_relacion = [c for c in _corridas(linea) if _REL.search(c)]
        for corrida in _corridas(linea):
            if not _REL.search(corrida):
                if re.fullmatch(r'[A-Za-z]\d*', corrida.strip()):
                    pendientes.append(corrida.strip().lower())
                continue
            try:
                rels = _relaciones_de_corrida(corrida)
            except ErrorExtraccion as exc:
                pendientes = []
                solo_matematica = len(_corridas(linea)) == 1 and corrida.replace(' ', '') == linea.replace(' ', '')
                if solo_matematica:                      # una línea que era solo matemática y no se entiende
                    advertencias.append(f'No pude interpretar «{corrida}»: {exc}')
                continue                                 # si no, era una frase («x2 = cantidad de…»)
            # «x1, x2 ≥ 0»: la lista antes de la coma pertenece a esta relación
            if pendientes and len(rels) == 1 and len(rels[0][0].c) == 1:
                lin, op = rels[0]
                (var, q), = lin.c.items()
                rels = [(Lineal({p: q}, lin.k), op) for p in pendientes + [var]]
            pendientes = []
            rotulo = rotulos[i] if len(con_relacion) == 1 and len(rels) == 1 else ''
            relaciones.extend((lin_, op_, rotulo) for lin_, op_ in rels)
        if not _corridas(linea) or not any(_REL.search(c) for c in _corridas(linea)):
            if re.search(r'\d', linea):
                ignoradas.append(linea)

    if not relaciones:
        raise ErrorExtraccion(
            'Encontré la función objetivo pero ninguna restricción. Escribe cada una en su línea, '
            'por ejemplo «2x + y <= 8».')

    # Variables del problema (máximo dos)
    usadas = set(objetivo.c)
    for lin, _, _ in relaciones:
        usadas |= set(lin.c)
    if len(usadas) > 2:
        raise ErrorExtraccion(
            f'Encontré {len(usadas)} variables ({", ".join(_nombres_ordenados(usadas))}). '
            'El método gráfico solo resuelve problemas con 2 variables; para más variables se usa Simplex.')
    if len(usadas) < 2:
        raise ErrorExtraccion(
            f'Solo encontré una variable ({", ".join(usadas) or "ninguna"}). '
            'El método gráfico necesita exactamente 2 variables de decisión.')
    v1, v2 = _nombres_ordenados(usadas)

    restricciones, vistas = [], set()
    for lin, op, rotulo in relaciones:
        a, b, c = lin.c.get(v1, Fraction(0)), lin.c.get(v2, Fraction(0)), -lin.k
        if a == 0 and b == 0:
            advertencias.append('Ignoré una condición sin variables.')
            continue
        # No negatividad (ya se asume): x ≥ 0, que también se escribe −x ≤ 0
        solo_una = (a == 0) != (b == 0)
        signo = a + b
        if solo_una and c == 0 and ((op == '>=' and signo > 0) or (op == '<=' and signo < 0)):
            continue
        clave = (a, b, op, c)
        if clave in vistas:
            continue
        vistas.add(clave)
        restricciones.append({'x': _fmt_num(a), 'y': _fmt_num(b), 'op': op, 'c': _fmt_num(c), 'rotulo': rotulo})

    if not restricciones:
        raise ErrorExtraccion('Solo encontré condiciones de no negatividad (x ≥ 0, y ≥ 0); faltan las restricciones del problema.')

    if estrictas:
        advertencias.append('Había desigualdades estrictas (< o >): las tomé como ≤ y ≥, porque el método gráfico trabaja con la frontera.')
    if re.search(r'enter[oa]s?|\\mathbb\{Z\}|\bin\s*Z\b|integer', texto, re.I):
        advertencias.append('El enunciado menciona valores enteros: el método gráfico da la solución continua; revisa si el óptimo es entero.')
    vs = f'(?:{re.escape(v1)}|{re.escape(v2)})'        # solo líneas que parecen matemática (3x, x + …)
    utiles = [l for l in ignoradas
              if re.search(rf'\d{vs}(?![A-Za-z0-9])|(?<![A-Za-z0-9]){vs}\s*[-+*/]', l, re.I)]
    if utiles:                                    # líneas con las variables pero sin desigualdad
        advertencias.append('Ignoré líneas sin desigualdad: ' + ' | '.join(f'«{l[:60]}»' for l in utiles[:3]))
    if tipo is None:
        advertencias.append('No encontré si hay que maximizar o minimizar. Elige una opción antes de resolver.')

    return _armar(
        metodo='reglas', tipo=tipo,
        zx=objetivo.c.get(v1, Fraction(0)), zy=objetivo.c.get(v2, Fraction(0)), zk=objetivo.k,
        restricciones=restricciones,
        variables=[{'simbolo': v, 'descripcion': _nombre_de_variable(norm, v)} for v in (v1, v2)],
        objetivo_nombre=_nombre_del_objetivo(norm),
        advertencias=advertencias,
        requiere_revision=tipo is None or any(a.startswith('No pude interpretar') for a in advertencias),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Resultado común (reglas e IA) + validación
# ═══════════════════════════════════════════════════════════════════════════
def _armar(metodo, tipo, zx, zy, zk, restricciones, variables, advertencias,
           requiere_revision=False, notas=None, objetivo_nombre=''):
    zx, zy, zk = Fraction(zx), Fraction(zy), Fraction(zk)
    filas = []
    for r in restricciones:
        try:
            a, b, c = (parse_numero(str(r[k]), 'una restricción') for k in ('x', 'y', 'c'))
        except EntradaInvalida as exc:
            raise ErrorExtraccion(f'Una restricción quedó con un número inválido: {exc}')
        if r['op'] not in OPERADORES:
            raise ErrorExtraccion(f'Operador inválido en una restricción: {r["op"]}')
        filas.append({'x': _fmt_num(a), 'y': _fmt_num(b), 'op': r['op'], 'c': _fmt_num(c),
                      'rotulo': r.get('rotulo', ''),
                      'texto': f'{expresion(a, b)} {SIMBOLO[r["op"]]} {fmt(c)}'})

    for i, v in enumerate(variables, start=1):
        v['nombre'] = f'X{i}'

    z_txt = expresion(zx, zy) + (f' {"+" if zk > 0 else "−"} {fmt(abs(zk))}' if zk else '')
    resumen = []
    if variables[0]['simbolo'] or variables[1]['simbolo']:
        resumen.append('Variables: ' + ' · '.join(
            f'X{i} = {v["simbolo"]}' + (f' ({v["descripcion"]})' if v['descripcion'] else '')
            for i, v in enumerate(variables, start=1)))
    resumen.append(f'Objetivo: {"Maximizar" if tipo == "max" else "Minimizar" if tipo == "min" else "¿Maximizar o minimizar?"} Z = {z_txt}')
    if objetivo_nombre:
        resumen.append(f'Z mide: {objetivo_nombre}')
    resumen += [f'R{i}: {f["texto"]}' + (f' — {f["rotulo"]}' if f['rotulo'] else '') for i, f in enumerate(filas, start=1)]
    resumen.append('X1 ≥ 0, X2 ≥ 0 (no negatividad, se asume siempre)')

    return {
        'ok': True, 'metodo': metodo, 'tipo': tipo,
        'z': [_fmt_num(zx), _fmt_num(zy)], 'z_k': _fmt_num(zk), 'objetivo_nombre': objetivo_nombre,
        'restricciones': filas, 'variables': variables,
        'resumen': resumen, 'advertencias': advertencias, 'notas': notas or [],
        'requiere_revision': requiere_revision,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Punto de entrada
# ═══════════════════════════════════════════════════════════════════════════
def extraer(texto):
    """Lee el enunciado y devuelve el modelo; lanza ErrorExtraccion si no lo entiende."""
    texto = (texto or '').strip()
    if not texto:
        raise ErrorExtraccion('Escribe o pega primero el enunciado del ejercicio.')
    if len(texto) > MAX_TEXTO:
        raise ErrorExtraccion(f'El enunciado es muy largo (máximo {MAX_TEXTO} caracteres).')
    return extraer_por_reglas(texto)
