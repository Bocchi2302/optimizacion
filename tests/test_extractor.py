import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blueprints.grafico_extractor import ErrorExtraccion, extraer


def filas(r):
    return [(f['x'], f['y'], f['op'], f['c']) for f in r['restricciones']]


PRODUCCION = [('1', '0', '<=', '4'), ('0', '2', '<=', '12'), ('3', '2', '<=', '18')]


class ReglasTests(unittest.TestCase):
    def ex(self, texto):
        return extraer(texto)

    def test_texto_plano(self):
        r = self.ex("Maximizar Z = 3x + 5y\nsujeto a:\nx <= 4\n2y <= 12\n3x + 2y <= 18\nx, y >= 0")
        self.assertEqual((r['tipo'], r['z']), ('max', ['3', '5']))
        self.assertEqual(filas(r), PRODUCCION)
        self.assertEqual([v['simbolo'] for v in r['variables']], ['x', 'y'])
        self.assertFalse(r['requiere_revision'])

    def test_todo_en_una_linea(self):
        r = self.ex("max z = 3x1 + 5x2 s.a. x1 <= 4, 2x2 <= 12, 3x1 + 2x2 <= 18, x1,x2 >= 0")
        self.assertEqual(filas(r), PRODUCCION)
        self.assertEqual(r['advertencias'], [])

    def test_latex(self):
        r = self.ex(r"$$\max Z = 3x_1 + 5x_2 \\ \text{s.t.} \\ x_1 \leq 4 \\ 2x_2 \leq 12 \\ 3x_1 + 2x_2 \leq 18 \\ x_1, x_2 \geq 0$$")
        self.assertEqual(filas(r), PRODUCCION)

    def test_latex_aligned_minimizar(self):
        r = self.ex(r"\begin{aligned} \text{Minimizar } & Z = 2x + 3y \\ \text{sujeto a } & 2x + y \geq 8 \\ & x + 3y \geq 9 \\ & x,y \ge 0 \end{aligned}")
        self.assertEqual(r['tipo'], 'min')
        self.assertEqual(filas(r), [('2', '1', '>=', '8'), ('1', '3', '>=', '9')])

    def test_fracciones_latex_y_decimales(self):
        r = self.ex(r"Maximizar $Z = \frac{1}{2}x + \frac{3}{4}y$ sujeto a $x + y \le 10$, $x \ge 2$")
        self.assertEqual(r['z'], ['0.5', '0.75'])          # decimal exacto cuando termina
        r = self.ex("Maximizar Z = 2,5x + 1.5y\n0,5x + y <= 6,25\nx <= 5")
        self.assertEqual(r['z'], ['2.5', '1.5'])
        self.assertEqual(filas(r)[0], ('0.5', '1', '<=', '6.25'))

    def test_unicode_y_subindices(self):
        r = self.ex("Maximizar Z = 3x₁ + 5x₂\nsujeto a\nx₁ ≤ 4\n2x₂ ≤ 12\n3x₁ + 2x₂ ≤ 18")
        self.assertEqual(filas(r), PRODUCCION)

    def test_texto_con_palabras_y_numeracion(self):
        r = self.ex("Minimizar el costo C = 3x + 2y (en miles de pesos)\nRestricciones:\n1) Proteína: 2x + y ≥ 8 unidades\n2) Vitaminas: x + 3y ≥ 9 unidades\nx, y ≥ 0")
        self.assertEqual((r['tipo'], r['z']), ('min', ['3', '2']))
        self.assertEqual(filas(r), [('2', '1', '>=', '8'), ('1', '3', '>=', '9')])

    def test_enunciado_con_narracion(self):
        r = self.ex("Una fábrica produce mesas (x) y sillas (y).\nModelo:\nMaximizar Z = 30x + 20y\nSujeto a:\n2x + y <= 100 (horas de carpintería)\nx + y <= 80\nx <= 40")
        self.assertEqual(r['z'], ['30', '20'])
        self.assertEqual(len(r['restricciones']), 3)

    def test_conjuncion_y_no_se_confunde_con_la_variable_y(self):
        r = self.ex("Maximizar Z = x + y sujeto a x + y <= 10 y x >= 2 y y <= 7")
        self.assertEqual(filas(r), [('1', '1', '<=', '10'), ('1', '0', '>=', '2'), ('0', '1', '<=', '7')])

    def test_variables_en_ambos_lados_y_parentesis(self):
        r = self.ex("Maximizar Z = 2x + 3y\nx + y <= 10 - y\n2(x + y) >= x - 4\n0 <= x <= 5")
        self.assertEqual(filas(r), [('1', '2', '<=', '10'), ('1', '2', '>=', '-4'), ('1', '0', '<=', '5')])

    def test_constante_en_la_funcion_objetivo(self):
        r = self.ex("Max Z = 3x + 2y + 10; x + y <= 4; x <= 3")
        self.assertEqual((r['z'], r['z_k']), (['3', '2'], '10'))

    def test_igualdad_y_palabras_como_operador(self):
        r = self.ex("Maximizar Z = x + 2y\nx + y = 4\nx menor o igual que 3")
        self.assertEqual(filas(r), [('1', '1', '=', '4'), ('1', '0', '<=', '3')])

    def test_estrictas_se_avisan(self):
        r = self.ex("Maximizar Z = x + y\nx + y < 5\nx > 1")
        self.assertTrue(any('estrictas' in a for a in r['advertencias']))
        self.assertEqual(filas(r), [('1', '1', '<=', '5'), ('1', '0', '>=', '1')])

    def test_sin_tipo_pide_revision(self):
        r = self.ex("Z = 3x + 2y\nx + y <= 5\nx <= 3")
        self.assertIsNone(r['tipo'])
        self.assertTrue(r['requiere_revision'])

    def test_orden_natural_de_variables(self):
        r = self.ex("Maximizar Z = 2y + 3x\nx + y <= 5")
        self.assertEqual((r['variables'][0]['simbolo'], r['z']), ('x', ['3', '2']))

    def test_errores_claros(self):
        casos = {
            'tres variables': "Maximizar Z = x + y + z\nx + y + z <= 5",
            'sin objetivo': "x + y <= 5\nx >= 1",
            'sin restricciones': "Maximizar Z = x + y",
            'una variable': "Maximizar Z = 3x\nx <= 4",
            'no lineal': "Maximizar Z = x*y\nx + y <= 5",
            'solo narrativa': "Una fábrica produce mesas y sillas y quiere maximizar su ganancia.",
            'vacío': "   ",
        }
        for nombre, texto in casos.items():
            with self.subTest(nombre), self.assertRaises(ErrorExtraccion):
                self.ex(texto)

    def test_no_negatividad_en_forma_menos_x(self):
        r = self.ex("Maximizar Z = x + y\nx + y <= 5\n-x <= 0\n-y <= 0")
        self.assertEqual(len(r['restricciones']), 1)


class RutaTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        self.c = app.test_client()

    def test_extraer_ok_y_error(self):
        r = self.c.post('/metodo_grafico/extraer', json={'texto': 'Max Z = 3x + 5y\nx <= 4\n2y <= 12\n3x + 2y <= 18'}).get_json()
        self.assertTrue(r['ok'])
        self.assertEqual(r['z'], ['3', '5'])
        r = self.c.post('/metodo_grafico/extraer', json={'texto': 'hola'}).get_json()
        self.assertFalse(r['ok'])
        r = self.c.post('/metodo_grafico/extraer', data='no json').get_json()
        self.assertFalse(r['ok'])

    def test_constante_y_nombres_llegan_al_resultado(self):
        d = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'z_k': '10', 'nombre_x1': 'mesas', 'nombre_x2': 'sillas',
             'extraccion': 'reglas', 'contexto': 'Fábrica',
             'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'], 'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18']}
        html = self.c.post('/metodo_grafico/', data=d).get_data(as_text=True)
        self.assertIn('Z = 46', html)           # 36 + 10
        self.assertIn('2 mesas y 6 sillas', html)          # la conclusión usa los nombres
        self.assertIn('3X1 + 5X2 + 10', html)


if __name__ == '__main__':
    unittest.main()


class NombresTests(unittest.TestCase):
    TEXTO = """Una fábrica produce mesas (x) y sillas (y). Cada mesa deja $30 y cada silla $20.
Maximizar la ganancia total.
Modelo:
Maximizar Z = 30x + 20y
Sujeto a:
Carpintería: 2x + y <= 100
1) Pintura: x + y <= 80 horas de pintura
x <= 40 (demanda máxima de mesas)
x, y >= 0"""

    def test_detecta_nombres_objetivo_y_rotulos(self):
        r = extraer(self.TEXTO)
        self.assertEqual([v['descripcion'] for v in r['variables']], ['mesas', 'sillas'])
        self.assertEqual(r['objetivo_nombre'], 'la ganancia total')
        self.assertEqual([f['rotulo'] for f in r['restricciones']], ['Carpintería', 'Pintura', 'demanda máxima de mesas'])
        self.assertEqual(r['advertencias'], [])

    def test_definiciones_con_sea_y_dos_puntos(self):
        r = extraer("Sea x1 el número de porciones del alimento A y x2 = cantidad de porciones del alimento B. "
                    "Minimizar el costo C = 3x1 + 2x2\nsujeto a\nProteína: 2x1 + x2 >= 8 unidades\nVitaminas: x1 + 3x2 >= 9")
        self.assertEqual([v['descripcion'] for v in r['variables']], ['porciones del alimento A', 'porciones del alimento B'])
        self.assertEqual((r['objetivo_nombre'], r['tipo']), ('el costo', 'min'))
        self.assertEqual(r['advertencias'], [])
        r = extraer("donde x: horas de estudio, y: horas de trabajo. Z es la satisfacción total. Maximizar Z = 3x + 2y\nx + y <= 10")
        self.assertEqual([v['descripcion'] for v in r['variables']], ['horas de estudio', 'horas de trabajo'])
        self.assertEqual(r['objetivo_nombre'], 'la satisfacción total')

    def test_sin_pistas_no_inventa_nombres(self):
        r = extraer("Maximizar Z = 3x + 5y\nx <= 4\n2y <= 12\n3x + 2y <= 18")
        self.assertEqual([v['descripcion'] for v in r['variables']], ['', ''])
        self.assertEqual(r['objetivo_nombre'], '')
        self.assertEqual([f['rotulo'] for f in r['restricciones']], ['', '', ''])


class RelacionesEnPalabrasTests(unittest.TestCase):
    def test_como_maximo_al_menos_y_compania(self):
        r = extraer("Maximizar Z = 3x + 5y\nx + y como máximo 10\n2x + y al menos 4\nx no más de 6\n"
                    "y por lo menos 1\nx + 2y exactamente 8")
        self.assertEqual(filas_de(r), [('1', '1', '<=', '10'), ('2', '1', '>=', '4'), ('1', '0', '<=', '6'),
                                       ('0', '1', '>=', '1'), ('1', '2', '=', '8')])

    def test_listas_de_variables_con_cotas(self):
        base = "Maximizar Z = x + y\nx + y <= 10\n"
        for lista in ('x, y >= 2', 'x e y >= 2', 'x y y >= 2'):
            with self.subTest(lista):
                self.assertEqual(filas_de(extraer(base + lista))[1:], [('1', '0', '>=', '2'), ('0', '1', '>=', '2')])
        self.assertEqual(filas_de(extraer(base + 'x, y >= 0')), [('1', '1', '<=', '10')])   # no negatividad: no es restricción

    def test_la_palabra_maximo_del_objetivo_no_se_confunde(self):
        r = extraer("Maximizar el máximo de la ganancia Z = 2x + 3y\nx + y <= 7")
        self.assertEqual((r['tipo'], r['z']), ('max', ['2', '3']))


def filas_de(r):
    return [(f['x'], f['y'], f['op'], f['c']) for f in r['restricciones']]


class FormatoNumericoTests(unittest.TestCase):
    def test_decimales_exactos_y_fracciones_que_no_terminan(self):
        from fractions import Fraction as F
        from blueprints.grafico_extractor import _fmt_num
        esperado = {F(241, 2): '120.5', F(25, 4): '6.25', F(7, 10): '0.7', F(-5, 2): '-2.5', F(1, 1000): '0.001',
                    F(1, 3): '1/3', F(1, 7): '1/7', F(4): '4'}
        for q, texto in esperado.items():
            self.assertEqual(_fmt_num(q), texto)
            self.assertEqual(F(texto), q)               # nunca pierde exactitud

    def test_el_formulario_recibe_120_5_y_no_241_2(self):
        r = extraer("Maximizar Z = 120.5x + 85y + 300\nx + y <= 10")
        self.assertEqual((r['z'], r['z_k']), (['120.5', '85'], '300'))
