"""Auditoría independiente del motor.

1. Vuelve a calcular, con Fraction y sin usar el motor, cada pivote registrado
   y comprueba que la tabla siguiente es exactamente la esperada.
2. Comprueba las reglas del curso: variable entrante, razón mínima, transición
   a la Fase 2 (Z original con K = 0, luego Z canónica) y detención.
3. Contrasta estados y valores con SciPy/HiGHS si está instalado (opcional).
"""
import random
import unittest
from fractions import Fraction as F

from blueprints.dos_fases_solver import solve

try:
    from scipy.optimize import linprog
except ImportError:  # SciPy es solo un oráculo opcional
    linprog = None


def fr(row):
    return [F(v) for v in row]


def random_model(rng):
    n, m = rng.randint(1, 5), rng.randint(1, 6)
    num = lambda: rng.choice([0, 0, 1, -1, 2, -2, 3, 5, -4, 7, F(1, 2), F(3, 2), F(-1, 3), F(5, 4)])
    c = [num() for _ in range(n)]
    cons = []
    for _ in range(m):
        cons.append({"coefficients": [str(num()) for _ in range(n)], "operator": rng.choice(["<=", "<=", ">=", "="]),
                     "rhs": str(rng.choice([0, 0, 1, 2, 4, 6, 10, 12, -2, -5, F(7, 2), 20]))})
    return {"sense": rng.choice(["max", "min"]), "objective": [str(v) for v in c], "constraints": cons}


def audit_events(testcase, model, r):
    ev = r["events"]
    n = len(model["objective"])
    bland = any("Bland" in note for note in r["notes"])
    for k, e in enumerate(ev):
        tab = [fr(row) for row in e["tableau"]]
        testcase.assertEqual(len(tab) - 1, len(e["basis"]))
        # Una tabla con base canónica: columnas básicas = vectores unitarios, K >= 0 en las filas.
        if e["kind"] == "pivot" or e["title"].endswith("reducida respecto de la base") or "canónica" in e["title"]:
            for i, name in enumerate(e["basis"], 1):
                j = e["columns"].index(name)
                testcase.assertEqual([row[j] for row in tab], [F(int(x == i)) for x in range(len(tab))])
                testcase.assertGreaterEqual(tab[i][-1], 0, "K negativo en una fila")
        if e["kind"] != "pivot":
            continue
        p = e["pivot"]
        prev = ev[p["previous_table"] - 1]
        T = [fr(row) for row in prev["tableau"]]
        i, j = p["row_index"], p["column_index"]
        piv = T[i][j]
        testcase.assertNotEqual(piv, 0)
        T[i] = [v / piv for v in T[i]]
        for x in range(len(T)):
            if x != i:
                f = T[x][j]
                T[x] = [a - f * b for a, b in zip(T[x], T[i])]
        testcase.assertEqual(T, tab, f"Tabla {e['number']} no coincide con el pivoteo exacto")
        basis = prev["basis"][:]
        basis[i - 1] = prev["columns"][j]
        testcase.assertEqual(basis, e["basis"])
        if p["rule"].startswith("Limpieza"):
            continue
        # Regla de entrada.
        prow = [fr(row) for row in prev["tableau"]][0]
        nonbasic = [c for c in range(len(prev["columns"])) if prev["columns"][c] not in prev["basis"]]
        sense_min = prev["phase"] == 1 or model["sense"] == "min"
        cand = [c for c in nonbasic if (prow[c] > 0 if sense_min else prow[c] < 0)]
        testcase.assertIn(j, cand)
        if not bland:
            best = max(prow[c] for c in cand) if sense_min else min(prow[c] for c in cand)
            testcase.assertEqual(prow[j], best, "No entra el coeficiente más positivo/negativo")
        # Razón mínima: solo coeficientes positivos, razón cero permitida.
        T0 = [fr(row) for row in prev["tableau"]]
        ratios = {x: T0[x][-1] / T0[x][j] for x in range(1, len(T0)) if T0[x][j] > 0}
        testcase.assertIn(i, ratios)
        testcase.assertEqual(ratios[i], min(ratios.values()))
        testcase.assertTrue(all(F(x["rhs"]) >= 0 for x in p["ratios"]))
    # Transición.
    phases = [e["phase"] for e in ev]
    if 2 in phases:
        first2 = phases.index(2)
        z0 = fr(ev[first2]["tableau"][0])
        testcase.assertEqual(z0, [-F(c) for c in model["objective"]] + [F(0)] * (len(z0) - n),
                             "Z original debe verse con -cj y K = 0")
        testcase.assertFalse(any(name.startswith("A") for name in ev[first2]["columns"]))
        z1 = fr(ev[first2 + 1]["tableau"][0])
        for name in ev[first2 + 1]["basis"]:
            testcase.assertEqual(z1[ev[first2 + 1]["columns"].index(name)], 0)
    testcase.assertEqual(sorted(e["number"] for e in ev), list(range(1, len(ev) + 1)))


def check_solution(testcase, model, r):
    x = [F(v) for v in r["solution"]]
    testcase.assertTrue(all(v >= 0 for v in x))
    for item in model["constraints"]:
        lhs = sum(F(a) * v for a, v in zip(item["coefficients"], x))
        b = F(item["rhs"])
        op = item["operator"]
        testcase.assertTrue(lhs <= b if op == "<=" else lhs >= b if op == ">=" else lhs == b)


class AuditTests(unittest.TestCase):
    def test_random_models_internal_consistency(self):
        rng = random.Random(7771)
        seen = {"optimal": 0, "infeasible": 0, "unbounded": 0}
        for case in range(700):
            model = random_model(rng)
            r = solve(model)
            self.assertIn(r["status"], seen, f"estado inesperado en caso {case}")
            seen[r["status"]] += 1
            with self.subTest(case=case, status=r["status"]):
                audit_events(self, model, r)
                if r["status"] == "optimal":
                    check_solution(self, model, r)
                    last = [F(v) for v in r["events"][-1]["tableau"][0][:-1]]
                    self.assertTrue(all(v >= 0 for v in last) if model["sense"] == "max" else all(v <= 0 for v in last))
                    self.assertEqual(F(r["objective_value"]), sum(F(c) * F(v) for c, v in zip(model["objective"], r["solution"])))
                elif r["status"] == "infeasible":
                    self.assertGreater(F(r["phase1_value"]), 0)
                    self.assertFalse(any(e["phase"] == 2 for e in r["events"]))
                elif r["status"] == "unbounded":
                    check_solution(self, model, r)
                    col = [F(row[r["unbounded_column_index"]]) for row in r["events"][-1]["tableau"][1:]]
                    self.assertTrue(all(v <= 0 for v in col))
                    d = [F(v) for v in r["ray"]]
                    x = [F(a) + 1000 * b for a, b in zip(r["solution"], d)]
                    self.assertTrue(all(v >= 0 for v in x))
                    for item in model["constraints"]:
                        lhs = sum(F(a) * v for a, v in zip(item["coefficients"], x))
                        b, op = F(item["rhs"]), item["operator"]
                        self.assertTrue(lhs <= b if op == "<=" else lhs >= b if op == ">=" else lhs == b)
        for key in seen:  # el generador debe ejercitar los tres estados
            self.assertGreater(seen[key], 20, f"pocos casos {key}: {seen}")

    @unittest.skipIf(linprog is None, "Comparación opcional: requiere scipy")
    def test_against_highs_with_fractions(self):
        rng = random.Random(424242)
        for case in range(700):
            model = random_model(rng)
            r = solve(model)
            sign = -1 if model["sense"] == "max" else 1
            aub, bub, aeq, beq = [], [], [], []
            for item in model["constraints"]:
                a = [float(F(v)) for v in item["coefficients"]]
                b = float(F(item["rhs"]))
                if item["operator"] == "=":
                    aeq.append(a); beq.append(b)
                else:
                    s = -1 if item["operator"] == ">=" else 1
                    aub.append([s * v for v in a]); bub.append(s * b)
            ref = linprog([sign * float(F(c)) for c in model["objective"]], A_ub=aub or None, b_ub=bub or None,
                          A_eq=aeq or None, b_eq=beq or None, method="highs", options={"presolve": False})
            with self.subTest(case=case):
                self.assertEqual(r["status"], {0: "optimal", 2: "infeasible", 3: "unbounded"}[ref.status])
                if ref.status == 0:
                    self.assertAlmostEqual(float(F(r["objective_value"])), sign * ref.fun, places=6)


if __name__ == "__main__":
    unittest.main()
