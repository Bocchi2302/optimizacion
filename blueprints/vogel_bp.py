"""Método de Aproximación de Vogel (VAM) para problemas de transporte.

Además de la solución inicial factible, registra cada iteración con los pasos
que se enseñan en clase:

1. Verificar el balance (oferta total vs. demanda total).
2. Calcular las penalizaciones (segundo menor − menor) de filas y columnas.
3. Elegir la mayor penalización.
4. Elegir la celda de menor costo dentro de esa fila o columna.
5. Asignar la mayor cantidad posible: min(oferta, demanda).
6. Actualizar oferta y demanda.
7. Eliminar la fila o columna satisfecha.
8. Recalcular penalizaciones con la tabla reducida.
9. Repetir hasta satisfacer todas las ofertas y demandas.

Con el enunciado (contexto) y los nombres que dé la persona redacta un
análisis del resultado: plan de envíos, costo, rutas, ficticios, degeneración
y una comprobación rápida de optimalidad con los multiplicadores u-v.
"""
import re
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request

vogel_bp = Blueprint("vogel_bp", __name__)
MAX_DIMENSION = 10
MAX_CONTEXTO = 4000
MAX_NOMBRE = 40


# ── Formato ─────────────────────────────────────────────────────────────────
def fmt(valor):
    """Número legible: 7 en vez de 7.00, 2.5 en vez de 2.50, sin notación científica."""
    if valor is None:
        return "—"
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    if valor == valor.to_integral_value():
        return str(int(valor))
    return format(valor.quantize(Decimal("0.0001")).normalize(), "f")


def _lista(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def _suma_texto(valores):
    return " + ".join(fmt(v) for v in valores)


# ── Solver ──────────────────────────────────────────────────────────────────
def _penalizacion(costos, celdas, nombre):
    """Penalización de una fila o columna con las celdas que siguen activas."""
    valores = [costos[i][j] for i, j in celdas]
    ordenados = sorted(valores)
    if len(ordenados) > 1:
        menor, segundo = ordenados[0], ordenados[1]
        valor, unico = segundo - menor, False
    else:
        menor, segundo = ordenados[0], None
        valor, unico = ordenados[0], True
    return {
        "nombre": nombre,
        "costos": valores,
        "menor": menor,
        "segundo": segundo,
        "valor": valor,
        "unico": unico,
    }


def _completar_base(m, n, celdas):
    """Árbol generador con m + n − 1 celdas (añade ceros si la solución es degenerada)."""
    padre = list(range(m + n))

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra == rb:
            return False
        padre[ra] = rb
        return True

    base = []
    for i, j in celdas:
        if unir(i, m + j):
            base.append((i, j))
    for i in range(m):
        for j in range(n):
            if len(base) == m + n - 1:
                return base
            if unir(i, m + j):
                base.append((i, j))
    return base


def comprobar_optimalidad(costos, asignaciones):
    """Multiplicadores u-v y costos reducidos Δij = cij − ui − vj de las celdas vacías."""
    m, n = len(costos), len(costos[0])
    ocupadas = [(i, j) for i in range(m) for j in range(n) if asignaciones[i][j] > 0]
    base = _completar_base(m, n, ocupadas)
    u, v = [None] * m, [None] * n
    u[0] = Decimal(0)
    cambio = True
    while cambio:
        cambio = False
        for i, j in base:
            if u[i] is not None and v[j] is None:
                v[j] = costos[i][j] - u[i]
                cambio = True
            elif v[j] is not None and u[i] is None:
                u[i] = costos[i][j] - v[j]
                cambio = True
    if any(x is None for x in u) or any(x is None for x in v):
        return None
    deltas = [
        {"i": i, "j": j, "delta": costos[i][j] - u[i] - v[j]}
        for i in range(m)
        for j in range(n)
        if (i, j) not in base
    ]
    negativos = sorted((d for d in deltas if d["delta"] < 0), key=lambda d: d["delta"])
    return {
        "u": u,
        "v": v,
        "deltas": deltas,
        "optima": not negativos,
        "alternativa": any(d["delta"] == 0 for d in deltas),
        "mejor_mejora": negativos[0] if negativos else None,
    }


def resolver_vogel(costos, oferta, demanda, nombres_origen=None, nombres_destino=None):
    """Calcula una solución inicial factible usando el método de Vogel, iteración por iteración."""
    filas = len(oferta)
    columnas = len(demanda)
    if filas == 0 or columnas == 0:
        raise ValueError("La tabla debe tener al menos un origen y un destino.")
    if len(costos) != filas or any(len(fila) != columnas for fila in costos):
        raise ValueError("Las dimensiones de costos, oferta y demanda no coinciden.")
    if any(valor < 0 for valor in oferta) or any(valor < 0 for valor in demanda):
        raise ValueError("La oferta y la demanda no pueden ser negativas.")

    costos = [fila[:] for fila in costos]
    oferta_restante = oferta[:]
    demanda_restante = demanda[:]
    nombres_origen = list(nombres_origen or [f"Origen {i + 1}" for i in range(filas)])
    nombres_destino = list(nombres_destino or [f"Destino {j + 1}" for j in range(columnas)])

    # ── Paso 1: verificar el balance ───────────────────────────────────────
    total_oferta = sum(oferta_restante, Decimal(0))
    total_demanda = sum(demanda_restante, Decimal(0))
    if total_oferta == 0 and total_demanda == 0:
        raise ValueError("La oferta y la demanda no pueden ser todas cero.")
    balance = {
        "oferta_total": total_oferta,
        "demanda_total": total_demanda,
        "suma_oferta": _suma_texto(oferta),
        "suma_demanda": _suma_texto(demanda),
        "balanceado": total_oferta == total_demanda,
        "ficticio": None,
        "diferencia": abs(total_oferta - total_demanda),
    }
    if total_oferta < total_demanda:
        costos.append([Decimal(0)] * columnas)
        oferta_restante.append(total_demanda - total_oferta)
        nombres_origen.append("Origen ficticio")
        balance["ficticio"] = "origen"
    elif total_oferta > total_demanda:
        costos = [fila + [Decimal(0)] for fila in costos]
        demanda_restante.append(total_oferta - total_demanda)
        nombres_destino.append("Destino ficticio")
        balance["ficticio"] = "destino"

    m, n = len(oferta_restante), len(demanda_restante)
    oferta_balanceada = oferta_restante[:]
    demanda_balanceada = demanda_restante[:]
    asignaciones = [[Decimal(0)] * n for _ in range(m)]
    # Un origen sin oferta o un destino sin demanda no participa desde el inicio.
    fila_activa = [cantidad > 0 for cantidad in oferta_restante]
    columna_activa = [cantidad > 0 for cantidad in demanda_restante]
    iteraciones = []
    pasos = []

    while any(fila_activa) and any(columna_activa):
        filas_act = [i for i in range(m) if fila_activa[i]]
        cols_act = [j for j in range(n) if columna_activa[j]]

        # ── Paso 2 / 8: penalizaciones ─────────────────────────────────────
        pen_filas = [None] * m
        pen_cols = [None] * n
        for i in filas_act:
            pen_filas[i] = _penalizacion(costos, [(i, j) for j in cols_act], nombres_origen[i])
        for j in cols_act:
            pen_cols[j] = _penalizacion(costos, [(i, j) for i in filas_act], nombres_destino[j])

        # ── Pasos 3 y 4: mayor penalización y celda de menor costo ─────────
        candidatos = []
        for tipo, indices in (("fila", filas_act), ("columna", cols_act)):
            for k in indices:
                celdas = [(k, j) for j in cols_act] if tipo == "fila" else [(i, k) for i in filas_act]
                minimo = min(costos[i][j] for i, j in celdas)
                minimas = [c for c in celdas if costos[c[0]][c[1]] == minimo]
                celda = min(
                    minimas,
                    key=lambda c: (-min(oferta_restante[c[0]], demanda_restante[c[1]]), c),
                )
                pen = (pen_filas[k] if tipo == "fila" else pen_cols[k])["valor"]
                candidatos.append({
                    "tipo": tipo,
                    "indice": k,
                    "nombre": nombres_origen[k] if tipo == "fila" else nombres_destino[k],
                    "penalizacion": pen,
                    "costo_min": minimo,
                    "cantidad": min(oferta_restante[celda[0]], demanda_restante[celda[1]]),
                    "celda": celda,
                    "celdas": celdas,
                    "empate_celda": len(minimas) > 1,
                })

        max_pen = max(c["penalizacion"] for c in candidatos)
        empatados = [c for c in candidatos if c["penalizacion"] == max_pen]
        desempate = []
        if len(empatados) > 1:
            # Desempate: menor costo disponible, luego mayor cantidad asignable,
            # y si persiste se prefiere la fila y, dentro del mismo tipo, la primera.
            menor_costo = min(c["costo_min"] for c in empatados)
            por_costo = [c for c in empatados if c["costo_min"] == menor_costo]
            mayor_cant = max(c["cantidad"] for c in por_costo)
            por_cant = [c for c in por_costo if c["cantidad"] == mayor_cant]
            elegido = min(por_cant, key=lambda c: (c["tipo"] != "fila", c["indice"]))
            if len({c["celda"] for c in empatados}) == 1:
                desempate.append("Todas llevan a la misma celda, así que da igual cuál se tome.")
            else:
                if len(por_costo) < len(empatados):
                    desempate.append(
                        f"Se desempata eligiendo la de menor costo disponible ({fmt(menor_costo)})."
                    )
                if len(por_cant) < len(por_costo):
                    desempate.append(
                        ("Entre las que tienen ese costo" if len(por_costo) < len(empatados)
                         else f"Todas tienen el mismo costo mínimo ({fmt(menor_costo)}), así que")
                        + f" se prefiere la que permite asignar más unidades ({fmt(mayor_cant)})."
                    )
                if len({c["celda"] for c in por_cant}) > 1:
                    desempate.append(
                        f"Aún quedan empatadas {_lista([c['nombre'] for c in por_cant])}; se toma "
                        f"{elegido['nombre']} (cualquiera de ellas es válida)."
                    )
        else:
            elegido = empatados[0]

        i, j = elegido["celda"]
        costos_linea = [
            {
                "origen": nombres_origen[a],
                "destino": nombres_destino[b],
                "costo": costos[a][b],
                "elegida": (a, b) == (i, j),
            }
            for a, b in elegido["celdas"]
        ]

        # ── Paso 5: asignar la mayor cantidad posible ──────────────────────
        oferta_antes = oferta_restante[i]
        demanda_antes = demanda_restante[j]
        cantidad = min(oferta_antes, demanda_antes)
        oferta_disp = oferta_restante[:]
        demanda_disp = demanda_restante[:]
        asignaciones[i][j] += cantidad

        # ── Paso 6: actualizar oferta y demanda ────────────────────────────
        oferta_restante[i] -= cantidad
        demanda_restante[j] -= cantidad

        # ── Paso 7: eliminar fila o columna satisfecha ─────────────────────
        eliminadas = []
        if oferta_restante[i] == 0:
            fila_activa[i] = False
            eliminadas.append({"tipo": "fila", "indice": i, "nombre": nombres_origen[i]})
        if demanda_restante[j] == 0:
            columna_activa[j] = False
            eliminadas.append({"tipo": "columna", "indice": j, "nombre": nombres_destino[j]})

        iteraciones.append({
            "numero": len(iteraciones) + 1,
            "filas_activas": [k in filas_act for k in range(m)],
            "columnas_activas": [k in cols_act for k in range(n)],
            "oferta_disp": oferta_disp,
            "demanda_disp": demanda_disp,
            "oferta_nueva": oferta_restante[:],
            "demanda_nueva": demanda_restante[:],
            "asignaciones": [fila[:] for fila in asignaciones],
            "pen_filas": pen_filas,
            "pen_cols": pen_cols,
            "max_pen": max_pen,
            "pen_filas_lista": [(nombres_origen[k], pen_filas[k]["valor"]) for k in filas_act],
            "pen_cols_lista": [(nombres_destino[k], pen_cols[k]["valor"]) for k in cols_act],
            "empatados": [
                {"tipo": c["tipo"], "nombre": c["nombre"], "costo_min": c["costo_min"], "cantidad": c["cantidad"]}
                for c in empatados
            ],
            "desempate": desempate,
            "empate_relevante": len({c["celda"] for c in empatados}) > 1,
            "ultima_celda": len(filas_act) == 1 and len(cols_act) == 1,
            "elegido": {"tipo": elegido["tipo"], "indice": elegido["indice"], "nombre": elegido["nombre"]},
            "costos_linea": costos_linea,
            "costo_min": elegido["costo_min"],
            "empate_celda": elegido["empate_celda"],
            "celda": (i, j),
            "origen": nombres_origen[i],
            "destino": nombres_destino[j],
            "cantidad": cantidad,
            "oferta_antes": oferta_antes,
            "demanda_antes": demanda_antes,
            "oferta_despues": oferta_restante[i],
            "demanda_despues": demanda_restante[j],
            "eliminadas": eliminadas,
            "filas_restantes": sum(fila_activa),
            "columnas_restantes": sum(columna_activa),
            "oferta_pendiente": sum((oferta_restante[k] for k in range(m) if fila_activa[k]), Decimal(0)),
            "demanda_pendiente": sum((demanda_restante[k] for k in range(n) if columna_activa[k]), Decimal(0)),
        })
        pasos.append({
            "numero": len(pasos) + 1,
            "tipo": "origen" if elegido["tipo"] == "fila" else "destino",
            "indice": elegido["indice"] + 1,
            "origen": nombres_origen[i],
            "destino": nombres_destino[j],
            "cantidad": cantidad,
            "costo_unitario": costos[i][j],
        })

    rutas = []
    for a in range(m):
        for b in range(n):
            if asignaciones[a][b] > 0:
                rutas.append({
                    "i": a,
                    "j": b,
                    "origen": nombres_origen[a],
                    "destino": nombres_destino[b],
                    "cantidad": asignaciones[a][b],
                    "costo": costos[a][b],
                    "subtotal": asignaciones[a][b] * costos[a][b],
                    "ficticia": (balance["ficticio"] == "origen" and a == m - 1)
                    or (balance["ficticio"] == "destino" and b == n - 1),
                })
    costo_total = sum((r["subtotal"] for r in rutas), Decimal(0))

    return {
        "costos": costos,
        "asignaciones": asignaciones,
        "origenes": nombres_origen,
        "destinos": nombres_destino,
        "oferta": oferta_balanceada,
        "demanda": demanda_balanceada,
        "pasos": pasos,
        "iteraciones": iteraciones,
        "balance": balance,
        "rutas": rutas,
        "costo_total": costo_total,
        "calculo_total": " + ".join(f"{fmt(r['cantidad'])}·{fmt(r['costo'])}" for r in rutas),
        "oferta_total": total_oferta,
        "demanda_total": total_demanda,
        "celdas_basicas": len(rutas),
        "celdas_requeridas": m + n - 1,
        "degenerada": len(rutas) < m + n - 1,
        "optimalidad": comprobar_optimalidad(costos, asignaciones),
    }


# ── Análisis guiado por el contexto ─────────────────────────────────────────
_PALABRAS_DISTANCIA = re.compile(r"\b(distancias?|kil[oó]metros?|km|millas?|recorrid[oa]s?)\b", re.I)
_PALABRAS_TIEMPO = re.compile(r"\b(tiempos?|horas?|minutos?)\b", re.I)
_PALABRAS_DINERO = re.compile(r"\bcostos?\b|\$|\bpesos\b|\bd[oó]lares\b|\btarifas?\b", re.I)
_PALABRAS_GANANCIA = re.compile(
    r"\b(ganancias?|utilidad(es)?|beneficios?|ingresos?|maximizar|maximice|maximizaci[oó]n)\b", re.I
)
_PREFIJOS_MONEDA = {"$", "us$", "cop", "cop$", "€", "usd", "s/", "£"}

_NOMBRE_TOTAL = {
    "costo": "costo total de transporte",
    "distancia": "distancia total recorrida",
    "tiempo": "tiempo total de transporte",
}
_ARTICULO = {"costo": "el", "distancia": "la", "tiempo": "el"}


def detectar_tipo_valor(contexto, elegido="auto"):
    """('costo' | 'distancia' | 'tiempo', detectado): lo elegido o lo que sugiere el enunciado."""
    if elegido in _NOMBRE_TOTAL:
        return elegido, False
    texto = contexto or ""
    if _PALABRAS_DINERO.search(texto):
        return "costo", False
    if _PALABRAS_DISTANCIA.search(texto):
        return "distancia", True
    if _PALABRAS_TIEMPO.search(texto):
        return "tiempo", True
    return "costo", False


def _con_unidad(valor, unidad):
    numero = fmt(valor)
    if not unidad:
        return numero
    if unidad.lower() in _PREFIJOS_MONEDA:
        return f"{unidad}{numero}" if unidad == "$" else f"{unidad} {numero}"
    return f"{numero} {unidad}"


def redactar_analisis(res, contexto="", unidad_envio="", unidad_valor="", tipo_valor="auto"):
    """Análisis del resultado en el lenguaje del problema real (reglas sobre los datos, sin IA)."""
    tipo, detectado = detectar_tipo_valor(contexto, tipo_valor)
    envio = unidad_envio or "unidades"
    nombre_total = _NOMBRE_TOTAL[tipo]
    el_total = f"{_ARTICULO[tipo]} {nombre_total}"

    def val(x):
        return _con_unidad(x, unidad_valor)

    def cant(x):
        return f"{fmt(x)} {envio}"

    balance = res["balance"]
    rutas_reales = [r for r in res["rutas"] if not r["ficticia"]]
    rutas_ficticias = [r for r in res["rutas"] if r["ficticia"]]
    m_real = len(res["origenes"]) - (1 if balance["ficticio"] == "origen" else 0)
    n_real = len(res["destinos"]) - (1 if balance["ficticio"] == "destino" else 0)
    bloques = []

    # 1. Plan de distribución por origen
    plan = []
    for i in range(m_real):
        envios = [r for r in rutas_reales if r["i"] == i]
        if not envios:
            plan.append(f"{res['origenes'][i]} no envía nada en este plan.")
            continue
        partes = [f"{cant(r['cantidad'])} a {r['destino']}" for r in envios]
        plan.append(f"Desde {res['origenes'][i]} se envían {_lista(partes)}.")
    bloques.append({"titulo": "Plan de distribución", "tipo": "plan", "parrafos": plan})

    # 2. Valor de la función objetivo
    unidades_reales = sum((r["cantidad"] for r in rutas_reales), Decimal(0))
    valor = [
        f"Con este plan {el_total} es {val(res['costo_total'])} "
        f"({res['calculo_total']} = {fmt(res['costo_total'])})."
    ]
    if any(r["ficticia"] for r in res["rutas"]):
        valor[0] += " Las rutas ficticias cuestan 0, así que no suman al total."

    if unidades_reales > 0:
        promedio = (res["costo_total"] / unidades_reales).quantize(Decimal("0.01"))
        valor.append(
            f"Se movilizan {cant(unidades_reales)} en total, con un promedio de {val(promedio)} "
            f"por cada una ({fmt(res['costo_total'])} ÷ {fmt(unidades_reales)})."
        )
    if rutas_reales and res["costo_total"] > 0:
        mayor = max(rutas_reales, key=lambda r: r["subtotal"])
        porcentaje = (mayor["subtotal"] / res["costo_total"] * 100).quantize(Decimal("0.1"))
        valor.append(
            f"La ruta que más pesa es {mayor['origen']} → {mayor['destino']}: aporta {val(mayor['subtotal'])}, "
            f"el {fmt(porcentaje)} % del total. Es la primera a revisar "
            + ("si se quiere negociar tarifas o buscar otra alternativa." if tipo == "costo"
               else "si se quiere buscar una alternativa más corta.")
        )
    bloques.append({"titulo": nombre_total[:1].upper() + nombre_total[1:], "tipo": "valor", "parrafos": valor})

    # 3. Rutas: cuántas se usan y qué pasó con la más barata
    total_rutas = m_real * n_real
    rutas = [
        f"Se usan {len(rutas_reales)} de las {total_rutas} rutas posibles; las otras "
        f"{total_rutas - len(rutas_reales)} quedan sin envíos."
    ]
    if total_rutas:
        i, j = min(
            ((a, b) for a in range(m_real) for b in range(n_real)),
            key=lambda c: (res["costos"][c[0]][c[1]], c),
        )
        nombre = f"{res['origenes'][i]} → {res['destinos'][j]}"
        if res["asignaciones"][i][j] > 0:
            rutas.append(
                f"La ruta más económica de la tabla ({nombre}, {val(res['costos'][i][j])} por unidad) sí se "
                f"aprovecha, con {cant(res['asignaciones'][i][j])}."
            )
        else:
            rutas.append(
                f"La ruta más económica de la tabla ({nombre}, {val(res['costos'][i][j])} por unidad) no se usa. "
                "Vogel no toma siempre la celda más barata: atiende primero la fila o columna con mayor "
                "penalización, es decir, donde sería más caro no usar su mejor ruta."
            )
    bloques.append({"titulo": "Rutas utilizadas", "tipo": "rutas", "parrafos": rutas})

    # 4. Desbalance (ficticios)
    if balance["ficticio"] == "origen":
        texto = [
            f"La demanda ({cant(balance['demanda_total'])}) supera la oferta ({cant(balance['oferta_total'])}): "
            f"faltan {cant(balance['diferencia'])}. Lo asignado al origen ficticio es demanda que no se podrá atender."
        ]
        texto += [f"{r['destino']} quedará sin recibir {cant(r['cantidad'])}." for r in rutas_ficticias]
        texto.append("Para cubrir ese faltante haría falta más capacidad o un proveedor adicional.")
        bloques.append({"titulo": "Oferta y demanda desbalanceadas", "tipo": "aviso", "parrafos": texto})
    elif balance["ficticio"] == "destino":
        texto = [
            f"La oferta ({cant(balance['oferta_total'])}) supera la demanda ({cant(balance['demanda_total'])}): "
            f"sobran {cant(balance['diferencia'])}. Lo asignado al destino ficticio es producto que no sale del origen."
        ]
        texto += [f"{r['origen']} conserva {cant(r['cantidad'])} sin despachar." for r in rutas_ficticias]
        texto.append("Ese excedente queda como inventario o capacidad sin usar.")
        bloques.append({"titulo": "Oferta y demanda desbalanceadas", "tipo": "aviso", "parrafos": texto})

    # 5. Calidad de la solución: optimalidad, degeneración y empates
    calidad = []
    opt = res["optimalidad"]
    if opt is not None:
        if opt["optima"]:
            calidad.append(
                "Comprobación rápida con los multiplicadores u-v (MODI): todos los costos reducidos de las rutas "
                "vacías son mayores o iguales a cero, así que esta solución inicial ya es óptima: ningún cambio "
                f"de rutas reduce {el_total}."
            )
            if opt["alternativa"]:
                calidad.append(
                    "Al menos una ruta vacía tiene costo reducido igual a 0: existe otro plan distinto con "
                    f"{'la misma' if tipo == 'distancia' else 'el mismo'} {nombre_total}."
                )
        else:
            d = opt["mejor_mejora"]
            calidad.append(
                f"Comprobación rápida con los multiplicadores u-v (MODI): la ruta {res['origenes'][d['i']]} → "
                f"{res['destinos'][d['j']]} tiene un costo reducido de {fmt(d['delta'])}. Cada unidad que se "
                f"envíe por ella bajaría el total en {val(-d['delta'])}, así que esta solución inicial todavía "
                "puede mejorarse aplicando un método de mejora como MODI o el de banquillo (stepping stone)."
            )
    if res["degenerada"]:
        faltan = res["celdas_requeridas"] - res["celdas_basicas"]
        calidad.append(
            f"La solución es degenerada: tiene {res['celdas_basicas']} celdas ocupadas y se necesitan "
            f"m + n − 1 = {res['celdas_requeridas']}. Para aplicar MODI hay que marcar como básica"
            f"{'s' if faltan > 1 else ''} {faltan} celda{'s' if faltan > 1 else ''} con asignación 0."
        )
    else:
        calidad.append(
            f"La solución no es degenerada: tiene {res['celdas_basicas']} celdas ocupadas, exactamente "
            f"m + n − 1 = {res['celdas_requeridas']}, así que se puede pasar directamente a MODI."
        )
    empates = [it["numero"] for it in res["iteraciones"] if it["empate_relevante"]]
    if empates:
        calidad.append(
            f"Hubo empates en la mayor penalización (iteración{'es' if len(empates) > 1 else ''} "
            f"{_lista([str(k) for k in empates])}). Elegir otra de las opciones empatadas es igual de válido "
            "y puede llevar a otra solución inicial."
        )
    bloques.append({"titulo": "Calidad de la solución", "tipo": "calidad", "parrafos": calidad})

    # 6. Avisos que dependen del enunciado
    avisos = []
    if contexto and _PALABRAS_GANANCIA.search(contexto):
        avisos.append(
            "El enunciado habla de ganancias, utilidades o de maximizar. Este módulo de Vogel minimiza: si la "
            "tabla tiene utilidades, el resultado no es el de mayor ganancia. Para maximizar, primero convierte "
            "las utilidades en costos de oportunidad (mayor valor − cada valor) y resuelve con esa tabla."
        )
    if detectado:
        avisos.append(
            f"Por el enunciado, los valores de la tabla se interpretaron como "
            f"{'distancias' if tipo == 'distancia' else 'tiempos'}. Si no es así, cámbialo en "
            "«Los valores de la tabla son»."
        )
    if avisos:
        bloques.append({"titulo": "Según el enunciado", "tipo": "aviso", "parrafos": avisos})

    n_rutas, n_iter = len(rutas_reales), len(res["iteraciones"])
    resumen = (
        f"{el_total[:1].upper()}{el_total[1:]} del plan inicial es {val(res['costo_total'])}, con {n_rutas} "
        f"ruta{'s' if n_rutas != 1 else ''} y {n_iter} iteracion{'es' if n_iter != 1 else ''}."
    )
    return {
        "resumen": resumen,
        "bloques": bloques,
        "tipo_valor": tipo,
        "nombre_total": nombre_total,
        "valor_total": val(res["costo_total"]),
        "unidad_envio": envio,
    }


# ── Formulario ──────────────────────────────────────────────────────────────
def _decimal_formulario(nombre, etiqueta):
    valor = request.form.get(nombre, "").strip().replace(",", ".")
    if not valor:
        raise ValueError(f"Falta el {etiqueta}.")
    try:
        numero = Decimal(valor)
    except (InvalidOperation, ValueError):
        raise ValueError(f"El campo «{etiqueta}» debe contener un número válido.")
    if not numero.is_finite():
        raise ValueError(f"El campo «{etiqueta}» debe ser un número finito.")
    return numero


def _dimension_formulario(nombre, predeterminado):
    try:
        dimension = int(request.form.get(nombre, predeterminado))
    except (TypeError, ValueError):
        raise ValueError("La cantidad de orígenes y destinos debe ser entera.")
    if not 1 <= dimension <= MAX_DIMENSION:
        raise ValueError(
            f"La cantidad de orígenes y destinos debe estar entre 1 y {MAX_DIMENSION}."
        )
    return dimension


def _texto(nombre, maximo):
    return (request.form.get(nombre) or "").strip()[:maximo]


def _nombres(prefijo, etiqueta, cantidad):
    nombres = [
        " ".join(_texto(f"{prefijo}_{k}", MAX_NOMBRE).split()) or f"{etiqueta} {k + 1}"
        for k in range(cantidad)
    ]
    vistos = set()
    for k, nombre in enumerate(nombres):  # nombres repetidos confundirían las tablas
        if nombre in vistos:
            nombres[k] = f"{nombre} ({k + 1})"
        vistos.add(nombres[k])
    return nombres


def _datos_red(res):
    """Orígenes, destinos y rutas usadas, para la animación de cierre (red de transporte)."""
    if not res:
        return None
    return {
        "origenes": res["origenes"],
        "destinos": res["destinos"],
        "rutas": [
            {"i": r["i"], "j": r["j"], "cantidad": float(r["cantidad"]), "ficticia": r["ficticia"]}
            for r in res["rutas"]
        ],
    }


@vogel_bp.route("/", methods=["GET", "POST"])
def vista_principal():
    filas = columnas = 2
    resultados = analisis = error = None
    form = {"contexto": "", "unidad_envio": "", "unidad_valor": "", "tipo_valor": "auto"}

    if request.method == "POST":
        form = {
            "contexto": _texto("contexto", MAX_CONTEXTO),
            "unidad_envio": _texto("unidad_envio", 30),
            "unidad_valor": _texto("unidad_valor", 15),
            "tipo_valor": request.form.get("tipo_valor", "auto"),
        }
        if form["tipo_valor"] not in ("auto", "costo", "distancia", "tiempo"):
            form["tipo_valor"] = "auto"
        try:
            filas = _dimension_formulario("num_origenes", 2)
            columnas = _dimension_formulario("num_destinos", 2)
            costos = [
                [
                    _decimal_formulario(
                        f"costo_{i}_{j}",
                        f"costo del origen {i + 1} al destino {j + 1}",
                    )
                    for j in range(columnas)
                ]
                for i in range(filas)
            ]
            oferta = [
                _decimal_formulario(f"oferta_{i}", f"oferta del origen {i + 1}")
                for i in range(filas)
            ]
            demanda = [
                _decimal_formulario(f"demanda_{j}", f"demanda del destino {j + 1}")
                for j in range(columnas)
            ]
            resultados = resolver_vogel(
                costos,
                oferta,
                demanda,
                _nombres("nombre_origen", "Origen", filas),
                _nombres("nombre_destino", "Destino", columnas),
            )
            analisis = redactar_analisis(
                resultados,
                form["contexto"],
                form["unidad_envio"],
                form["unidad_valor"],
                form["tipo_valor"],
            )
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "metodo_vogel/resolucion.html",
        resultados=resultados,
        red=_datos_red(resultados),
        analisis=analisis,
        error=error,
        form=form,
        filas=filas,
        columnas=columnas,
        max_dimension=MAX_DIMENSION,
        fmt=fmt,
    )
