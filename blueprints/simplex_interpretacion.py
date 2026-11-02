"""Interpretación en español de un resultado del Simplex normal.

Combina el contexto escrito por el usuario (texto libre, unidades de variables y
recursos) con la solución y la sensibilidad. No usa servicios externos.
Devuelve una lista de secciones: [{"titulo": str, "items": [str, ...]}].
"""
from fractions import Fraction

_BENEFICIO = ("utilidad", "ganancia", "beneficio", "ingreso", "venta", "rentabilidad", "retorno",
              "margen", "rendimiento", "producción", "produccion")
_COSTO = ("costo", "coste", "gasto", "inversión", "inversion", "desperdicio", "pérdida", "perdida",
          "tiempo", "consumo")


def _num(v):
    """Entero, o decimal con hasta 4 cifras."""
    if v is None:
        return "—"
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    return f"{float(v):.4f}".rstrip("0").rstrip(".")


def _con(v, unidad):
    return f"{_num(v)} {unidad}".strip()


def _objetivo(res):
    """('la ganancia', 'máxima') / ('el costo', 'mínimo') según el contexto y el sentido."""
    texto = (res["contexto"] + " " + res["unidad_z"]).lower()
    sentido = res["sentido"]
    hay_costo = any(p in texto for p in _COSTO)
    hay_beneficio = any(p in texto for p in _BENEFICIO)
    if hay_costo and (sentido == "min" or not hay_beneficio):
        sustantivo = "el costo"
    elif hay_beneficio:
        sustantivo = "la ganancia"
    else:
        sustantivo = "el beneficio" if sentido == "max" else "el costo"
    extremo = "máximo" if sentido == "max" else "mínimo"
    if sustantivo.startswith("la "):
        extremo = extremo[:-1] + "a"
    return sustantivo, extremo


def _rango(lo, hi, unidad=""):
    u = f" {unidad}" if unidad else ""
    if lo is None and hi is None:
        return "sin límite en ningún sentido"
    if lo is None:
        return f"hasta {_num(hi)}{u}"
    if hi is None:
        return f"desde {_num(lo)}{u} en adelante"
    return f"entre {_num(lo)}{u} y {_num(hi)}{u}"


def interpretar(res):
    contexto = res["contexto"]
    secciones = []
    if contexto:
        secciones.append({"titulo": "Contexto", "items": [contexto]})
    if res["estado"] == "no_acotado":
        sustantivo, _ = _objetivo(res)
        direccion = "crecer" if res["sentido"] == "max" else "decrecer"
        secciones.append({"titulo": "El problema es no acotado", "items": [
            f"{sustantivo.capitalize()} puede {direccion} sin límite: se puede aumentar "
            f"{res['variable_no_acotada']} indefinidamente sin que ninguna restricción lo impida.",
            "En un caso real falta una restricción (un límite de recursos, de capacidad o de demanda) "
            "o hay un signo mal digitado. Revisa que cada actividad esté limitada por algún recurso."]})
        return secciones

    p = res["problema"]
    sustantivo, extremo = _objetivo(res)
    uz = res["unidad_z"]
    sentido = res["sentido"]
    n = len(p["c"])

    # ---- decisión óptima
    items = [f"El modelo encontró una solución óptima: {sustantivo} {extremo} posible es {_con(res['z'], uz)}."]
    usadas = 0
    for j in range(n):
        u = p["unidades"][j]
        if res["x"][j] > 0:
            usadas += 1
            items.append(f"{p['nombres'][j]} = {_con(res['x'][j], u)}")
    for j in range(n):
        if res["x"][j] == 0:
            rc = res["sens_variables"][j]["costo_reducido"]
            peor = "reduciría" if sentido == "max" else "aumentaría"
            if rc > 0:
                items.append(f"{p['nombres'][j]} = 0: no conviene incluirlo. Forzar una unidad de "
                             f"{p['nombres'][j]} {peor} {sustantivo} en {_con(rc, uz)} (su costo reducido).")
            else:
                items.append(f"{p['nombres'][j]} = 0: no se usa, pero su costo reducido es 0, así que "
                             "podría entrar sin cambiar Z (ver soluciones alternativas).")
    if not usadas:
        items.append("La solución óptima es no realizar ninguna actividad: todas las variables valen 0.")
    secciones.append({"titulo": "Decisión óptima", "items": items})

    # ---- recursos
    items, importantes = [], []
    for i, d in enumerate(res["sens_restricciones"]):
        u = p["uni_res"][i]
        nombre, b, sombra, hol = d["restriccion"], d["rhs"], d["precio_sombra"], res["holguras"][i]
        rango = _rango(d["minimo"], d["maximo"], u)
        if hol > 0:
            items.append(f"{nombre} (≤ {_con(b, u)}): NO es limitante, sobran {_con(hol, u)}. Ampliarlo no "
                         f"mejora el resultado (precio sombra 0); podría reducirse hasta "
                         f"{_con(d['minimo'], u)} sin cambiar la solución.")
        elif sombra == 0:
            items.append(f"{nombre} (≤ {_con(b, u)}): se usa por completo, pero su precio sombra es 0: "
                         "ampliarlo no cambia Z (solución degenerada).")
        else:
            mejora = (sombra > 0) == (sentido == "max")
            signo = "aumentaría" if sombra > 0 else "disminuiría"
            items.append(f"{nombre} (≤ {_con(b, u)}): se usa por completo; es un recurso LIMITANTE. "
                         f"Precio sombra = {_num(sombra)}: cada unidad adicional {signo} Z en "
                         f"{_con(abs(sombra), uz)} ({'mejora' if mejora else 'empeora'} {sustantivo}). "
                         f"Vale mientras el límite esté {rango}.")
            importantes.append((abs(sombra), nombre, u))
    secciones.append({"titulo": "¿Qué está limitando el resultado?", "items": items})

    # ---- estabilidad
    items = []
    for d in res["sens_variables"]:
        items.append(f"{d['variable']} (coeficiente actual {_num(d['coeficiente'])}): la decisión óptima "
                     f"no cambia mientras su coeficiente esté {_rango(d['minimo'], d['maximo'], uz)}.")
    secciones.append({"titulo": "¿Qué tan estable es la decisión?", "items": items})

    # ---- observaciones
    obs = []
    if res["optimos_multiples"]:
        obs.append("Hay soluciones óptimas alternativas: otra combinación logra el mismo Z. Puedes elegir la "
                   "que mejor se ajuste a criterios que el modelo no considera.")
    if res["degenerado"]:
        obs.append("La solución es degenerada (una variable básica vale 0): los precios sombra y rangos "
                   "pueden no ser únicos; interprétalos con cautela.")
    if obs:
        secciones.append({"titulo": "Observaciones", "items": obs})

    # ---- conclusión
    concl = [f"Se recomienda implementar la solución anterior, que logra {sustantivo} {extremo} "
             f"de {_con(res['z'], uz)}."]
    if importantes:
        v, nombre, u = max(importantes)
        por = f" por cada unidad adicional ({u})" if u else " por cada unidad adicional"
        concl.append(f"El recurso más influyente es «{nombre}»: {_con(v, uz)}{por}. Si vas a flexibilizar "
                     "algo, empieza por ahí, siempre dentro del rango de validez indicado.")
    else:
        concl.append("Ninguna restricción tiene precio sombra distinto de 0, por lo que ampliar recursos "
                     "no mejora el resultado.")
    secciones.append({"titulo": "Conclusión y recomendación", "items": concl})
    return secciones
