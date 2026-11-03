"""Simplex de dos fases con aritmética racional y trazabilidad didáctica.

Convención del curso: Z - sum(c_j x_j) = 0. Max: entra el más
negativo; Min (incluida r): entra el más positivo. No usa un optimizador
externo: cada tableau se obtiene por operaciones elementales exactas.
"""
from fractions import Fraction as F
import re


class ModelError(ValueError):
    """Datos que no definen un modelo admitido. `field` identifica el campo de la interfaz."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


def number(value, where="", field=None):
    prefix = f"{where}: " if where else ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, F)):
        raise ModelError(prefix + "Los coeficientes deben ser números, decimales o fracciones.", field)
    text = str(value).strip().replace(",", ".")
    if len(text) > 40 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,2})?|[+-]?\d+/[+-]?\d+", text):
        raise ModelError(prefix + f"Número inválido: {text[:40]!r}. Usa, por ejemplo, -2, 0.5 o 1/3.", field)
    try:
        result = F(text)
    except (ValueError, ZeroDivisionError, OverflowError):
        raise ModelError(prefix + "Fracción inválida: el denominador no puede ser 0.", field) from None
    if abs(result) > 10**9 or result.denominator > 10**12:
        raise ModelError(prefix + "Usa magnitudes de hasta 10⁹ y denominadores de hasta 10¹².", field)
    return result


def label(value, default="", limit=160):
    if value is None:
        return default
    if not isinstance(value, str) or len(value) > limit:
        raise ModelError(f"El texto debe tener como máximo {limit} caracteres.")
    return value.strip() or default


def validate(payload):
    if not isinstance(payload, dict):
        raise ModelError("Envía un objeto con objective y constraints.")
    sense = payload.get("sense", "max")
    if sense not in ("max", "min"):
        raise ModelError("Selecciona max o min.")
    c = payload.get("objective")
    if not isinstance(c, list) or not 1 <= len(c) <= 8:
        raise ModelError("Se admiten entre 1 y 8 variables de decisión.")
    n = len(c)
    c = [number(v, f"Z · x{j+1}", f"c-{j}") for j, v in enumerate(c)]
    items = payload.get("constraints")
    if not isinstance(items, list) or not 1 <= len(items) <= 12:
        raise ModelError("Se admiten entre 1 y 12 restricciones.")
    constraints = []
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("coefficients"), list) or len(item["coefficients"]) != n:
            raise ModelError(f"R{i+1}: debe haber un coeficiente por variable.")
        op = item.get("operator")
        if op not in ("<=", ">=", "=", "≤", "≥"):
            raise ModelError(f"R{i+1}: utiliza ≤, ≥ o =.")
        constraints.append({"coefficients": [number(v, f"R{i+1} · x{j+1}", f"a-{i}-{j}") for j, v in enumerate(item["coefficients"])],
                            "operator": {"≤": "<=", "≥": ">="}.get(op, op),
                            "rhs": number(item.get("rhs"), f"R{i+1} · K", f"b-{i}"),
                            "label": label(item.get("label"), f"R{i+1}"),
                            "unit": label(item.get("unit"), "", 80)})
    raw_variables = payload.get("variables", [{} for _ in c])
    if not isinstance(raw_variables, list) or len(raw_variables) != n or any(not isinstance(v, dict) for v in raw_variables):
        raise ModelError("variables debe tener un objeto por variable de decisión.")
    variables = [{"symbol": f"x{i+1}", "name": label(v.get("name"), f"x{i+1}"),
                  "unit": label(v.get("unit"), "unidades", 80)} for i, v in enumerate(raw_variables)]
    return {"sense": sense, "objective": c, "constraints": constraints, "variables": variables,
            "context": label(payload.get("context"), "", 4000),
            "objective_name": label(payload.get("objective_name"), "Valor de Z"),
            "objective_unit": label(payload.get("objective_unit"), "unidades", 80)}


def expression(coefficients, names):
    parts = []
    for a, name in zip(coefficients, names):
        if a:
            term = ("" if abs(a) == 1 else str(abs(a)) + "·") + name
            parts.append((" − " if a < 0 else " + ") + term)
    text = "".join(parts)
    return text[3:] if text.startswith(" + ") else "−" + text[3:] if text else "0"


def solve(payload, *, max_iterations=120):
    """Devuelve datos JSON compatibles; todos los números exactos son cadenas.

    Las variables son continuas y no negativas. El contexto no se analiza como
    código ni se convierte automáticamente en restricciones.
    """
    model = validate(payload)
    n = len(model["objective"])
    names = [f"x{i+1}" for i in range(n)]
    normalized = []
    standard = []
    for i, item in enumerate(model["constraints"]):
        a, b, op = item["coefficients"][:], item["rhs"], item["operator"]
        flipped = b < 0
        if flipped:
            a, b = [-v for v in a], -b
            op = {"<=": ">=", ">=": "<=", "=": "="}[op]
        normalized.append((a, op, b))
        standard.append({"restriction": f"R{i+1}", "flipped": flipped,
                         "normalized": f"{expression(a, names)} {op} {b}"})
    names += [f"S{i+1}" for i, (_, op, _) in enumerate(normalized) if op != "="]
    names += [f"A{i+1}" for i, (_, op, _) in enumerate(normalized) if op != "<="]
    art = {j for j, name in enumerate(names) if name.startswith("A")}
    basis, rows, row_ids = [], [], []
    for i, (a, op, b) in enumerate(normalized):
        row = a + [F(0)] * (len(names) - n) + [b]
        if op != "=":
            row[names.index(f"S{i+1}")] = F(1 if op == "<=" else -1)
        basic = f"S{i+1}" if op == "<=" else f"A{i+1}"
        if op != "<=":
            row[names.index(basic)] = F(1)
        basis.append(names.index(basic))
        rows.append(row)
        row_ids.append(f"R{i+1}")
        standard[i]["equation"] = expression(row[:-1], names) + f" = {b}"
        standard[i]["basic"] = basic
        sym = {"<=": "≤", ">=": "≥", "=": "="}
        text = (f"K negativo: se multiplica la fila por −1 y la relación queda {sym[op]}. " if standard[i]["flipped"] else "")
        text += {"<=": f"≤: se suma la holgura S{i+1}, que es la variable básica inicial.",
                 ">=": f"≥: se resta el excedente S{i+1} y se suma la artificial A{i+1}, que es la variable básica inicial.",
                 "=": f"=: no hay holgura; se suma la artificial A{i+1}, que es la variable básica inicial."}[op]
        standard[i]["explanation"] = text
    objective = [F(-1 if j in art else 0) for j in range(len(names))] + [F(0)]
    events, notes = [], []
    result = {"model": model, "standardization": standard, "events": events,
              "notes": notes, "initial_basis": [names[j] for j in basis],
              "auxiliary": " + ".join(names[j] for j in sorted(art)) or "0"}
    phase, iteration, bland = 1, 0, False

    def snapshot(title, kind="tableau", operations=None, pivot=None, stage="pivote", **extra):
        # Copias defensivas: los pivotes posteriores no alteran el historial.
        values = {names[j]: rows[i][-1] for i, j in enumerate(basis)}
        events.append({"number": len(events) + 1, "title": title, "kind": kind, "stage": stage,
                       "phase": phase, "columns": names[:], "basis": [names[j] for j in basis],
                       "row_ids": row_ids[:], "objective_label": "r" if phase == 1 else "Z",
                       "tableau": [objective[:]] + [r[:] for r in rows],
                       "operations": operations or [], "pivot": pivot,
                       # Solución básica que representa la tabla (para el recorrido y el mapa).
                       "point": [values.get(f"x{k+1}", F(0)) for k in range(n)],
                       "artificial_sum": sum((v for name, v in values.items() if name.startswith("A")), F(0)),
                       **extra})

    def row_operation(target_name, before, pivot_row, factor, after):
        return {"kind": "reduce", "target": target_name, "multiplier": factor,
                "formula": f"{target_name} nueva = ({factor})·Rp nueva + {target_name} anterior",
                "components": [{"column": col, "calculation": f"({factor})·({p}) + ({b}) = {a}"}
                               for col, b, p, a in zip(names + ["K"], before, pivot_row, after)]}

    def canonicalize():
        ops = []
        for i, j in enumerate(basis):
            factor = -objective[j]
            if factor:
                before = objective[:]
                objective[:] = [v + factor*p for v, p in zip(objective, rows[i])]
                op = row_operation("r" if phase == 1 else "Z", before, rows[i], factor, objective)
                op["formula"] = op["formula"].replace("Rp nueva", f"{row_ids[i]} ({names[j]})")
                op["source"] = f"{row_ids[i]} ({names[j]})"
                ops.append(op)
        return ops

    def pivot(i, j, title, info):
        nonlocal iteration
        p = rows[i][j]
        old = rows[i][:]
        rows[i] = [v / p for v in old]
        ops = [{"kind": "normalize", "target": row_ids[i], "multiplier": F(1) / p,
                "formula": f"Rp nueva = {row_ids[i]} anterior / ({p})",
                "components": [{"column": col, "calculation": f"({v}) / ({p}) = {out}"}
                               for col, v, out in zip(names + ["K"], old, rows[i])]}]
        for k in range(len(rows)):
            if k == i:
                continue
            factor = -rows[k][j]
            before = rows[k][:]
            rows[k] = [v + factor*q for v, q in zip(before, rows[i])]
            ops.append(row_operation(row_ids[k], before, rows[i], factor, rows[k]))
        factor = -objective[j]
        before = objective[:]
        objective[:] = [v + factor*q for v, q in zip(before, rows[i])]
        ops.append(row_operation("r" if phase == 1 else "Z", before, rows[i], factor, objective))
        basis[i] = j
        iteration += 1
        info = dict(info, previous_table=len(events), table=len(events) + 1)
        snapshot(title, "pivot", ops, info, stage="limpieza" if info["rule"].startswith("Limpieza") else "pivote")

    def run(sense):
        nonlocal bland
        seen = set()
        while True:
            signature = tuple(basis)
            if signature in seen and not bland:
                bland = True
                notes.append("Se repitió una base: se activa la regla de Bland para evitar ciclos.")
            seen.add(signature)
            candidates = [j for j in range(len(names)) if j not in basis and
                          (objective[j] < 0 if sense == "max" else objective[j] > 0)]
            if not candidates:
                return "optimal", None
            if iteration >= max_iterations:
                return "iteration_limit", None
            j = min(candidates) if bland else (min(candidates, key=lambda k: (objective[k], k)) if sense == "max"
                                              else min(candidates, key=lambda k: (-objective[k], k)))
            ratios = [{"row": row_ids[i], "basic": names[basis[i]], "rhs": row[-1],
                       "coefficient": row[j], "ratio": row[-1]/row[j] if row[j] > 0 else None}
                      for i, row in enumerate(rows)]
            eligible = [i for i, r in enumerate(ratios) if r["ratio"] is not None]
            if not eligible:
                return "unbounded", j
            i = min(eligible, key=lambda k: (ratios[k]["ratio"], basis[k]))
            best_value = objective[j]
            entering_ties = [names[k] for k in candidates if objective[k] == best_value]
            ratio_ties = [ratios[k]["row"] for k in eligible if ratios[k]["ratio"] == ratios[i]["ratio"]]
            info = {"entering_ties": entering_ties if len(entering_ties) > 1 and not bland else [],
                    "ratio_ties": ratio_ties if len(ratio_ties) > 1 else [],
                    "min_ratio": ratios[i]["ratio"],"entering": names[j], "leaving": names[basis[i]], "row": row_ids[i],
                    "column_index": j, "row_index": i+1, "element": rows[i][j],
                    "objective_coefficient": objective[j], "ratios": ratios,
                    "rule": "Bland" if bland else ("Más negativo de Z" if sense == "max" else "Más positivo de " + ("r" if phase == 1 else "Z")),
                    "degenerate": ratios[i]["ratio"] == 0}
            pivot(i, j, f"Fase {phase} · Resultado del pivote {sum(e['kind']=='pivot' and e['phase']==phase for e in events)+1}", info)

    def finish(status, message, **extra):
        result.update(status=status, message=message, iterations=iteration, **extra)
        explain(result, model)
        result["conclusion"] = conclude(result, model)
        return serialize(result)

    snapshot("Fase 1 · Tableau inicial: r − ΣA = 0", stage="f1_inicial")
    snapshot("Fase 1 · Fila r reducida respecto de la base", operations=canonicalize(), stage="f1_reducida")
    if not art:
        notes.append("No se necesitan artificiales: r = 0 desde el inicio. Se conserva la base de holguras y se pasa a Fase 2.")
    status, _ = run("min")
    if status == "iteration_limit":
        return finish(status, "Se alcanzó el límite de iteraciones en Fase 1; no se certifica una solución óptima.")
    if status == "unbounded":
        raise ArithmeticError("La función auxiliar no puede ser no acotada inferiormente.")
    result["phase1_value"] = objective[-1]
    if objective[-1] != 0:
        artificial_values = {names[j]: rows[i][-1] for i, j in enumerate(basis) if j in art}
        lines = []
        for name, value in artificial_values.items():
            if value:
                item = model["constraints"][int(name[1:]) - 1]
                unit = f" {item['unit']}" if item["unit"] else ""
                lines.append(f"{name} = {value}{unit}: la restricción R{name[1:]} ({item['label']}) no puede cumplirse "
                             f"al mismo tiempo que las demás. Falta cubrir {value}{unit} de esa condición.")
        lines.append("Con los datos ingresados no existe un plan que respete todas las condiciones a la vez; "
                     "revisa los signos, las relaciones (≤, ≥, =) y los términos independientes.")
        return finish("infeasible", "El mínimo de r es positivo. No existe una solución que satisfaga todas las restricciones.",
                      artificial_values=artificial_values, interpretation=lines)
    # Artificial básica de valor cero: se pivotea fuera (incluso con pivote
    # negativo) o se elimina una fila redundante 0 = 0, siempre con evidencia.
    for i in range(len(basis)-1, -1, -1):
        if basis[i] not in art:
            continue
        j = next((k for k in range(len(names)) if k not in art and k not in basis and rows[i][k]), None)
        if j is not None:
            if iteration >= max_iterations:
                return finish("iteration_limit", "Límite de iteraciones durante la salida de artificiales básicas.")
            info = {"entering": names[j], "leaving": names[basis[i]], "row": row_ids[i],
                    "column_index": j, "row_index": i+1, "element": rows[i][j], "ratios": [],
                    "rule": "Limpieza: artificial básica con K = 0", "degenerate": True}
            pivot(i, j, "Transición · Retirar artificial básica de valor cero", info)
        else:
            removed = row_ids.pop(i)
            rows.pop(i)
            basis.pop(i)
            notes.append(f"{removed} es redundante: al retirar las artificiales queda 0 = 0. Se elimina únicamente esa fila transformada.")
            snapshot(f"Transición · Eliminar fila redundante {removed}", stage="redundante", removed=removed)
    result["phase1_basis"] = [names[j] for j in basis]
    keep = [j for j in range(len(names)) if j not in art]
    mapping = {old: new for new, old in enumerate(keep)}
    names = [names[j] for j in keep]
    rows = [[row[j] for j in keep] + [row[-1]] for row in rows]
    basis = [mapping[j] for j in basis]
    phase = 2
    objective = [-v for v in model["objective"]] + [F(0)]*(len(names)-n+1)
    snapshot("Fase 2 · Función original visible: Z − Σcⱼxⱼ = 0", stage="f2_original")
    snapshot("Fase 2 · Z canónica vinculada con la base heredada", operations=canonicalize(), stage="f2_canonica")
    status, entering = run(model["sense"])
    if status == "iteration_limit":
        return finish(status, "Se alcanzó el límite de iteraciones; no se certifica el óptimo.")
    values = [F(0)] * len(names)
    for i, j in enumerate(basis):
        values[j] = rows[i][-1]
    x = values[:n]
    z = sum((c*v for c, v in zip(model["objective"], x)), F(0))
    checks = []
    for item in model["constraints"]:
        lhs = sum((a*v for a, v in zip(item["coefficients"], x)), F(0))
        b, op = item["rhs"], item["operator"]
        ok = lhs <= b if op == "<=" else lhs >= b if op == ">=" else lhs == b
        checks.append({"label": item["label"], "unit": item["unit"], "lhs": lhs, "operator": op, "rhs": b,
                       "margin": b-lhs if op == "<=" else lhs-b if op == ">=" else F(0),
                       "binding": lhs == b, "satisfied": ok,
                       "substitution": " + ".join(f"({a})·({v})" for a,v in zip(item["coefficients"],x))})
    if not all(ch["satisfied"] for ch in checks) or any(v < 0 for v in x) or z != objective[-1]:
        raise ArithmeticError("La solución no superó la verificación exacta del modelo original.")
    result.update(values=dict(zip(names, values)), solution=x, objective_value=z, verification=checks,
                  nonnegative=all(v >= 0 for v in x), final_basis=[names[j] for j in basis],
                  objective_substitution=" + ".join(f"({c})·({v})" for c,v in zip(model["objective"],x)))
    if status == "unbounded":
        ray = [F(0)] * len(names)
        ray[entering] = F(1)
        for i, j in enumerate(basis):
            ray[j] = -rows[i][entering]
        gain = sum(c*v for c, v in zip(model["objective"], ray[:n]))
        def cambio(valor, unidad):
            return f"{'aumenta' if valor > 0 else 'disminuye'} en {abs(valor)}" + (f" ({unidad})" if unidad else "")
        lines = [f"Por cada unidad de avance t: {var['name']} ({var['symbol']}) {cambio(r, var['unit'])}."
                 for var, r in zip(model["variables"], ray[:n]) if r]
        lines.append(f"{model['objective_name']} {cambio(gain, model['objective_unit'])} por cada unidad de t, "
                     f"sin tope: no existe un {'máximo' if model['sense'] == 'max' else 'mínimo'} finito.")
        lines.append("Revisa si falta una restricción que limite esa dirección (por ejemplo, una capacidad o un presupuesto).")
        return finish(status, "El modelo es factible, pero Z puede mejorar sin límite. No existe un valor óptimo finito.",
                      ray=ray[:n], ray_gain=gain, interpretation=lines,
                      unbounded_column_index=entering)
    alternatives = []
    for j in range(len(names)):
        if j in basis or objective[j] != 0:
            continue
        limits = [rows[i][-1]/row[j] for i,row in enumerate(rows) if row[j] > 0]
        if limits and min(limits) == 0:
            continue
        direction = [F(0)]*len(names)
        direction[j] = F(1)
        for i, k in enumerate(basis):
            direction[k] = -rows[i][j]
        if any(direction[:n]):
            alternatives.append(names[j])
    interpretation = [f"{var['name']} ({var['symbol']}): {v} {var['unit']}." for var, v in zip(model["variables"], x)]
    interpretation.append(f"{model['objective_name']} (valor {'máximo' if model['sense']=='max' else 'mínimo'}): {z} {model['objective_unit']}.")
    slacks = []
    for item, ch, (_, nop, _) in zip(model["constraints"], checks, normalized):
        unit = f" {item['unit']}" if item["unit"] else ""
        op = item["operator"]
        if op == "=":
            interpretation.append(f"{item['label']}: se cumple exactamente ({ch['lhs']}{unit} = {ch['rhs']}{unit}).")
        elif op == "<=":
            interpretation.append(f"{item['label']}: " + (f"límite alcanzado, se usan {ch['lhs']}{unit} de {ch['rhs']}{unit}." if ch["binding"]
                                  else f"sobran {ch['margin']}{unit} (holgura); se usan {ch['lhs']}{unit} de {ch['rhs']}{unit}."))
        else:
            interpretation.append(f"{item['label']}: " + (f"se cumple justo en el mínimo requerido ({ch['rhs']}{unit})." if ch["binding"]
                                  else f"se supera el mínimo en {ch['margin']}{unit} (excedente); resultado {ch['lhs']}{unit} frente a {ch['rhs']}{unit}."))
    for i, item in enumerate(model["constraints"]):
        if item["operator"] != "=":
            slacks.append({"name": f"S{i+1}", "restriction": f"R{i+1}", "label": item["label"], "unit": item["unit"],
                           "kind": "holgura" if item["operator"] == "<=" else "excedente",
                           "value": checks[i]["margin"]})
    return finish("optimal", "Solución óptima verificada en las restricciones originales.",
                  interpretation=interpretation, slacks=slacks, alternate_directions=alternatives,
                  optimality="No hay coeficientes negativos en Z." if model["sense"]=="max" else "No hay coeficientes positivos en Z.")


# ---------------------------------------------------------------------------
# Bitácora en lenguaje natural, recorrido de soluciones y conclusión.
# Todo se deriva de las tablas ya calculadas: no cambia ningún resultado.
# ---------------------------------------------------------------------------
def _plural(count, singular, plural=None):
    return singular if count == 1 else (plural or singular + "s")


def _point_text(point):
    return "(" + ", ".join(str(v) for v in point) + ")"


def _objective_equation(model):
    text = "Z"
    for j, c in enumerate(model["objective"]):
        coef = -c
        if coef == 0:
            continue
        mag = abs(coef)
        text += (" − " if coef < 0 else " + ") + ("" if mag == 1 else f"{mag}·") + f"x{j+1}"
    return text + " = 0"


def explain(result, model):
    """Agrega a cada tabla una bitácora con preguntas y respuestas, y un resumen del recorrido."""
    events = result["events"]
    status = result.get("status")
    sense = model["sense"]
    for k, e in enumerate(events):
        nxt = events[k + 1] if k + 1 < len(events) else None
        obj, T, stage = e["objective_label"], e["tableau"], e["stage"]
        notes = []

        def add(kind, title, text):
            notes.append({"kind": kind, "title": title, "text": text})

        if stage == "f1_inicial":
            arts = [c for c in e["columns"] if c.startswith("A")]
            if arts:
                one = len(arts) == 1
                add("hecho", "¿Qué se hizo?",
                    f"Fase 1: se minimiza r = {' + '.join(arts)}. Escrita como r − {' − '.join(arts)} = 0, la fila r tiene −1 en "
                    f"{', '.join(arts)}. {'Esa artificial es básica' if one else 'Esas artificiales son básicas'}, pero su "
                    f"coeficiente en r todavía no es 0: hay que limpiar la fila.")
            else:
                add("hecho", "¿Qué se hizo?",
                    "No hace falta ninguna artificial: todas las restricciones son ≤ con K ≥ 0 y las holguras ya forman una base "
                    "factible. r = 0 desde el inicio.")
        elif stage == "f1_reducida":
            if e["operations"]:
                sources = ", ".join(op["source"] for op in e["operations"])
                add("hecho", "¿Qué se hizo?",
                    f"Se suman a la fila r las filas de las artificiales básicas: {sources}. Así cada artificial queda con 0 en r, "
                    "como corresponde a una variable básica, y K muestra cuánto suman todavía las artificiales.")
            else:
                add("hecho", "¿Qué se hizo?", "No hay artificiales básicas: la fila r ya está reducida.")
        elif stage == "pivote":
            p = e["pivot"]
            reds = [op for op in e["operations"] if op["kind"] == "reduce" and op["multiplier"] != 0]
            same = [op["target"] for op in e["operations"] if op["kind"] == "reduce" and op["multiplier"] == 0]
            text = (f"Se divide {p['row']} entre el pivote {p['element']} para dejar un 1. Con esa fila nueva (Rp) se hace 0 "
                    f"el resto de la columna {p['entering']}: "
                    + "; ".join(f"{op['target']} nueva = ({op['multiplier']})·Rp + {op['target']}" for op in reds) + ".")
            if same:
                text += f" {', '.join(same)} {_plural(len(same), 'no cambia', 'no cambian')}: ya {_plural(len(same), 'tenía', 'tenían')} 0 en esa columna."
            text += f" {p['entering']} entra a la base en lugar de {p['leaving']}."
            add("hecho", "¿Qué se hizo?", text)
        elif stage == "limpieza":
            p = e["pivot"]
            add("hecho", "¿Qué se hizo?",
                f"{p['leaving']} seguía en la base con valor 0. Se pivotea en {p['row']} con {p['entering']} (coeficiente "
                f"{p['element']}) para sacarla; como K = 0 en esa fila, el punto no cambia.")
        elif stage == "redundante":
            add("hecho", "¿Qué se hizo?",
                f"Al retirar las artificiales, {e['removed']} quedó como 0 = 0: es una restricción redundante y se elimina esa fila.")
        elif stage == "f2_original":
            nonzero = [b for b in e["basis"] if T[0][e["columns"].index(b)] != 0]
            text = (f"Fase 2: se retiran la fila r y las columnas artificiales y se conserva la base {', '.join(e['basis'])}. "
                    f"Se escribe la Z original, {_objective_equation(model)}, con K = 0.")
            text += (f" Las básicas {', '.join(nonzero)} todavía tienen coeficiente distinto de 0 en Z: falta vincular Z con la base."
                     if nonzero else " Las básicas ya tienen 0 en Z.")
            add("hecho", "¿Qué se hizo?", text)
        elif stage == "f2_canonica":
            if e["operations"]:
                sources = ", ".join(f"({op['multiplier']})·{op['source']}" for op in e["operations"])
                add("hecho", "¿Qué se hizo?",
                    f"Se suman a Z las filas de las básicas multiplicadas por el opuesto de su coeficiente: {sources}. Así quedan "
                    "con 0 en Z y K muestra el valor de Z para la base heredada.")
            else:
                add("hecho", "¿Qué se hizo?", "Las básicas ya tenían 0 en Z: no hace falta reducir.")

        reading = "Variables básicas: " + ", ".join(f"{b} = {T[i + 1][-1]}" for i, b in enumerate(e["basis"]))
        reading = (reading + "; las demás valen 0.") if e["basis"] else "No quedan filas con variables básicas."
        if stage not in ("f1_inicial", "f2_original"):
            reading += f" {obj} = {T[0][-1]}."
        if e["phase"] == 1 and e["artificial_sum"] > 0:
            reading += f" El punto {_point_text(e['point'])} todavía no es factible: las artificiales suman {e['artificial_sum']}."
        elif model and len(e["point"]) <= 4:
            reading += f" Punto actual: x = {_point_text(e['point'])}."
        add("lectura", "¿Qué muestra la tabla?", reading)

        if nxt is not None and nxt["kind"] == "pivot":
            q = nxt["pivot"]
            if q["rule"].startswith("Limpieza"):
                add("entra", "Siguiente paso",
                    f"{q['leaving']} sigue en la base con valor 0. Antes de la Fase 2 se retira: entra {q['entering']} pivoteando en "
                    f"{q['row']} (coeficiente {q['element']}).")
            else:
                if q["rule"] == "Bland":
                    why = (f"Regla de Bland (se repitió una base): entra {q['entering']}, la variable de menor índice que mejora "
                           f"{obj} (coeficiente {q['objective_coefficient']}).")
                elif q["rule"].startswith("Más positivo"):
                    why = (f"Se minimiza {obj}: entra la variable con el mayor coeficiente positivo de la fila {obj}, "
                           f"{q['entering']} ({q['objective_coefficient']}).")
                else:
                    why = (f"Se maximiza Z: entra la variable con el coeficiente más negativo de la fila Z, "
                           f"{q['entering']} ({q['objective_coefficient']}).")
                ties = [t for t in q["entering_ties"] if t != q["entering"]]
                if ties:
                    why += f" Empata con {', '.join(ties)}; se elige la de menor índice."
                add("entra", "¿Quién entra?", why)
                parts = [f"{r['row']}: {r['rhs']} ÷ {r['coefficient']} = {r['ratio']}" for r in q["ratios"] if r["ratio"] is not None]
                skip = [r["row"] for r in q["ratios"] if r["ratio"] is None]
                text = f"Se divide K entre el coeficiente de {q['entering']} en cada fila: " + "; ".join(parts) + "."
                if skip:
                    text += f" {', '.join(skip)} no {_plural(len(skip), 'participa', 'participan')} (coeficiente ≤ 0)."
                text += f" La menor razón es {q['min_ratio']}: sale {q['leaving']} ({q['row']}) y el pivote es {q['element']}."
                if q["ratio_ties"]:
                    text += f" Empate de razones en {', '.join(q['ratio_ties'])}: sale la básica de menor índice."
                if q["degenerate"]:
                    text += " La razón es 0: pivote degenerado, cambia la base pero no el punto."
                add("sale", "¿Quién sale?", text)

        if e["phase"] == 1 and nxt is not None and nxt["phase"] == 2:
            add("conclusion", "Conclusión",
                f"r = 0: todas las artificiales valen 0, así que el punto {_point_text(e['point'])} es factible. Termina la Fase 1.")
        if nxt is None:
            if status == "infeasible":
                add("conclusion", "Conclusión",
                    f"En la fila r ya no hay coeficientes positivos, pero r = {T[0][-1]} > 0: no es posible llevar todas las "
                    "artificiales a 0. Las restricciones son incompatibles: el modelo es infactible y no se ejecuta la Fase 2.")
            elif status == "optimal":
                values = ", ".join(f"x{j+1} = {v}" for j, v in enumerate(result["solution"]))
                add("conclusion", "Conclusión",
                    f"Ya no quedan coeficientes {'negativos' if sense == 'max' else 'positivos'} en Z: ninguna variable no básica "
                    f"mejora Z. La solución es óptima: {values}; Z {'máximo' if sense == 'max' else 'mínimo'} = {result['objective_value']}.")
            elif status == "unbounded":
                col = e["columns"][result["unbounded_column_index"]]
                add("conclusion", "Conclusión",
                    f"Entra {col} ({T[0][result['unbounded_column_index']]}) porque mejora Z, pero en su columna no hay coeficientes "
                    f"positivos: ninguna fila limita su aumento. Z puede {'crecer' if sense == 'max' else 'disminuir'} sin límite.")
            elif status == "iteration_limit":
                add("conclusion", "Conclusión", "Se alcanzó el límite de iteraciones: no se certifica un óptimo.")
        e["narrative"] = notes
        p = e["pivot"] or {}
        e["headline"] = {"f1_inicial": "Se plantea la función auxiliar r", "f1_reducida": "Se limpia la fila r",
                         "pivote": f"Entra {p.get('entering')}, sale {p.get('leaving')}",
                         "limpieza": f"Se retira {p.get('leaving')}, que valía 0",
                         "redundante": f"{e.get('removed')} era redundante",
                         "f2_original": "Vuelve la función Z original",
                         "f2_canonica": "Se vincula Z con la base heredada"}[stage]

    # Recorrido: soluciones básicas consecutivas (se agrupan las tablas con el mismo punto).
    trajectory = []
    for e in events:
        feasible = not (e["phase"] == 1 and e["artificial_sum"] > 0)
        if trajectory and trajectory[-1]["point"] == e["point"] and trajectory[-1]["feasible"] == feasible:
            trajectory[-1]["tables"].append(e["number"])
            trajectory[-1]["phases"] = sorted(set(trajectory[-1]["phases"]) | {e["phase"]})
        else:
            trajectory.append({"point": e["point"], "tables": [e["number"]], "feasible": feasible, "phases": [e["phase"]],
                               "artificial_sum": e["artificial_sum"],
                               "z": sum((c * v for c, v in zip(model["objective"], e["point"])), F(0))})
    first_feasible = next((i for i, t in enumerate(trajectory) if t["feasible"]), None)
    for i, t in enumerate(trajectory):
        last = i == len(trajectory) - 1
        if not t["feasible"]:
            t["note"] = ("Punto de partida: " if i == 0 else "Aún fuera de la región: ") + f"las artificiales suman {t['artificial_sum']}."
        elif last and status == "optimal":
            t["note"] = f"Óptimo: Z = {t['z']}."
        elif last and status == "unbounded":
            t["note"] = f"Z = {t['z']} aquí, pero desde este punto Z mejora sin límite."
        elif i == first_feasible and 1 in t["phases"]:
            t["note"] = f"Primer punto factible: termina la Fase 1 (Z = {t['z']})."
        else:
            t["note"] = f"Punto factible intermedio: Z = {t['z']}."
    result["trajectory"] = trajectory
    r_values = [e["tableau"][0][-1] for e in events if e["phase"] == 1 and e["stage"] in ("f1_reducida", "pivote", "limpieza")]
    z_values = [e["tableau"][0][-1] for e in events if e["phase"] == 2 and e["stage"] in ("f2_canonica", "pivote")]
    p1 = sum(1 for e in events if e["phase"] == 1 and e["kind"] == "pivot")
    p2 = sum(1 for e in events if e["phase"] == 2 and e["kind"] == "pivot")
    story = []
    if r_values:
        if p1:
            text = f"{p1} {_plural(p1, 'pivote')}: r pasó de {r_values[0]} a {r_values[-1]}"
        elif r_values[-1] == 0:
            text = "Sin pivotes: no hacían falta artificiales y r = 0 desde el inicio"
        else:
            text = f"Sin pivotes posibles: r se quedó en {r_values[-1]}"
        story.append({"phase": 1, "label": "Fase 1 · llegar a lo factible", "text": text, "values": r_values, "symbol": "r"})
    if z_values:
        if status == "unbounded":
            text = (f"{p2} {_plural(p2, 'pivote')}: Z pasó de {z_values[0]} a {z_values[-1]}; después Z puede mejorar sin límite"
                    if p2 else f"Sin pivotes: desde la base heredada (Z = {z_values[-1]}) ya hay una dirección en la que Z mejora sin límite")
        else:
            text = (f"{p2} {_plural(p2, 'pivote')}: Z pasó de {z_values[0]} a {z_values[-1]}" if p2 else
                    f"Sin pivotes: la base heredada de la Fase 1 ya era la mejor (Z = {z_values[-1]})")
        meta = "subir al óptimo" if sense == "max" else "bajar al óptimo"
        if status == "unbounded":
            meta = "Z mejora sin tope"
        story.append({"phase": 2, "label": f"Fase 2 · {meta}",
                      "text": text, "values": z_values, "symbol": "Z"})
    result["story"] = story


def _lista(partes):
    partes = [p for p in partes if p]
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1] if partes else ""


def _cantidad(valor, unidad):
    return f"{valor} {unidad}".strip()


def conclude(result, model):
    """Conclusión final en el contexto del usuario: decisión, valor de Z y condiciones que limitan.

    Solo redacta con los valores ya verificados; no calcula nada nuevo.
    """
    status, maxi = result["status"], model["sense"] == "max"
    variables, zname, zunit = model["variables"], model["objective_name"], model["objective_unit"]
    if status == "optimal":
        x, z = result["solution"], result["objective_value"]
        dentro = [f"{v['name']} = {_cantidad(val, v['unit'])}" for v, val in zip(variables, x) if val != 0]
        fuera = [v["name"] for v, val in zip(variables, x) if val == 0]
        lead = (f"La mejor decisión es {_lista(dentro)}." if dentro else "La mejor decisión es dejar todas las variables en 0.")
        if fuera:
            lead += f" {_lista(fuera)} {'queda' if len(fuera) == 1 else 'quedan'} en 0: no {'conviene' if len(fuera) == 1 else 'convienen'} en este plan."
        lead += (f" Con esa combinación se obtiene Z = {_cantidad(z, zunit)} ({zname}), "
                 f"el {'máximo' if maxi else 'mínimo'} posible con las condiciones planteadas.")
        limitan = [ch["label"] for ch in result["verification"] if ch["binding"]]
        puntos = []
        for ch in result["verification"]:
            u = f" {ch['unit']}" if ch["unit"] else ""
            if ch["operator"] == "=":
                puntos.append(f"{ch['label']}: queda en {ch['rhs']}{u}, tal como se exige.")
            elif ch["operator"] == "<=":
                puntos.append(f"{ch['label']}: se usa por completo ({ch['lhs']} de {ch['rhs']}{u})." if ch["binding"] else
                              f"{ch['label']}: se usan {ch['lhs']} de {ch['rhs']}{u}; quedan {ch['margin']}{u} sin usar.")
            else:
                puntos.append(f"{ch['label']}: se cumple justo en el mínimo ({ch['rhs']}{u})." if ch["binding"] else
                              f"{ch['label']}: se supera el mínimo en {ch['margin']}{u} ({ch['lhs']} frente a {ch['rhs']}{u}).")
        cierre = []
        if limitan:
            cierre.append(f"{'La condición que limita' if len(limitan) == 1 else 'Las condiciones que limitan'} el resultado "
                          f"{'es' if len(limitan) == 1 else 'son'} {_lista(limitan)}: si {'cambia' if len(limitan) == 1 else 'cambian'}, "
                          f"cambia el {'máximo' if maxi else 'mínimo'} de Z.")
        if result.get("alternate_directions"):
            cierre.append(f"Hay otras combinaciones con el mismo valor de Z (óptimos alternativos); esta es una de ellas.")
        if any(F(v).denominator != 1 for v in x):
            cierre.append("Hay valores fraccionarios porque el modelo es continuo; si las cantidades deben ser enteras, "
                          "redondear no garantiza la mejor solución.")
        cifras = [{"label": v["name"], "symbol": v["symbol"], "value": val, "unit": v["unit"]} for v, val in zip(variables, x)]
        cifras.append({"label": zname, "symbol": "Z", "value": z, "unit": zunit, "main": True})
        return {"tone": "optimal", "title": f"{'Máximo' if maxi else 'Mínimo'} de {zname}: {_cantidad(z, zunit)}",
                "lead": lead, "points": puntos, "closing": cierre, "figures": cifras}
    if status == "infeasible":
        faltan = []
        for name, value in result.get("artificial_values", {}).items():
            if value:
                item = model["constraints"][int(name[1:]) - 1]
                u = f" {item['unit']}" if item["unit"] else ""
                faltan.append(f"{item['label']} (R{name[1:]}): quedan {value}{u} sin cubrir.")
        nombres = _lista([v["name"] for v in variables])
        lead = (f"Con las condiciones planteadas no existe ningún valor de {nombres} que las cumpla todas a la vez. "
                f"La Fase 1 terminó con r = {result['phase1_value']} (mayor que 0), así que no se puede pasar a la Fase 2 "
                f"ni hablar de un {'máximo' if maxi else 'mínimo'} de Z ({zname}).")
        return {"tone": "infeasible", "title": "El modelo no tiene solución factible", "lead": lead, "points": faltan,
                "closing": ["Hay que revisar los datos: alguna exigencia mínima supera lo que permiten los límites, o hay un signo o "
                            "una relación (≤, ≥, =) mal escrita."],
                "figures": [{"label": "suma de artificiales al final de la Fase 1", "symbol": "r", "value": result["phase1_value"], "unit": "", "main": True}]}
    if status == "unbounded":
        x, ray, gain = result["solution"], result["ray"], result["ray_gain"]
        crecen = [f"{v['name']}" for v, d in zip(variables, ray) if d > 0]
        punto = _lista([f"{v['name']} = {_cantidad(val, v['unit'])}" for v, val in zip(variables, x)])
        lead = (f"{zname} (Z) no tiene un valor {'máximo' if maxi else 'mínimo'}: puede {'crecer' if maxi else 'bajar'} sin límite. "
                f"Partiendo de {punto} (Z = {_cantidad(result['objective_value'], zunit)}), "
                f"si se {'aumentan' if len(crecen) > 1 else 'aumenta'} {_lista(crecen) or 'la variable que entra'}, todas las condiciones se siguen cumpliendo y "
                f"Z {'sube' if gain > 0 else 'baja'} {_cantidad(abs(gain), zunit)} por cada paso.")
        puntos = [f"{v['name']} {'aumenta' if d > 0 else 'disminuye'} {_cantidad(abs(d), v['unit'])} por cada paso."
                  for v, d in zip(variables, ray) if d]
        return {"tone": "unbounded", "title": f"{zname} no tiene {'máximo' if maxi else 'mínimo'}", "lead": lead, "points": puntos,
                "closing": ["En un problema real esto suele indicar que falta una restricción, por ejemplo una capacidad o un presupuesto."],
                "figures": []}
    return {"tone": "stopped", "title": "Cálculo detenido", "lead": result.get("message", ""), "points": [],
            "closing": ["El límite de iteraciones nunca se presenta como un óptimo."], "figures": []}


def serialize(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: serialize(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Ejemplos reproducibles. El primero corresponde a las capturas del curso.
# Nombres, unidades y contextos son ILUSTRATIVOS: los coeficientes y relaciones
# son los que definen el modelo matemático.
# ---------------------------------------------------------------------------
EXAMPLES = {
    "profesora": {
        "sense": "max", "objective": ["5", "8"],
        "constraints": [
            {"coefficients": ["2", "1"], "operator": "=", "rhs": "12", "label": "Recurso utilizado exactamente", "unit": "unidades de recurso"},
            {"coefficients": ["1", "1"], "operator": ">=", "rhs": "8", "label": "Producción mínima", "unit": "unidades"},
            {"coefficients": ["0", "1"], "operator": "<=", "rhs": "8", "label": "Límite del producto B", "unit": "unidades"}],
        "variables": [{"name": "Producto A", "unit": "unidades"}, {"name": "Producto B", "unit": "unidades"}],
        "context": "Un taller fabrica los productos A y B; utiliza exactamente 12 unidades de recurso (2 por A y 1 por B), produce como mínimo 8 unidades en total y como máximo 8 de B. La contribución por unidad es 5 para A y 8 para B.",
        "objective_name": "Contribución total", "objective_unit": "unidades monetarias"},
    "minimo": {
        "sense": "min", "objective": ["2", "3"],
        "constraints": [
            {"coefficients": ["1", "1"], "operator": ">=", "rhs": "4", "label": "Cobertura mínima", "unit": "horas"},
            {"coefficients": ["1", "3"], "operator": ">=", "rhs": "6", "label": "Capacidad mínima", "unit": "puntos de capacidad"}],
        "variables": [{"name": "Servicio A", "unit": "horas"}, {"name": "Servicio B", "unit": "horas"}],
        "context": "Se contratan horas de dos servicios para cubrir dos necesidades al menor costo.",
        "objective_name": "Costo total", "objective_unit": "unidades monetarias"},
    "infactible": {
        "sense": "max", "objective": ["1"],
        "constraints": [
            {"coefficients": ["1"], "operator": ">=", "rhs": "3", "label": "Pedido mínimo", "unit": "unidades"},
            {"coefficients": ["1"], "operator": "<=", "rhs": "1", "label": "Capacidad máxima", "unit": "unidades"}],
        "variables": [{"name": "Producción", "unit": "unidades"}],
        "context": "Se exige producir al menos 3 unidades, pero la capacidad permite como máximo 1.",
        "objective_name": "Ganancia", "objective_unit": "unidades monetarias"},
    "no_acotado": {
        "sense": "max", "objective": ["1", "1"],
        "constraints": [
            {"coefficients": ["1", "-1"], "operator": ">=", "rhs": "1", "label": "Diferencia mínima entre A y B", "unit": "unidades"}],
        "variables": [{"name": "Producto A", "unit": "unidades"}, {"name": "Producto B", "unit": "unidades"}],
        "context": "Solo se exige que A supere a B en al menos 1 unidad; no hay un tope de capacidad.",
        "objective_name": "Ganancia", "objective_unit": "unidades monetarias"},
}
