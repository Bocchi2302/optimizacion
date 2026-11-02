# blueprints/gran_m_bp.py
import re
from fractions import Fraction as F
from flask import Blueprint, render_template, request

gran_m_bp = Blueprint('gran_m_bp', __name__)

DIGITOS_SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
SUB_A_DIGITO = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
MAX_ITERACIONES = 100

# Ejercicio que aparece precargado en el formulario (el mismo del enunciado)
DATOS_EJEMPLO = {
    'tipo_opt': 'min',
    'z': ['1.5', '2.5'],
    'restricciones': [
        {'a': ['2', '1'], 'op': '<=', 'c': '90'},
        {'a': ['1', '1'], 'op': '>=', 'c': '50'},
        {'a': ['1', '0'], 'op': '<=', 'c': '10'},
    ],
}


class Num:
    """Número con la forma a + b·M, donde M es una penalización tan grande que tiende a infinito."""

    def __init__(self, a=0, b=0):
        self.a = F(a)
        self.b = F(b)

    def __add__(self, otro):
        otro = _como_num(otro)
        return Num(self.a + otro.a, self.b + otro.b)

    def __sub__(self, otro):
        otro = _como_num(otro)
        return Num(self.a - otro.a, self.b - otro.b)

    def __mul__(self, otro):
        # La fila pivote nunca contiene M, así que solo se multiplica M por números sin M
        if isinstance(otro, Num):
            if otro.b == 0:
                return Num(self.a * otro.a, self.b * otro.a)
            if self.b == 0:
                return Num(otro.a * self.a, otro.b * self.a)
            raise ValueError('No se puede multiplicar M por M')
        return Num(self.a * otro, self.b * otro)

    def __neg__(self):
        return Num(-self.a, -self.b)

    def __truediv__(self, otro):
        divisor = _como_num(otro)
        if divisor.b != 0:
            raise ValueError('No se puede dividir entre una expresión con M')
        return Num(self.a / divisor.a, self.b / divisor.a)

    def es_cero(self):
        return self.a == 0 and self.b == 0

    def clave(self):
        # Con M tendiendo a infinito, se compara primero el coeficiente de M
        return (self.b, self.a)


def _como_num(valor):
    return valor if isinstance(valor, Num) else Num(valor)


def _fmt_numero(x):
    return str(int(x)) if x.denominator == 1 else str(float(x))


def fmt(n):
    """Convierte un Num a texto, por ejemplo 'M - 1.5' o '40M + 15'."""
    if n.b == 0:
        return _fmt_numero(n.a)
    termino_m = 'M' if abs(n.b) == 1 else f'{_fmt_numero(abs(n.b))}M'
    if n.b < 0:
        termino_m = '-' + termino_m
    if n.a == 0:
        return termino_m
    signo = ' + ' if n.a > 0 else ' - '
    return f'{termino_m}{signo}{_fmt_numero(abs(n.a))}'


def nombre(prefijo, indice):
    return prefijo + str(indice).translate(DIGITOS_SUB)


def a_latex(texto):
    """Convierte 'S₁' en 'S_1' para usarlo dentro de KaTeX."""
    return re.sub(r'[₀₁₂₃₄₅₆₇₈₉]+', lambda m: '_' + m.group(0).translate(SUB_A_DIGITO), texto)


def expr_latex(terminos):
    """Arma una expresión lineal en LaTeX a partir de pares (coeficiente, nombre_latex)."""
    partes = []
    for coef, nom in terminos:
        if coef == 0:
            continue
        magnitud = '' if abs(coef) == 1 else _fmt_numero(abs(coef))
        partes.append(('-' if coef < 0 else '+', magnitud + nom))
    if not partes:
        return '0'
    signo, texto = partes[0]
    resultado = ('-' if signo == '-' else '') + texto
    for signo, texto in partes[1:]:
        resultado += f' {signo} {texto}'
    return resultado


def normalizar(restricciones):
    """Si el lado derecho es negativo, se multiplica la restricción por -1 para que quede ≥ 0."""
    salida = []
    for a, op, b in restricciones:
        if b < 0:
            a = [-x for x in a]
            b = -b
            op = {'<=': '>=', '>=': '<=', '=': '='}[op]
        salida.append((a, op, b))
    return salida


def construir_tabla(tipo, c, restricciones):
    """Arma la tabla inicial con holguras, excesos y artificiales, y la fila Z con la penalización."""
    columnas = ['Z'] + [nombre('x', j + 1) for j in range(len(c))]
    cont_s = cont_a = 0
    base = []
    info = []  # (a, op, b, columna_S, signo_S, columna_A)

    for a, op, b in restricciones:
        col_s = col_a = None
        signo = 0
        if op in ('<=', '>='):
            cont_s += 1
            columnas.append(nombre('S', cont_s))
            col_s = len(columnas) - 1
            signo = 1 if op == '<=' else -1
            if op == '<=':
                base.append(columnas[col_s])
        if op in ('>=', '='):
            cont_a += 1
            columnas.append(nombre('A', cont_a))
            col_a = len(columnas) - 1
            base.append(columnas[col_a])
        info.append((a, op, b, col_s, signo, col_a))

    columnas.append('Solución')
    ncol = len(columnas)

    # Fila Z: Z - c·x = 0. Min penaliza con -M·A, max con +M·A (así queda Z - c·x ± M·A = 0)
    penal = -1 if tipo == 'min' else 1
    fila_z = [Num() for _ in range(ncol)]
    fila_z[0] = Num(1)
    for j, cj in enumerate(c):
        fila_z[1 + j] = Num(-cj)
    for *_, col_a in info:
        if col_a is not None:
            fila_z[col_a] = Num(0, penal)

    tab = [fila_z]
    for a, _, b, col_s, signo, col_a in info:
        fila = [Num() for _ in range(ncol)]
        for j, aj in enumerate(a):
            fila[1 + j] = Num(aj)
        if col_s is not None:
            fila[col_s] = Num(signo)
        if col_a is not None:
            fila[col_a] = Num(1)
        fila[-1] = Num(b)
        tab.append(fila)

    return tab, base, columnas, info


def eliminar_artificiales(tab, base, columnas):
    """Hace 0 el coeficiente de las variables básicas en la fila Z."""
    for i, variable in enumerate(base, start=1):
        col = columnas.index(variable)
        if not tab[0][col].es_cero():
            factor = tab[0][col]
            tab[0] = [tab[0][j] - factor * tab[i][j] for j in range(len(tab[0]))]


def columna_entrante(tab, tipo):
    """Elige la variable que mejora Z. Min: coeficiente positivo más grande. Max: coeficiente negativo más grande en valor absoluto."""
    candidatos = []
    for j in range(1, len(tab[0]) - 1):
        r = tab[0][j]
        g = r if tipo == 'min' else -r
        if g.clave() > (0, 0):
            candidatos.append((j, g))
    if not candidatos:
        return None
    return max(candidatos, key=lambda c: c[1].clave())[0]


def fila_saliente(tab, col):
    """Prueba del cociente mínimo: sale la fila con la menor razón RHS / coeficiente positivo."""
    cocientes = []
    for i in range(1, len(tab)):
        coef = tab[i][col]
        if coef.b == 0 and coef.a > 0:
            cocientes.append((tab[i][-1].a / coef.a, i))
    if not cocientes:
        return None
    return min(cocientes)[1]


def razones_texto(tab, base, col):
    partes = []
    for i in range(1, len(tab)):
        coef = tab[i][col]
        if coef.b == 0 and coef.a > 0:
            razon = tab[i][-1] / coef
            partes.append(f'{base[i - 1]}: {fmt(tab[i][-1])} / {fmt(coef)} = {fmt(razon)}')
    return partes


def pivotear(tab, base, columnas, fila, col):
    piv = tab[fila][col]
    tab[fila] = [celda / piv for celda in tab[fila]]
    for i, fila_i in enumerate(tab):
        if i != fila and not fila_i[col].es_cero():
            factor = fila_i[col]
            tab[i] = [celda - factor * tab[fila][j] for j, celda in enumerate(fila_i)]
    base[fila - 1] = columnas[col]


def serializar(tab, base, columnas):
    """Convierte la tabla a texto para que el frontend la muestre."""
    filas = [{'base': 'Z', 'celdas': [fmt(c) for c in tab[0]]}]
    for i, variable in enumerate(base, start=1):
        filas.append({'base': variable, 'celdas': [fmt(c) for c in tab[i]]})
    return {'columnas': columnas, 'filas': filas}


def _paso(titulo, explicacion, formulas=None, tabla=None, tabla_resultado=None, pivote=None):
    return {
        'titulo': titulo,
        'explicacion': explicacion,
        'formulas': formulas or [],
        'tabla': tabla,
        'tabla_resultado': tabla_resultado,
        'pivote': pivote,
    }


def _diagnostico_infactible(tab, base, columnas, arts_restriccion, formulas_paso1, numero):
    """Explica por qué no hay solución factible: una artificial queda positiva en la solución final."""
    items = []
    for i, variable in enumerate(base, start=1):
        if variable.startswith('A') and not tab[i][-1].es_cero():
            restriccion = arts_restriccion[variable]
            items.append(
                f'<li>${a_latex(variable)} = {fmt(tab[i][-1])}$ sigue en la base. Viene de la restricción '
                f'{restriccion}: {formulas_paso1[restriccion - 1]}</li>'
            )
    explicacion = (
        '<p>En la solución final hay variables artificiales con valor positivo. Como su penalización es $M$ '
        '(muy grande), el Simplex intenta sacarlas de la base, pero no puede: no existe ningún punto que cumpla '
        'todas las restricciones a la vez.</p>'
        '<p><strong>Restricciones involucradas:</strong></p>'
        f'<ul>{"".join(items)}</ul>'
        '<p>Revisa esas restricciones: sus lados derechos o coeficientes pueden contradecir a las demás.</p>'
    )
    return _paso(
        f'Paso {numero}: Diagnóstico: no hay solución factible',
        explicacion,
        tabla=serializar(tab, base, columnas),
    )


def _diagnostico_no_acotado(tab, base, columnas, tipo, col, numero):
    """Explica por qué el problema no está acotado: la variable que entra no tiene ninguna fila que la limite."""
    entra = columnas[col]
    coeficientes = ', '.join(f'{base[i - 1]}: {fmt(tab[i][col])}' for i in range(1, len(tab)))
    sentido = 'crece' if tipo == 'max' else 'decrece'
    explicacion = (
        f'<p>La variable ${a_latex(entra)}$ puede aumentar sin límite: en su columna ninguna fila tiene coeficiente '
        'positivo, así que la prueba del cociente mínimo no encuentra fila que salga.</p>'
        f'<p>Coeficientes de la columna de {entra}: {coeficientes} (ninguno es positivo).</p>'
        f'<p>Al aumentar {entra}, la función objetivo {sentido} sin límite. Por eso no existe un óptimo finito.</p>'
        '<p>Revisa si falta una restricción que limite esta variable.</p>'
    )
    return _paso(
        f'Paso {numero}: Diagnóstico: problema no acotado',
        explicacion,
        tabla=serializar(tab, base, columnas),
        pivote={'fila': None, 'columna': col},
    )


def resolver(tipo, c, restricciones):
    """
    Resuelve un problema de programación lineal con el método de la Gran M.
    tipo: 'min' o 'max'. c: coeficientes de la función objetivo (Fraction).
    restricciones: lista de (coeficientes, operador, lado_derecho).
    Devuelve (pasos, mensaje). Si el problema no tiene solución óptima factible, los pasos
    llegan hasta el diagnóstico y el mensaje lo explica; si tiene solución, el mensaje es None.
    """
    invertidas = [i + 1 for i, (_, _, b) in enumerate(restricciones) if b < 0]
    restricciones = normalizar(restricciones)
    tab, base, columnas, info = construir_tabla(tipo, c, restricciones)
    # Qué restricción creó cada variable artificial (para el diagnóstico)
    arts_restriccion = {columnas[col_a]: i for i, (*_, col_a) in enumerate(info, start=1) if col_a is not None}
    nombres_a = [columnas[col_a] for *_, col_a in info if col_a is not None]
    nombre_tipo = 'minimización' if tipo == 'min' else 'maximización'
    signo_penal = '+' if tipo == 'min' else '-'

    pasos = []

    # Paso 1: estandarización
    formulas = []
    for a, op, b, col_s, signo, col_a in info:
        terminos = [(aj, a_latex(columnas[1 + j])) for j, aj in enumerate(a)]
        if col_s is not None:
            terminos.append((signo, a_latex(columnas[col_s])))
        if col_a is not None:
            terminos.append((1, a_latex(columnas[col_a])))
        formulas.append(f'${expr_latex(terminos)} = {_fmt_numero(b)}$')

    penalizacion = ''.join(f' {signo_penal} M {a_latex(n)}' for n in nombres_a)
    terminos_z = [(cj, a_latex(columnas[1 + j])) for j, cj in enumerate(c)]
    formulas.append(f'$Z = {expr_latex(terminos_z)}{penalizacion}$')

    pasos.append(_paso(
        'Paso 1: Estandarización',
        '<p>El Simplex trabaja con <strong>igualdades</strong>. Cada restricción se transforma así:</p>'
        '<ul>'
        '<li>Restricción ≤: se suma una <strong>holgura</strong> $+S_i$.</li>'
        '<li>Restricción ≥: se resta un <strong>exceso</strong> $-S_i$ y se suma una <strong>artificial</strong> $+A_i$.</li>'
        '<li>Restricción =: se suma solo una <strong>artificial</strong> $+A_i$.</li>'
        '</ul>'
        f'<p>Como el problema es de <strong>{nombre_tipo}</strong>, cada artificial penaliza la función objetivo '
        f'con ${signo_penal} M A_i$.</p>'
        + ''.join(
            f'<p>La restricción {i} tenía lado derecho negativo: se multiplicó por −1 y la desigualdad cambió de sentido.</p>'
            for i in invertidas
        ),
        formulas=formulas,
    ))

    # Paso 2: tabla inicial
    pasos.append(_paso(
        'Paso 2: Tabla inicial del Simplex',
        f'<p>Las variables básicas iniciales son {", ".join(base)}. En la fila Z aparece la penalización '
        f'en las columnas de las artificiales, así que la fila Z todavía no está lista para pivotear.</p>',
        tabla=serializar(tab, base, columnas),
    ))

    # Paso 3: eliminar las artificiales de la fila Z
    eliminar_artificiales(tab, base, columnas)
    pasos.append(_paso(
        'Paso 3: Eliminación de las artificiales en la fila Z',
        '<p>Cada variable básica con coeficiente distinto de cero en la fila Z se elimina restando a Z el múltiplo '
        'de su fila, para que ese coeficiente quede en 0.</p>'
        '<p>Después de este paso, la fila Z tiene coeficientes que dependen de $M$.</p>',
        tabla=serializar(tab, base, columnas),
    ))

    # Pasos 4 en adelante: iteraciones del Simplex
    k = 0
    while True:
        col = columna_entrante(tab, tipo)
        if col is None:
            break
        fila = fila_saliente(tab, col)
        if fila is None:
            pasos.append(_diagnostico_no_acotado(tab, base, columnas, tipo, col, 4 + k))
            return pasos, ('El problema no está acotado: la función objetivo crece sin límite. '
                           'Revisa el diagnóstico al final del procedimiento.')
        k += 1
        if k > MAX_ITERACIONES:
            raise ValueError('El método no convergió después de 100 iteraciones.')

        entra = columnas[col]
        sale = base[fila - 1]
        elemento = fmt(tab[fila][col])
        coef_entra = fmt(tab[0][col])
        razones = razones_texto(tab, base, col)
        antes = serializar(tab, base, columnas)

        pivotear(tab, base, columnas, fila, col)
        despues = serializar(tab, base, columnas)

        if tipo == 'min':
            motivo_col = 'tiene el coeficiente positivo más grande en la fila Z'
            efecto = 'En minimización, aumentar esa variable reduce Z.'
        else:
            motivo_col = 'tiene el coeficiente negativo más grande en valor absoluto en la fila Z'
            efecto = 'En maximización, aumentar esa variable aumenta Z.'

        pasos.append(_paso(
            f'Paso {3 + k}: Iteración {k} (Columna pivote {entra}, Fila pivote {sale}, Elemento pivote {elemento})',
            f'<p><strong>Columna pivote:</strong> ${a_latex(entra)}$ {motivo_col} ({coef_entra}). {efecto}</p>'
            f'<p><strong>Fila pivote:</strong> se calcula la razón RHS / coeficiente de cada fila con coeficiente positivo: '
            f'{"; ".join(razones)}. La menor es {sale}, así que sale {sale}.</p>'
            f'<p><strong>Elemento pivote:</strong> {elemento}. Se divide la fila pivote entre el elemento pivote y '
            f'se eliminan los demás valores de la columna.</p>',
            tabla=antes,
            tabla_resultado=despues,
            pivote={'fila': fila, 'columna': col},
        ))

    # Factibilidad: las artificiales deben valer 0 en la solución final
    artificiales_positivas = [v for i, v in enumerate(base, start=1) if v.startswith('A') and not tab[i][-1].es_cero()]
    if artificiales_positivas:
        pasos.append(_diagnostico_infactible(tab, base, columnas, arts_restriccion, pasos[0]['formulas'], 4 + k))
        return pasos, ('El problema no tiene solución factible: la variable artificial '
                       f'{", ".join(artificiales_positivas)} queda positiva. '
                       'Revisa el diagnóstico al final del procedimiento.')

    # Último paso: solución óptima
    valores = {nombre_col: F(0) for nombre_col in columnas[1:-1]}
    for i, variable in enumerate(base, start=1):
        valores[variable] = tab[i][-1].a
    z_optimo = tab[0][-1].a

    formulas = [f'${a_latex(nombre_col)} = {_fmt_numero(valor)}$' for nombre_col, valor in valores.items()]
    formulas.append(f'$Z = {_fmt_numero(z_optimo)}$')

    pasos.append(_paso(
        f'Paso {4 + k}: Solución óptima',
        '<p>No quedan coeficientes que mejoren la función objetivo, así que la solución es óptima.</p>'
        '<p>Las variables artificiales valen 0, por lo que la solución es válida para el problema original.</p>',
        formulas=formulas,
        tabla=serializar(tab, base, columnas),
    ))

    return pasos, None


def leer_numero(texto, contexto):
    try:
        return F(texto.strip().replace(',', '.'))
    except (ValueError, ZeroDivisionError, AttributeError):
        raise ValueError(f'El valor "{texto}" en {contexto} no es un número válido.')


def leer_formulario(form):
    xs = form.getlist('r_x[]')
    ys = form.getlist('r_y[]')
    ops = form.getlist('r_op[]')
    cs = form.getlist('r_c[]')
    return {
        'tipo_opt': form.get('tipo_opt', 'min'),
        'z': [form.get('z_x', ''), form.get('z_y', '')],
        'restricciones': [
            {'a': [x, y], 'op': op, 'c': c} for x, y, op, c in zip(xs, ys, ops, cs)
        ],
    }


def convertir_datos(datos):
    """Pasa los textos del formulario a números exactos y valida los datos."""
    tipo = datos['tipo_opt']
    if tipo not in ('min', 'max'):
        raise ValueError('El tipo de optimización debe ser maximizar o minimizar.')

    c = [leer_numero(t, 'la función objetivo') for t in datos['z']]

    if not datos['restricciones']:
        raise ValueError('Agrega al menos una restricción.')

    restricciones = []
    for i, r in enumerate(datos['restricciones'], start=1):
        if r['op'] not in ('<=', '>=', '='):
            raise ValueError(f'El operador de la restricción {i} no es válido.')
        a = [leer_numero(t, f'la restricción {i}') for t in r['a']]
        b = leer_numero(r['c'], f'la restricción {i}')
        restricciones.append((a, r['op'], b))

    return tipo, c, restricciones


@gran_m_bp.route('/', methods=['GET', 'POST'])
def vista_principal():
    datos = DATOS_EJEMPLO
    pasos = []
    error = None

    if request.method == 'POST':
        datos = leer_formulario(request.form)
        try:
            tipo, c, restricciones = convertir_datos(datos)
            pasos, error = resolver(tipo, c, restricciones)
        except ValueError as e:
            error = str(e)

    return render_template(
        'metodo_gran_m/index.html',
        datos=datos,
        pasos=pasos,
        error=error,
    )
