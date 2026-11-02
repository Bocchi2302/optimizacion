# blueprints/grafico_conclusion.py
"""
Redacta la conclusión del ejercicio a partir de la solución y del enunciado.

Usa los nombres que la persona (o el extractor) le dio a las variables, a Z y a
cada restricción («mesas», «la ganancia total», «horas de carpintería») para que
la conclusión hable del problema real y no solo de X1 y X2.

Además de la decisión óptima analiza:
* qué restricciones se agotan (las que realmente limitan) y cuáles tienen holgura,
* el precio sombra de cada límite (cuánto cambiaría Z con una unidad más),
* y, si no hay solución, qué restricciones se contradicen entre sí.
Todo con aritmética exacta (Fraction).
"""
from fractions import Fraction
from itertools import combinations

from .grafico_solver import SIMBOLO, fmt, fmt_exacto, resolver

_ARTICULOS = ('el ', 'la ', 'los ', 'las ')


# ── Pequeños ayudantes de redacción ─────────────────────────────────────────
def _de(frase):
    """'de la ganancia' / 'del costo' (contrae «de el»)."""
    return 'del ' + frase[3:] if frase.lower().startswith('el ') else 'de ' + frase


def _sin_articulo(frase):
    f = frase.strip()
    for a in _ARTICULOS:
        if f.lower().startswith(a):
            return f[len(a):]
    return f


def _mayuscula(frase):
    return frase[:1].upper() + frase[1:] if frase else frase


def _lista(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' y ' + items[-1]


def _nombre_var(sol, i):
    return sol['nombres'][i] or f'X{i + 1}'


def _etq(r):
    return f'{r.nombre} ({r.rotulo})' if r.rotulo else r.nombre


def _cantidad(sol, i, valor):
    """'2 mesas' si la variable tiene nombre; 'X1 = 2' si no."""
    if sol['nombres'][i]:
        return f'{fmt_exacto(valor)} {sol["nombres"][i]}'
    return f'X{i + 1} = {fmt_exacto(valor)}'


def _objetivo(sol):
    return sol.get('objetivo_nombre', '').strip()


def _valor_extremo(sol):
    extremo = 'máximo' if sol['tipo'] == 'max' else 'mínimo'
    obj = _objetivo(sol)
    return f'el valor {extremo} {_de(obj) if obj else "de Z"}'


# ── Análisis del óptimo ─────────────────────────────────────────────────────
def _analizar_recursos(sol, o):
    """Uso de cada restricción en el punto óptimo `o`."""
    filas = []
    for r in sol['usuario']:
        if r.a == 0 and r.b == 0:
            continue
        usado = r.a * o['x'] + r.b * o['y']
        if r.op == '<=':
            holgura, estado = r.c - usado, None
            estado = 'agotado' if holgura == 0 else 'holgura'
        elif r.op == '>=':
            holgura = usado - r.c
            estado = 'justo' if holgura == 0 else 'superado'
        else:
            holgura, estado = Fraction(0), 'igualdad'

        fraccion = float(usado / r.c) if r.c > 0 and usado >= 0 else None
        calculo = (f'{fmt(r.a)}·({fmt(o["x"])}) + {fmt(r.b)}·({fmt(o["y"])})'
                   .replace('+ -', '− ')) + f' = {fmt(usado)}'
        if r.op == '<=':
            mensaje = ('Se agota por completo' if estado == 'agotado'
                       else f'Sobran {fmt_exacto(holgura)} sin usar')
        elif r.op == '>=':
            mensaje = ('Cumple justo el mínimo exigido' if estado == 'justo'
                       else f'Supera el mínimo en {fmt_exacto(holgura)}')
        else:
            mensaje = 'Se cumple exactamente'
        filas.append({
            'restriccion': r, 'nombre': r.nombre, 'rotulo': r.rotulo, 'texto': r.texto,
            'indice': sol['rectas'].index(r), 'usado': usado, 'limite': r.c, 'holgura': holgura,
            'estado': estado, 'mensaje': mensaje, 'calculo': calculo,
            'ancho': None if fraccion is None else max(0.0, min(100.0, fraccion * 100)),
            'exceso': fraccion is not None and r.op == '>=' and fraccion > 1,
            'detalle': f'{fmt_exacto(usado)} frente a {fmt(r.c)}',
        })
    return filas


def _precios_sombra(sol, o):
    """
    Cuánto cambia Z si el lado derecho de cada restricción activa sube una unidad.
    Solo cuando el óptimo está definido por exactamente dos restricciones activas
    (no degenerado): se resuelve  λ₁a₁ + λ₂a₂ = zx,  λ₁b₁ + λ₂b₂ = zy  con Cramer.
    """
    activas = []
    for r in sol['rectas']:
        if r.cumple(o['x'], o['y']) and r.valor(o['x'], o['y']) == r.c:
            activas.append((r.a, r.b, r))
    if o['x'] == 0:
        activas.append((Fraction(1), Fraction(0), 'X1'))
    if o['y'] == 0:
        activas.append((Fraction(0), Fraction(1), 'X2'))
    if len(activas) != 2:
        return [], len(activas) > 2
    (a1, b1, r1), (a2, b2, r2) = activas
    det = a1 * b2 - a2 * b1
    if det == 0:
        return [], False
    zx, zy = sol['zx'], sol['zy']
    lam = [(zx * b2 - zy * a2) / det, (a1 * zy - b1 * zx) / det]
    return [(ref, lam_i) for (_, _, ref), lam_i in zip(activas, lam) if lam_i != 0], False


def _frases_sensibilidad(sol, precios):
    frases = []
    for ref, lam in precios:
        sube = lam > 0
        cambio = fmt_exacto(abs(lam))
        if isinstance(ref, str):                    # eje: la variable vale 0 en el óptimo
            i = 0 if ref == 'X1' else 1
            nombre = _nombre_var(sol, i)
            frases.append(
                f'Hoy no se incluye {nombre} (vale 0). Si se obligara a incluir una unidad, '
                f'Z {"subiría" if sube else "bajaría"} {cambio}: por eso no conviene.')
            continue
        nuevo = ref.c + 1
        frases.append(
            f'Si {_lado_derecho(ref)} aumentara una unidad (de {fmt(ref.c)} a {fmt(nuevo)}), '
            f'Z {"aumentaría" if sube else "disminuiría"} en {cambio}.')
    return frases


def _lado_derecho(ref):
    """Cómo se llama el lado derecho según el tipo de restricción."""
    if ref.op == '<=':
        return f'el límite de {_etq(ref)}'
    if ref.op == '>=':
        return f'el mínimo exigido en {_etq(ref)}'
    return f'el valor exigido en {_etq(ref)}'


def _accion_que_mejora(sol, ref, lam):
    """
    Qué hacer con el lado derecho de `ref` para mejorar Z, según el signo del precio sombra:
    al maximizar conviene subirlo si λ > 0; al minimizar, si λ < 0.
    Devuelve (acción, 'de más' | 'de menos').
    """
    subir = (lam > 0) == (sol['tipo'] == 'max')
    if ref.op == '<=':
        accion = 'ampliar el límite de' if subir else 'reducir el límite de'
    elif ref.op == '>=':
        accion = 'aumentar el mínimo exigido en' if subir else 'reducir el mínimo exigido en'
    else:
        accion = 'subir el valor exigido en' if subir else 'bajar el valor exigido en'
    return f'{accion} {_etq(ref)}', 'de más' if subir else 'de menos'


def _comparar_vertices(sol):
    """Barras de Z en cada vértice y la frase «ninguno supera…» (por qué este y no otro)."""
    vs = sol['vertices']
    if len(vs) < 2:
        return [], ''
    maximizar = sol['tipo'] == 'max'
    ordenados = sorted(vs, key=lambda e: e['z'], reverse=maximizar)
    tope = max(abs(e['z']) for e in vs) or Fraction(1)
    filas = [{
        'punto': f'({fmt(e["x"])}, {fmt(e["y"])})', 'z': fmt(e['z']), 'optimo': e['optimo'],
        'ancho': float(abs(e['z']) / tope * 100), 'negativo': e['z'] < 0,
    } for e in ordenados]
    otros = []
    for e in ordenados:
        if not e['optimo'] and fmt(e['z']) not in otros:
            otros.append(fmt(e['z']))
    if not otros:
        return filas, 'Todos los vértices dan el mismo valor de Z.'
    mejor = fmt(sol['optimos'][0]['z'])
    frase = (f'Los demás vértices dan Z = {_lista(otros)}: ninguno {"supera" if maximizar else "baja de"} {mejor}, '
             f'por eso el óptimo es {" y ".join("(" + fmt(e["x"]) + ", " + fmt(e["y"]) + ")" for e in sol["optimos"])}.')
    return filas, frase


def _verificacion(o, recursos):
    partes = [f'{_etq(f["restriccion"])}: {fmt(f["usado"])} {SIMBOLO[f["restriccion"].op]} {fmt(f["limite"])} ✔' for f in recursos]
    return (f'Comprobación: el punto ({fmt(o["x"])}, {fmt(o["y"])}) cumple todas las restricciones — '
            + '; '.join(partes) + '; y X1 ≥ 0, X2 ≥ 0 ✔.')


def _recomendaciones(sol, precios, recursos):
    """Qué conviene hacer para mejorar el resultado, según qué restricciones limitan."""
    frases = []
    maximizar = sol['tipo'] == 'max'
    utiles = [(ref, lam) for ref, lam in precios if not isinstance(ref, str)]
    if utiles:
        ref, lam = max(utiles, key=lambda t: abs(t[1]))
        valor = abs(lam)
        accion, sentido = _accion_que_mejora(sol, ref, lam)
        frases.append(f'Para {"aumentar" if maximizar else "reducir"} Z, lo que más conviene es {accion}: '
                      f'cada unidad {sentido} mejora el resultado en {fmt_exacto(valor)}.')
        for otra, l2 in sorted((t for t in utiles if t[0] is not ref), key=lambda t: -abs(t[1])):
            v = abs(l2)
            comparativo = 'aunque menos' if v < valor else 'igual de útil'
            accion2, _ = _accion_que_mejora(sol, otra, l2)
            frases.append(f'También ayudaría {accion2} ({comparativo}): cada unidad mejora el resultado en {fmt_exacto(v)}.')
    elif any(f['estado'] in ('agotado', 'justo') for f in recursos):
        limitantes = [f['restriccion'] for f in recursos if f['estado'] in ('agotado', 'justo')]
        frases.append(f'El resultado solo puede mejorar relajando {_lista([_etq(r) for r in limitantes])}, '
                      f'que son las que definen el óptimo.')
    sobran = [f for f in recursos if f['estado'] in ('holgura', 'superado')]
    if sobran:
        frases.append(f'No tiene sentido invertir en {_lista([_etq(f["restriccion"]) for f in sobran])}: '
                      f'ya {"sobra" if len(sobran) == 1 else "sobran"} y no limita{"" if len(sobran) == 1 else "n"} la decisión.')
    return frases


# ── Conflictos (problemas sin solución) ─────────────────────────────────────
def _conflicto_minimo(sol):
    """Menor grupo de restricciones que ya se contradicen entre sí (hasta 3)."""
    if sol['contradiccion'] is not None:
        return [sol['contradiccion']]
    base = {'tipo': 'max', 'zx': Fraction(0), 'zy': Fraction(0), 'zk': Fraction(0),
            'nombres': ['', ''], 'contexto': ''}
    for tamano in (1, 2, 3):
        for grupo in combinations(sol['rectas'], tamano):
            if not resolver(dict(base, restricciones=list(grupo)))['factible']:
                return list(grupo)
    return []


# ── Redacción ───────────────────────────────────────────────────────────────
def _conclusion_optima(sol):
    o = sol['optimos'][0]
    maximizar = sol['tipo'] == 'max'
    objetivo = _objetivo(sol) or 'Z'
    recursos = _analizar_recursos(sol, o)

    decision = [
        {'etiqueta': f'X{i + 1}', 'nombre': sol['nombres'][i] or f'X{i + 1}',
         'valor': fmt_exacto(v), 'numero': float(v), 'cero': v == 0,
         'con_nombre': bool(sol['nombres'][i])}
        for i, v in enumerate((o['x'], o['y']))
    ]
    frase_decision = (' y '.join(_cantidad(sol, i, v) for i, v in enumerate((o['x'], o['y']))))

    activas = [_etq(r) for r in sol['rectas'] if r.valor(o['x'], o['y']) == r.c]
    activas += [f'el eje {n} ({n} = 0)' for n, v in (('X1', o['x']), ('X2', o['y'])) if v == 0]
    parrafos = [
        f'El óptimo se alcanza en el vértice ({fmt(o["x"])}, {fmt(o["y"])}) de la región factible, '
        f'donde se cruzan {_lista(activas)}.'
    ]

    agotados = [f for f in recursos if f['estado'] == 'agotado']
    justos = [f for f in recursos if f['estado'] == 'justo']
    holguras = [f for f in recursos if f['estado'] == 'holgura']
    superados = [f for f in recursos if f['estado'] == 'superado']

    if agotados:
        n = len(agotados)
        parrafos.append(
            f'{"Se agota" if n == 1 else "Se agotan"} por completo {_lista([_etq(f["restriccion"]) for f in agotados])}: '
            f'{"es" if n == 1 else "son"} {"el factor" if n == 1 else "los factores"} que realmente '
            f'{"limita" if n == 1 else "limitan"} la decisión: mientras no se {"amplíe" if n == 1 else "amplíen"}, '
            f'no se puede mejorar Z.')
    if justos:
        parrafos.append(
            f'Se {"cumple" if len(justos) == 1 else "cumplen"} justo en el mínimo exigido: '
            f'{_lista([_etq(f["restriccion"]) for f in justos])}. Mientras se exija ese mínimo, no se puede mejorar Z.')
    if holguras:
        parrafos.append(
            f'En cambio, {"no limita" if len(holguras) == 1 else "no limitan"} la decisión: ' + _lista(
                [f'{_etq(f["restriccion"])}, con {fmt_exacto(f["holgura"])} de sobra (se usan {fmt_exacto(f["usado"])} de {fmt(f["limite"])})'
                 for f in holguras]) + '.')
    if superados:
        parrafos.append('Se supera el mínimo exigido en ' + _lista(
            [f'{_etq(f["restriccion"])} (por {fmt_exacto(f["holgura"])})' for f in superados]) + '.')

    ceros = [i for i, v in enumerate((o['x'], o['y'])) if v == 0]
    if ceros:
        nombres = _lista([_nombre_var(sol, i) for i in ceros])
        parrafos.append(
            f'En el óptimo {nombres} {"vale" if len(ceros) == 1 else "valen"} 0: con estas condiciones '
            f'no conviene incluir{"lo" if len(ceros) == 1 else "los"}.')

    if sol['multiples']:
        if len(sol['optimos']) > 1:
            puntos = ' y '.join(f'({fmt(e["x"])}, {fmt(e["y"])})' for e in sol['optimos'])
            parrafos.append(
                f'Esta no es la única solución: {puntos} dan el mismo valor de Z, y también todos los puntos del '
                f'segmento que los une. Se puede elegir entre ellos con otro criterio (por ejemplo, el que '
                f'deje más recursos sin usar).')
        else:
            parrafos.append('Esta no es la única solución: desde este punto la región continúa en una dirección '
                            'donde Z no cambia, y todos esos puntos también son óptimos.')

    precios, degenerado = _precios_sombra(sol, o)
    sensibilidad = _frases_sensibilidad(sol, precios)

    cuidados = []
    fraccionaria = [i for i, v in enumerate((o['x'], o['y'])) if Fraction(v).denominator != 1]
    if fraccionaria:
        cuidados.append(
            'La solución tiene valores fraccionarios. Si ' + _lista([_nombre_var(sol, i) for i in fraccionaria]) +
            ' solo pueden ser cantidades enteras, este resultado es una cota y habría que buscar la mejor '
            'solución entera (programación entera).')
    if degenerado:
        cuidados.append('Más de dos restricciones se cruzan en el óptimo (solución degenerada), por eso no se '
                        'calculan los precios sombra: no son únicos.')
    if not sol['acotada']:
        cuidados.append('La región no tiene límite en alguna dirección, pero el óptimo existe porque en esa '
                        'dirección Z no mejora.')

    comparacion, frase_comparacion = _comparar_vertices(sol)
    unica = not sol['multiples']
    respuesta_final = (
        f'Se concluye que, para {"maximizar" if maximizar else "minimizar"} {objetivo}, '
        f'{"se debe elegir" if unica else "una de las decisiones óptimas es elegir"} {frase_decision}, '
        f'con lo que {_valor_extremo(sol)} es Z = {fmt_exacto(o["z"])}.')

    return {
        'estado': 'optimo',
        'respuesta_final': respuesta_final,
        'comparacion': comparacion, 'frase_comparacion': frase_comparacion,
        'verificacion': _verificacion(o, recursos),
        'recomendaciones': _recomendaciones(sol, precios, recursos),
        'titular': ('Una de las mejores decisiones' if sol['multiples'] else 'La mejor decisión') + f': {frase_decision}',
        'decision': decision,
        'objetivo': {
            'etiqueta': _mayuscula(_sin_articulo(_objetivo(sol))) if _objetivo(sol) else 'Z',
            'extremo': 'máximo' if maximizar else 'mínimo',
            'valor': fmt_exacto(o['z']), 'numero': float(o['z']),
        },
        'recursos': recursos,
        'parrafos': parrafos,
        'sensibilidad': sensibilidad,
        'cuidados': cuidados,
    }


def _conclusion_no_acotada(sol):
    d = sol['rayo_mejora']
    crece = sol['tipo'] == 'max'
    progreso = sol['zx'] * d[0] + sol['zy'] * d[1]
    movimiento = [_nombre_var(sol, i) for i, c in enumerate(d) if c > 0]
    objetivo = _objetivo(sol) or 'Z'
    parrafos = [
        f'No existe un {"máximo" if crece else "mínimo"} finito. Al avanzar en la dirección ({fmt(d[0])}, {fmt(d[1])}) '
        f'(es decir, aumentando {_lista(movimiento)}) se siguen cumpliendo todas las restricciones, y {objetivo} '
        f'{"crece" if crece else "decrece"} {fmt_exacto(abs(progreso))} por cada unidad que se avanza: nada lo detiene.',
        'En un problema real esto indica que al modelo le falta una restricción: por ejemplo, un límite de '
        'recursos, de capacidad o de demanda. Revisa si el enunciado trae algún dato que no se escribió en el modelo.',
    ]
    return {
        'estado': 'no_acotado',
        'respuesta_final': (f'Se concluye que el problema no tiene un {"máximo" if crece else "mínimo"} finito: '
                            f'{objetivo} puede {"crecer" if crece else "decrecer"} tanto como se quiera sin violar ninguna restricción.'),
        'comparacion': [], 'frase_comparacion': '', 'verificacion': '', 'recomendaciones': [
            'Agrega al modelo la restricción que falta (un límite de recursos, de capacidad o de demanda) y vuelve a resolverlo.'],
        'titular': f'El modelo no tiene un {"máximo" if crece else "mínimo"} finito',
        'decision': [], 'objetivo': None, 'recursos': [],
        'parrafos': parrafos, 'sensibilidad': [],
        'cuidados': ['Los vértices de la tabla no son el óptimo: son solo las esquinas de una región que sigue sin fin.'],
    }


def _conclusion_infactible(sol):
    grupo = _conflicto_minimo(sol)
    if len(grupo) == 1:
        r = grupo[0]
        causa = (f'{_etq(r)} ({r.texto}) no depende de las variables y es falsa.' if r.a == 0 and r.b == 0
                 else f'{_etq(r)} ({r.texto}) no puede cumplirse ni siquiera por sí sola, porque X1 y X2 no pueden ser negativos.')
    elif len(grupo) == 2:
        a, b = grupo
        causa = (f'{_etq(a)} exige {a.texto}, mientras que {_etq(b)} exige {b.texto}: '
                 f'no existe ningún par de valores que cumpla las dos a la vez.')
    elif len(grupo) == 3:
        causa = (f'{_lista([_etq(r) for r in grupo])} no pueden cumplirse juntas '
                 f'({"; ".join(r.texto for r in grupo)}), aunque cada pareja sí sea compatible.')
    else:
        causa = 'Las restricciones, en conjunto, se contradicen entre sí.'
    parrafos = [
        f'El problema no tiene solución: no existe ninguna decisión que cumpla todas las restricciones a la vez. {causa}',
        'Revisa los datos del enunciado: ¿algún límite quedó demasiado bajo o algún mínimo demasiado alto, o se '
        'invirtió un signo (≤ por ≥)? Para obtener una solución hay que relajar al menos una de las restricciones implicadas.',
    ]
    return {
        'estado': 'infactible', 'titular': 'El modelo no tiene solución',
        'respuesta_final': 'Se concluye que el problema no tiene solución: ninguna decisión cumple todas las restricciones a la vez.',
        'comparacion': [], 'frase_comparacion': '', 'verificacion': '', 'recomendaciones': [
            'Relaja al menos una de las restricciones que chocan (sube un límite o baja un mínimo) y vuelve a resolver.'],
        'decision': [], 'objetivo': None, 'recursos': [], 'parrafos': parrafos,
        'sensibilidad': [], 'cuidados': [], 'conflicto': [r.nombre for r in grupo],
    }


def redactar(sol):
    """Conclusión estructurada (para la plantilla) y en texto plano (para copiar)."""
    if sol['estado'] == 'optimo':
        c = _conclusion_optima(sol)
    elif sol['estado'] == 'no_acotado':
        c = _conclusion_no_acotada(sol)
    else:
        c = _conclusion_infactible(sol)
    c['texto_plano'] = _texto_plano(c)
    return c


def _texto_plano(c):
    lineas = [c['titular'], '', f'RESPUESTA: {c["respuesta_final"]}', '']
    lineas += c['parrafos']
    if c.get('comparacion'):
        lineas += ['', '¿Por qué este y no otro?']
        lineas += [f'- {f["punto"]}: Z = {f["z"]}{"  ← óptimo" if f["optimo"] else ""}' for f in c['comparacion']]
        lineas.append(c['frase_comparacion'])
    if c.get('recursos'):
        lineas += ['', 'Uso de las restricciones en el óptimo:']
        lineas += [f'- {f["nombre"]}{" (" + f["rotulo"] + ")" if f["rotulo"] else ""}: {f["texto"]} → '
                   f'{f["mensaje"]} ({f["detalle"]})' for f in c['recursos']]
    if c['sensibilidad']:
        lineas += ['', 'Qué pasaría si los límites cambian:']
        lineas += [f'- {t}' for t in c['sensibilidad']]
    if c.get('recomendaciones'):
        lineas += ['', 'Recomendación:']
        lineas += [f'- {t}' for t in c['recomendaciones']]
    if c['cuidados']:
        lineas += ['', 'Ten en cuenta:']
        lineas += [f'- {t}' for t in c['cuidados']]
    if c.get('verificacion'):
        lineas += ['', c['verificacion']]
    return '\n'.join(lineas)
