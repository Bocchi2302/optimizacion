"""Two-phase tableau simplex for Chebyshev (minimax) linear regression."""
from __future__ import annotations

import math

TOL = 1e-9


def _snapshot(tableau, names, basis, phase, label, pivot=None):
    return {
        "phase": phase,
        "label": label,
        "columns": names + ["LD"],
        "basis": [names[i] for i in basis],
        "rows": [[round(v, 9) for v in row] for row in tableau],
        "pivot": pivot,
    }


def _objective(tableau, basis, costs):
    row = [-v for v in costs] + [0.0]
    for i, basic in enumerate(basis):
        cost = costs[basic]
        if abs(cost) > TOL:
            row = [a + cost * b for a, b in zip(row, tableau[i])]
    tableau[-1] = row


def _pivot(tableau, basis, r, c):
    pivot = tableau[r][c]
    tableau[r] = [v / pivot for v in tableau[r]]
    for i, row in enumerate(tableau):
        if i != r:
            factor = row[c]
            tableau[i] = [a - factor * b for a, b in zip(row, tableau[r])]
    basis[r] = c


def _run(tableau, names, basis, phase, history, max_steps=500):
    for iteration in range(max_steps):
        entering = next((j for j, v in enumerate(tableau[-1][:-1]) if v < -TOL), None)
        if entering is None:
            history.append(_snapshot(tableau, names, basis, phase, "Óptimo de la fase"))
            return
        ratios = [(tableau[i][-1] / row[entering], basis[i], i)
                  for i, row in enumerate(tableau[:-1]) if row[entering] > TOL]
        if not ratios:
            raise ValueError("El problema no está acotado.")
        _, _, leaving = min(ratios)
        history.append(_snapshot(tableau, names, basis, phase,
                                 f"Entra {names[entering]}; sale {names[basis[leaving]]}",
                                 [leaving, entering]))
        _pivot(tableau, basis, leaving, entering)
    raise ValueError("Se superó el límite de iteraciones del método Simplex.")


def regress(points):
    if not isinstance(points, list) or not 3 <= len(points) <= 12:
        raise ValueError("Ingresa entre 3 y 12 puntos.")
    try:
        data = [(float(p["x"]), float(p["y"])) for p in points]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Cada punto necesita valores numéricos x e y.") from exc
    if any(not math.isfinite(x) or not math.isfinite(y) or abs(x) > 1e6 or abs(y) > 1e6
           for x, y in data):
        raise ValueError("Usa coordenadas finitas entre -1 000 000 y 1 000 000.")
    xs = [x for x, _ in data]
    if max(xs) - min(xs) < TOL:
        raise ValueError("Los puntos deben tener al menos dos valores distintos de X.")

    # Center and scale X to reduce numerical error. t=(x-center)/scale.
    center = (min(xs) + max(xs)) / 2
    scale = (max(xs) - min(xs)) / 2
    base_names = ["a+", "a-", "b+", "b-", "E"]
    rows = []
    rhs = []
    for x, y in data:
        t = (x - center) / scale
        rows.extend(([t, -t, 1, -1, -1], [-t, t, -1, 1, -1]))
        rhs.extend((y, -y))

    names = base_names[:]
    basis = []
    artificial = []
    matrix = []
    for i, (coeffs, bound) in enumerate(zip(rows, rhs)):
        if bound >= 0:
            slack_name, slack_value = f"s{i+1}", 1.0
            row, value = coeffs[:], bound
        else:
            slack_name, slack_value = f"u{i+1}", -1.0
            row, value = [-v for v in coeffs], -bound
        for prior in matrix:
            prior.insert(-1, 0.0)
        row.extend([0.0] * (len(names) - len(base_names)))
        row.append(slack_value)
        names.append(slack_name)
        if slack_value > 0:
            basis.append(len(names) - 1)
        else:
            for prior in matrix:
                prior.insert(-1, 0.0)
            row.append(1.0)
            names.append(f"A{i+1}")
            artificial.append(len(names) - 1)
            basis.append(len(names) - 1)
        row.append(value)
        matrix.append(row)

    # Adding columns to earlier rows also requires zero columns in any row
    # built before the current artificial variable.
    width = len(names) + 1
    matrix = [r[:-1] + [0.0] * (width - len(r)) + [r[-1]] if len(r) < width else r
              for r in matrix]
    tableau = matrix + [[0.0] * width]
    history = []
    costs = [-1.0 if j in artificial else 0.0 for j in range(len(names))]
    _objective(tableau, basis, costs)
    _run(tableau, names, basis, "I", history)
    if tableau[-1][-1] < -1e-7:
        raise ValueError("No existe una solución factible.")

    art_set = set(artificial)
    for i in range(len(basis) - 1, -1, -1):
        if basis[i] in art_set:
            candidate = next((j for j in range(len(names))
                              if j not in art_set and abs(tableau[i][j]) > TOL), None)
            if candidate is None:
                if abs(tableau[i][-1]) > 1e-7:
                    raise ValueError("No existe una solución factible.")
                tableau.pop(i)
                basis.pop(i)
            else:
                _pivot(tableau, basis, i, candidate)
    keep = [j for j in range(len(names)) if j not in art_set]
    mapping = {old: new for new, old in enumerate(keep)}
    tableau = [[row[j] for j in keep] + [row[-1]] for row in tableau]
    names = [names[j] for j in keep]
    basis = [mapping[j] for j in basis]
    costs = [-1.0 if name == "E" else 0.0 for name in names]
    _objective(tableau, basis, costs)
    _run(tableau, names, basis, "II", history)

    values = [0.0] * len(names)
    for i, j in enumerate(basis):
        values[j] = tableau[i][-1]
    slope_t = values[names.index("a+")] - values[names.index("a-")]
    intercept_t = values[names.index("b+")] - values[names.index("b-")]
    slope = slope_t / scale
    intercept = intercept_t - slope * center
    errors = [slope * x + intercept - y for x, y in data]
    max_error = max(abs(e) for e in errors)
    if abs(max_error - values[names.index("E")]) > 1e-5 * max(1, max_error):
        raise ValueError("La solución no superó la comprobación numérica.")
    return {
        "slope": slope, "intercept": intercept, "max_error": max_error,
        "points": [{"x": x, "y": y, "prediction": slope*x+intercept, "error": e}
                   for (x, y), e in zip(data, errors)],
        "iterations": history,
        "model": "minimax: minimizar E sujeto a -E <= ax+b-y_i <= E",
    }
