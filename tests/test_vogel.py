import unittest
from decimal import Decimal

from blueprints.vogel_bp import redactar_analisis, resolver_vogel


class ResolverVogelTests(unittest.TestCase):
    def test_resuelve_problema_balanceado_y_respeta_oferta_demanda(self):
        resultado = resolver_vogel(
            [
                [Decimal(19), Decimal(30), Decimal(50), Decimal(10)],
                [Decimal(70), Decimal(30), Decimal(40), Decimal(60)],
                [Decimal(40), Decimal(8), Decimal(70), Decimal(20)],
            ],
            [Decimal(7), Decimal(9), Decimal(18)],
            [Decimal(5), Decimal(8), Decimal(7), Decimal(14)],
        )

        self.assertEqual(resultado["costo_total"], Decimal(779))
        for i, oferta in enumerate([Decimal(7), Decimal(9), Decimal(18)]):
            self.assertEqual(sum(resultado["asignaciones"][i]), oferta)
        for j, demanda in enumerate(
            [Decimal(5), Decimal(8), Decimal(7), Decimal(14)]
        ):
            self.assertEqual(
                sum(fila[j] for fila in resultado["asignaciones"]), demanda
            )

    def test_agrega_origen_ficticio_si_demanda_supera_oferta(self):
        resultado = resolver_vogel(
            [[Decimal(4), Decimal(6)]],
            [Decimal(3)],
            [Decimal(2), Decimal(4)],
        )

        self.assertEqual(resultado["origenes"], ["Origen 1", "Origen ficticio"])
        self.assertEqual(resultado["asignaciones"][1], [Decimal(0), Decimal(3)])
        self.assertEqual(resultado["asignaciones"][0], [Decimal(2), Decimal(1)])
        self.assertEqual(resultado["costo_total"], Decimal(14))

    def test_agrega_destino_ficticio_si_oferta_supera_demanda(self):
        resultado = resolver_vogel(
            [[Decimal(4)], [Decimal(7)]],
            [Decimal(5), Decimal(2)],
            [Decimal(4)],
        )

        self.assertEqual(resultado["destinos"], ["Destino 1", "Destino ficticio"])
        self.assertEqual(
            [fila[1] for fila in resultado["asignaciones"]],
            [Decimal(1), Decimal(2)],
        )
        self.assertEqual(resultado["costo_total"], Decimal(16))

    def test_rechaza_dimensiones_incompatibles(self):
        with self.assertRaisesRegex(ValueError, "dimensiones"):
            resolver_vogel([[Decimal(1)]], [Decimal(1)], [Decimal(1), Decimal(2)])

    def test_rechaza_oferta_negativa(self):
        with self.assertRaisesRegex(ValueError, "no pueden ser negativas"):
            resolver_vogel([[Decimal(1)]], [Decimal(-1)], [Decimal(1)])


class IteracionesVogelTests(unittest.TestCase):
    """Cada iteración debe registrar los pasos 2 a 9 con sus cálculos."""

    def setUp(self):
        self.res = resolver_vogel(
            [
                [Decimal(19), Decimal(30), Decimal(50), Decimal(10)],
                [Decimal(70), Decimal(30), Decimal(40), Decimal(60)],
                [Decimal(40), Decimal(8), Decimal(70), Decimal(20)],
            ],
            [Decimal(7), Decimal(9), Decimal(18)],
            [Decimal(5), Decimal(8), Decimal(7), Decimal(14)],
        )

    def test_paso_1_balance(self):
        balance = self.res["balance"]
        self.assertTrue(balance["balanceado"])
        self.assertEqual(balance["suma_oferta"], "7 + 9 + 18")
        self.assertEqual(balance["oferta_total"], Decimal(34))

    def test_primera_iteracion_penalizaciones_y_asignacion(self):
        it = self.res["iteraciones"][0]
        self.assertEqual([p["valor"] for p in it["pen_filas"]], [9, 10, 12])
        self.assertEqual([p["valor"] for p in it["pen_cols"]], [21, 22, 10, 10])
        self.assertEqual(it["pen_cols"][1]["menor"], 8)
        self.assertEqual(it["pen_cols"][1]["segundo"], 30)
        self.assertEqual(it["max_pen"], 22)
        self.assertEqual(it["elegido"], {"tipo": "columna", "indice": 1, "nombre": "Destino 2"})
        self.assertEqual(it["celda"], (2, 1))
        self.assertEqual((it["oferta_antes"], it["demanda_antes"], it["cantidad"]), (18, 8, 8))
        self.assertEqual((it["oferta_despues"], it["demanda_despues"]), (10, 0))
        self.assertEqual(it["eliminadas"], [{"tipo": "columna", "indice": 1, "nombre": "Destino 2"}])

    def test_las_penalizaciones_se_recalculan_sin_lo_eliminado(self):
        it = self.res["iteraciones"][1]
        self.assertIsNone(it["pen_cols"][1])
        self.assertEqual([p["valor"] for p in it["pen_filas"]], [9, 20, 20])

    def test_termina_cuando_todo_queda_satisfecho(self):
        ultima = self.res["iteraciones"][-1]
        self.assertEqual(len(self.res["iteraciones"]), 6)
        self.assertTrue(ultima["ultima_celda"])
        self.assertEqual((ultima["filas_restantes"], ultima["columnas_restantes"]), (0, 0))

    def test_comprobacion_uv_detecta_que_se_puede_mejorar(self):
        opt = self.res["optimalidad"]
        self.assertFalse(opt["optima"])
        self.assertEqual(opt["mejor_mejora"]["delta"], Decimal(-18))
        self.assertFalse(self.res["degenerada"])


class AnalisisVogelTests(unittest.TestCase):
    def test_usa_nombres_unidades_y_contexto(self):
        res = resolver_vogel(
            [[Decimal(4), Decimal(6)]],
            [Decimal(3)],
            [Decimal(2), Decimal(4)],
            ["Planta Norte"],
            ["Tienda A", "Tienda B"],
        )
        analisis = redactar_analisis(res, "Una fábrica reparte cajas a dos tiendas", "cajas", "$")
        texto = " ".join(p for b in analisis["bloques"] for p in b["parrafos"])
        self.assertIn("Desde Planta Norte se envían 2 cajas a Tienda A y 1 cajas a Tienda B", texto)
        self.assertIn("Tienda B quedará sin recibir 3 cajas", texto)
        self.assertEqual(analisis["valor_total"], "$14")

    def test_detecta_distancias_y_avisa_si_el_enunciado_pide_maximizar(self):
        res = resolver_vogel([[Decimal(5)]], [Decimal(2)], [Decimal(2)])
        analisis = redactar_analisis(res, "Maximizar la ganancia según los kilómetros recorridos")
        titulos = [b["titulo"] for b in analisis["bloques"]]
        self.assertEqual(analisis["tipo_valor"], "distancia")
        self.assertIn("Según el enunciado", titulos)
        self.assertTrue(analisis["resumen"].startswith("La distancia total"))


class VistaVogelTests(unittest.TestCase):
    def test_post_muestra_iteraciones_y_analisis(self):
        from app import app

        datos = {
            "num_origenes": "2", "num_destinos": "2",
            "costo_0_0": "3", "costo_0_1": "1", "costo_1_0": "2", "costo_1_1": "4",
            "oferta_0": "5", "oferta_1": "5", "demanda_0": "4", "demanda_1": "6",
            "nombre_origen_0": "Bodega", "contexto": "Reparto de bultos de cemento",
            "unidad_envio": "bultos",
        }
        respuesta = app.test_client().post("/metodo_vogel/", data=datos)
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Iteración 1", html)
        self.assertIn("Recalcular las penalizaciones", html)
        self.assertIn("Análisis del resultado", html)
        self.assertIn("Reparto de bultos de cemento", html)
        self.assertIn("Bodega", html)
        self.assertNotIn("/metodo_mod", html)
        self.assertNotIn("Método MOD", html)

    def test_post_con_dato_invalido_muestra_error(self):
        from app import app

        respuesta = app.test_client().post("/metodo_vogel/", data={"num_origenes": "1", "num_destinos": "1", "costo_0_0": "abc"})
        self.assertIn("número válido", respuesta.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
