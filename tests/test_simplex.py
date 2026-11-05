import unittest

from app import app
from blueprints.simplex_solver import resolver


def problema(sentido, costos, restricciones, **extra):
    """restricciones: lista de (coefs, rhs)."""
    return {
        "sentido": sentido,
        "variables": [{"nombre": f"x{j+1}", "costo": c} for j, c in enumerate(costos)],
        "restricciones": [{"coefs": a, "tipo": "<=", "rhs": b} for a, b in restricciones],
        **extra,
    }


class SimplexNormalTests(unittest.TestCase):
    def test_wyndor_con_sensibilidad(self):
        r = resolver(problema("max", [3, 5], [([1, 0], 4), ([0, 2], 12), ([3, 2], 18)]))
        self.assertEqual(r["estado"], "optimo")
        self.assertAlmostEqual(r["z"], 36)
        self.assertEqual(r["x"], [2, 6])
        self.assertEqual([round(d["precio_sombra"], 6) for d in r["sens_restricciones"]], [0, 1.5, 1])
        self.assertEqual((r["sens_restricciones"][1]["minimo"], r["sens_restricciones"][1]["maximo"]), (6, 18))
        self.assertEqual((r["sens_variables"][0]["minimo"], r["sens_variables"][0]["maximo"]), (0, 7.5))
        self.assertIsNone(r["sens_variables"][1]["maximo"])

    def test_tablas_marcan_pivote_y_terminan_en_optimo(self):
        r = resolver(problema("max", [3, 5], [([1, 0], 4), ([0, 2], 12), ([3, 2], 18)]))
        its = r["iterations"]
        self.assertEqual(len(its), 3)
        self.assertEqual(its[0]["pivot"], [1, 1])
        self.assertIsNone(its[-1]["pivot"])
        self.assertEqual(its[-1]["rows"][-1][-1], 36)

    def test_cada_tabla_explica_el_paso_y_muestra_razones(self):
        its = resolver(problema("max", [3, 5], [([1, 0], 4), ([0, 2], 12), ([3, 2], 18)]))["iterations"]
        self.assertEqual(its[0]["ratios"], [None, 6, 9])
        self.assertIn("Punto de partida", its[0]["explicacion"])
        self.assertIn("Entra x2", its[0]["explicacion"])
        self.assertIn("12/2 = 6", its[0]["explicacion"])
        self.assertIn("sale de la base", its[0]["explicacion"])
        self.assertIn("único valor negativo", its[1]["explicacion"])
        self.assertIsNone(its[-1]["ratios"])
        self.assertIn("óptima", its[-1]["explicacion"])
        self.assertIn("Z = 36", its[-1]["explicacion"])

    def test_efecto_de_un_recurso_sobre_las_variables_predice_el_nuevo_optimo(self):
        base = problema("max", [3, 5], [([1, 0], 4), ([0, 2], 12), ([3, 2], 18)])
        r = resolver(base)
        planta2 = r["sens_restricciones"][1]
        self.assertAlmostEqual(planta2["efecto_variables"][0], -1 / 3, places=6)
        self.assertAlmostEqual(planta2["efecto_variables"][1], 0.5, places=6)
        # dentro del rango [6, 18] la predicción lineal coincide con volver a resolver
        for nuevo in (6, 9, 15, 18):
            delta = nuevo - planta2["rhs"]
            base["restricciones"][1]["rhs"] = nuevo
            real = resolver(base)
            self.assertAlmostEqual(real["z"], r["z"] + planta2["precio_sombra"] * delta, places=6)
            for j in range(2):
                self.assertAlmostEqual(real["x"][j], r["x"][j] + planta2["efecto_variables"][j] * delta, places=6)

    def test_explicacion_de_no_acotado(self):
        its = resolver(problema("max", [1, 1], [([1, -1], 2)]))["iterations"]
        self.assertIn("sin límite", its[-1]["explicacion"])

    def test_minimizar_con_costos_negativos(self):
        # min -x - y  s.a. x + y <= 4, x <= 3   ->  Z = -4
        r = resolver(problema("min", [-1, -1], [([1, 1], 4), ([1, 0], 3)]))
        self.assertAlmostEqual(r["z"], -4)

    def test_no_acotado(self):
        r = resolver(problema("max", [1, 1], [([1, -1], 2)]))
        self.assertEqual(r["estado"], "no_acotado")
        self.assertTrue(any("no acotado" in s["titulo"] for s in r["interpretacion"]))

    def test_optimos_multiples(self):
        r = resolver(problema("max", [1, 1], [([1, 1], 4), ([1, 0], 3)]))
        self.assertTrue(r["optimos_multiples"])

    def test_interpretacion_usa_el_contexto(self):
        r = resolver(problema("max", [3, 5], [([1, 0], 4), ([0, 2], 12), ([3, 2], 18)],
                              contexto="Una fábrica quiere maximizar la ganancia.", unidad_z="miles de pesos"))
        texto = " ".join(i for s in r["interpretacion"] for i in s["items"])
        self.assertIn("ganancia máxima", texto)
        self.assertIn("36 miles de pesos", texto)
        self.assertIn("LIMITANTE", texto)

    def test_rechaza_lo_que_es_de_dos_fases(self):
        malo = problema("max", [1], [([1], 5)])
        malo["restricciones"][0]["tipo"] = ">="
        with self.assertRaises(ValueError):
            resolver(malo)
        with self.assertRaises(ValueError):
            resolver(problema("max", [1], [([1], -5)]))

    def test_rechaza_datos_invalidos(self):
        with self.assertRaises(ValueError):
            resolver(problema("max", ["abc"], [([1], 5)]))
        with self.assertRaises(ValueError):
            resolver(problema("max", [1, 2], [([1], 5)]))
        with self.assertRaises(ValueError):
            resolver({"sentido": "otro"})

    def test_acepta_fracciones_y_comas(self):
        r = resolver(problema("max", ["1/2", "2,5"], [([1, 1], "10")]))
        self.assertAlmostEqual(r["z"], 25)

    def test_blueprint_y_api(self):
        client = app.test_client()
        self.assertEqual(client.get("/metodo_simplex/").status_code, 200)
        ok = client.post("/metodo_simplex/api/simplex",
                         json=problema("max", [3, 5], [([1, 0], 4), ([0, 2], 12), ([3, 2], 18)]))
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.get_json()["z"], 36)
        self.assertEqual(client.post("/metodo_simplex/api/simplex", json={}).status_code, 400)
        self.assertEqual(client.post("/metodo_simplex/api/simplex", data="no json").status_code, 400)


class ContraScipy(unittest.TestCase):
    def test_aleatorios(self):
        try:
            from scipy.optimize import linprog
        except ImportError:
            self.skipTest("scipy no instalado")
        import random
        rnd = random.Random(11)
        comparados = 0
        for _ in range(300):
            n, m = rnd.randint(2, 5), rnd.randint(2, 6)
            sentido = rnd.choice(["max", "min"])
            c = [rnd.randint(-4, 9) for _ in range(n)]
            rest = [([rnd.randint(-2, 6) for _ in range(n)], rnd.randint(0, 25)) for _ in range(m)]
            r = resolver(problema(sentido, c, rest))
            cc = c if sentido == "min" else [-v for v in c]
            s = linprog(cc, A_ub=[a for a, _ in rest], b_ub=[b for _, b in rest],
                        bounds=[(0, None)] * n, method="highs")
            self.assertEqual(r["estado"], {0: "optimo", 3: "no_acotado"}[s.status], (sentido, c, rest))
            if s.status == 0:
                self.assertAlmostEqual(r["z"], s.fun if sentido == "min" else -s.fun, places=6)
                comparados += 1
        self.assertGreater(comparados, 100)


if __name__ == "__main__":
    unittest.main()
