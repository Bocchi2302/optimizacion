import unittest

from app import app
from blueprints.mod_bp import calcular_mod
from blueprints.mod_solver import resolver_metodo_mod


class ModTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_ejemplos_y_signos(self):
        for a, b, q, r in [
            (10, 3, 3, 1),
            (20, 5, 4, 0),
            (0, 3, 0, 0),
            (2, 5, 0, 2),
            (-10, 3, -4, 2),
            (10, -3, -3, 1),
            (-10, -3, 4, 2),
            (17, 2, 8, 1),
        ]:
            with self.subTest(a=a, b=b):
                result = calcular_mod(a, b)
                self.assertEqual((result["cociente"], result["residuo"]), (str(q), str(r)))
                self.assertEqual(result["divisible"], r == 0)
                self.assertEqual(result["par"], a % 2 == 0)

    def test_identidad_y_rango(self):
        for a in range(-40, 41):
            for b in range(-12, 13):
                if b == 0:
                    continue
                result = calcular_mod(a, b)
                q, r = int(result["cociente"]), int(result["residuo"])
                self.assertEqual(a, b * q + r)
                self.assertTrue(0 <= r < abs(b))

    def test_precision_enteros_grandes(self):
        a = "9" * 200
        response = self.client.post("/metodo_mod/calcular", json={"dividendo": a, "divisor": "7"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["dividendo"], a)
        self.assertEqual(int(a), 7 * int(data["cociente"]) + int(data["residuo"]))

    def test_entradas_invalidas(self):
        for a, b in [
            ("10", "0"),
            ("1.5", "3"),
            ("1e3", "2"),
            ("", "2"),
            (True, 2),
            (1.0, 2),
            (None, 2),
            ("9" * 201, 2),
            ("10", "٢"),
            ([], 2),
            ("10", "--2"),
        ]:
            with self.subTest(a=a, b=b):
                response = self.client.post("/metodo_mod/calcular", json={"dividendo": a, "divisor": b})
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
        for body in [[], None, "texto", {}]:
            self.assertEqual(self.client.post("/metodo_mod/calcular", json=body).status_code, 400)
        self.assertEqual(
            self.client.post("/metodo_mod/calcular", data="{", content_type="application/json").status_code,
            400,
        )

    def test_paginas_y_recursos(self):
        self.assertIn(b"/metodo_mod/", self.client.get("/").data)
        self.assertEqual(self.client.get("/metodo_grafico/").status_code, 200)
        page = self.client.get("/metodo_mod/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Contexto del ejercicio", page.get_data(as_text=True))
        for resource, content_type in [("mod.css", "text/css"), ("mod.js", "javascript")]:
            with self.client.get("/metodo_mod/assets/" + resource) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response.content_type)

    def test_modi_maximizacion_y_costes_mejora(self):
        """Verifica que el Método MOD en maximización optimice y reporte costes de mejora <= 0."""
        costos = [[10, 12, 15], [14, 10, 16], [12, 15, 11]]
        oferta = [30, 40, 30]
        demanda = [25, 35, 40]
        contexto = "Optimizar ganancias de despachos entre 3 fábricas y 3 distribuidores"

        resultado = resolver_metodo_mod(
            costos, oferta, demanda, tipo_opt="max", contexto=contexto
        )

        self.assertEqual(resultado["tipo_opt"], "max")
        self.assertEqual(resultado["solucion_optima"]["z_str"], "1475")

        # Verificar que todos los costes de mejora en la solución final sean <= 0
        costes_mejora = resultado["solucion_optima"]["costes_mejora"]
        self.assertTrue(len(costes_mejora) > 0)
        for cm in costes_mejora:
            self.assertLessEqual(cm["delta"], 0, f"En maximización, el coste de mejora debe ser <= 0: {cm}")

        # Verificar que la conclusión incluya el contexto y los costes de mejora
        conclusion = resultado["conclusion"]
        self.assertIn(contexto, conclusion["parrafos"][0])
        self.assertIn("costes de mejora", conclusion["analisis_costes_mejora"].lower())
        self.assertIn("maximización", conclusion["analisis_costes_mejora"].lower())

    def test_modi_minimizacion_y_costes_mejora(self):
        """Verifica que el Método MOD en minimización optimice y reporte costes de mejora >= 0."""
        costos = [[2, 3, 5, 1], [7, 3, 4, 6], [4, 1, 7, 2]]
        oferta = [30, 40, 20]
        demanda = [20, 25, 25, 20]
        contexto = "Minimizar costos de transporte"

        resultado = resolver_metodo_mod(
            costos, oferta, demanda, tipo_opt="min", contexto=contexto
        )

        self.assertEqual(resultado["tipo_opt"], "min")
        self.assertEqual(resultado["solucion_optima"]["z_str"], "225")

        # Verificar que todos los costes de mejora en la solución final sean >= 0
        costes_mejora = resultado["solucion_optima"]["costes_mejora"]
        self.assertTrue(len(costes_mejora) > 0)
        for cm in costes_mejora:
            self.assertGreaterEqual(cm["delta"], 0, f"En minimización, el coste de mejora debe ser >= 0: {cm}")

        # Verificar conclusión
        conclusion = resultado["conclusion"]
        self.assertIn("minimización", conclusion["analisis_costes_mejora"].lower())
        self.assertIn("costes de mejora", conclusion["analisis_costes_mejora"].lower())

    def test_formulario_post_contexto_y_conclusion_html(self):
        """Prueba envío POST del formulario web con contexto y visualización de conclusión y costes de mejora."""
        datos_formulario = {
            "contexto": "Empresa distribuidora de bebidas y alimentos",
            "tipo_opt": "max",
            "num_origenes": "3",
            "num_destinos": "3",
            "costo_0_0": "10",
            "costo_0_1": "12",
            "costo_0_2": "15",
            "oferta_0": "30",
            "costo_1_0": "14",
            "costo_1_1": "10",
            "costo_1_2": "16",
            "oferta_1": "40",
            "costo_2_0": "12",
            "costo_2_1": "15",
            "costo_2_2": "11",
            "oferta_2": "30",
            "demanda_0": "25",
            "demanda_1": "35",
            "demanda_2": "40",
        }

        response = self.client.post("/metodo_mod/", data=datos_formulario)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Debe mostrar el contexto en la respuesta
        self.assertIn("Empresa distribuidora de bebidas y alimentos", html)
        # Debe mostrar la conclusión
        self.assertIn("Conclusión e Interpretación Gerencial", html)
        # Debe mostrar el valor óptimo
        self.assertIn("1475", html)
        # Debe mostrar la sección de costes de mejora
        self.assertIn("Costes de Mejora", html)


if __name__ == "__main__":
    unittest.main()
