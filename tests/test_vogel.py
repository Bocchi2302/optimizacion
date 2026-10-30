import unittest
from decimal import Decimal

from blueprints.vogel_bp import resolver_vogel


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


if __name__ == "__main__":
    unittest.main()
