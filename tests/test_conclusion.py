import os
import sys
import unittest
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blueprints.grafico_conclusion import redactar
from blueprints.grafico_solver import Restriccion, resolver


def R(n, a, b, op, c, rot=''):
    return Restriccion(n, F(a), F(b), op, F(c), rotulo=rot)


def sol(tipo, z, rs, nombres=('', ''), obj='', zk=0):
    return resolver({'tipo': tipo, 'zx': F(z[0]), 'zy': F(z[1]), 'zk': F(zk), 'nombres': list(nombres),
                     'objetivo_nombre': obj, 'contexto': '', 'restricciones': rs})


PRODUCCION = [R('R1', 1, 0, '<=', 4, 'horas de la planta 1'), R('R2', 0, 2, '<=', 12, 'horas de la planta 2'),
              R('R3', 3, 2, '<=', 18, 'horas de la planta 3')]


class ConclusionTests(unittest.TestCase):
    def test_usa_los_nombres_del_ejercicio(self):
        c = redactar(sol('max', (3, 5), PRODUCCION, ('puertas', 'ventanas'), 'la ganancia total'))
        txt = c['texto_plano']
        self.assertIn('2 puertas y 6 ventanas', txt)
        self.assertIn('maximizar la ganancia total', txt)
        self.assertIn('el valor máximo de la ganancia total es Z = 36', txt)
        self.assertEqual(c['objetivo']['etiqueta'], 'Ganancia total')
        self.assertEqual([d['valor'] for d in c['decision']], ['2', '6'])

    def test_sin_nombres_habla_de_x1_y_x2(self):
        c = redactar(sol('max', (3, 5), [R('R1', 1, 0, '<=', 4), R('R2', 0, 2, '<=', 12), R('R3', 3, 2, '<=', 18)]))
        self.assertIn('X1 = 2 y X2 = 6', c['texto_plano'])
        self.assertIn('el valor máximo de Z', c['texto_plano'])

    def test_contrae_de_el(self):
        c = redactar(sol('min', (3, 2), [R('R1', 2, 1, '>=', 8), R('R2', 1, 3, '>=', 9)], obj='el costo'))
        self.assertIn('el valor mínimo del costo', c['texto_plano'])

    def test_recursos_agotados_y_con_holgura(self):
        c = redactar(sol('max', (3, 5), PRODUCCION))
        estados = {f['nombre']: f['estado'] for f in c['recursos']}
        self.assertEqual(estados, {'R1': 'holgura', 'R2': 'agotado', 'R3': 'agotado'})
        holgura = next(f for f in c['recursos'] if f['nombre'] == 'R1')
        self.assertEqual(holgura['holgura'], 2)
        self.assertEqual(holgura['ancho'], 50.0)
        self.assertIn('Se agotan por completo R2', c['texto_plano'])

    def test_precios_sombra_exactos(self):
        # Problema clásico de Hillier: precios sombra 3/2 y 1
        c = redactar(sol('max', (3, 5), PRODUCCION))
        self.assertEqual(len(c['sensibilidad']), 2)
        self.assertIn('de 12 a 13), Z aumentaría en 3/2', c['sensibilidad'][0])
        self.assertIn('de 18 a 19), Z aumentaría en 1.', c['sensibilidad'][1])
        # Dieta: duales 7/5 y 1/5 (resolviendo 2y1+y2=3, y1+3y2=2)
        c = redactar(sol('min', (3, 2), [R('R1', 2, 1, '>=', 8), R('R2', 1, 3, '>=', 9)]))
        self.assertIn('en 7/5', c['sensibilidad'][0])
        self.assertIn('en 1/5', c['sensibilidad'][1])

    def test_variable_en_cero_y_costo_de_forzarla(self):
        c = redactar(sol('max', (1, 2), [R('R1', 1, 1, '<=', 4)], ('mesas', 'sillas')))
        self.assertIn('mesas vale 0', c['texto_plano'])
        self.assertTrue(any('Hoy no se incluye mesas' in t for t in c['sensibilidad']))

    def test_optimos_multiples(self):
        c = redactar(sol('max', (2, 4), [R('R1', 1, 2, '<=', 8), R('R2', 1, 0, '<=', 6)]))
        self.assertTrue(c['titular'].startswith('Una de las mejores'))
        self.assertIn('no es la única solución', c['texto_plano'])

    def test_aviso_de_solucion_fraccionaria(self):
        c = redactar(sol('max', (1, 1), [R('R1', 3, 1, '<=', 10), R('R2', 1, 3, '<=', 10)], ('autos', 'motos')))
        self.assertTrue(any('fraccionarios' in t and 'autos y motos' in t for t in c['cuidados']))

    def test_no_acotado(self):
        c = redactar(sol('max', (1, 1), [R('R1', 1, -1, '<=', 3), R('R2', 1, 0, '>=', 1)], ('a', 'b')))
        self.assertEqual(c['estado'], 'no_acotado')
        self.assertIn('no tiene un máximo finito', c['titular'])
        self.assertIn('aumentando b', c['texto_plano'])

    def test_infactible_identifica_el_choque(self):
        c = redactar(sol('max', (1, 1), [R('R1', 1, 1, '<=', 4, 'cupo'), R('R2', 1, 0, '<=', 9), R('R3', 1, 1, '>=', 6, 'pedido mínimo')]))
        self.assertEqual(c['estado'], 'infactible')
        self.assertEqual(c['conflicto'], ['R1', 'R3'])
        self.assertIn('R1 (cupo) exige X1 + X2 ≤ 4', c['texto_plano'])

    def test_infactible_por_una_sola_restriccion(self):
        c = redactar(sol('max', (1, 1), [R('R1', 1, 1, '<=', -2), R('R2', 1, 0, '<=', 5)]))
        self.assertEqual(c['conflicto'], ['R1'])
        self.assertIn('ni siquiera por sí sola', c['texto_plano'])

    def test_nunca_falla_con_problemas_aleatorios(self):
        import random
        azar = random.Random(3)
        vistos = set()
        for _ in range(400):
            rs = [R(f'R{i + 1}', azar.randint(-4, 6), azar.randint(-4, 6), azar.choice(['<=', '>=', '=']),
                    azar.randint(-5, 20), azar.choice(['', 'recurso']))
                  for i in range(azar.randint(1, 5))]
            s = sol(azar.choice(['max', 'min']), (azar.randint(-5, 5), azar.randint(-5, 5)), rs,
                    azar.choice([('', ''), ('mesas', 'sillas')]), azar.choice(['', 'el costo']), azar.randint(-2, 2))
            c = redactar(s)
            vistos.add(c['estado'])
            self.assertTrue(c['titular'] and c['parrafos'] and c['texto_plano'])
        self.assertEqual(vistos, {'optimo', 'infactible', 'no_acotado'})


if __name__ == '__main__':
    unittest.main()


class PaginaTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        self.c = app.test_client()

    def datos(self, **extra):
        d = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'nombre_x1': 'puertas', 'nombre_x2': 'ventanas',
             'objetivo_nombre': 'la ganancia total',
             'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'], 'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18'],
             'r_n[]': ['Planta 1', 'Planta 2', 'Planta 3']}
        d.update(extra)
        return d

    def test_la_conclusion_aparece_con_los_nombres(self):
        html = self.c.post('/metodo_grafico/', data=self.datos()).get_data(as_text=True)
        self.assertIn('La mejor decisión: 2 puertas y 6 ventanas', html)
        self.assertIn('class="decision-card', html)
        self.assertIn('Planta 2', html)
        self.assertIn('Se agota por completo', html)
        self.assertIn('¿Y si los límites cambian?', html)
        self.assertIn('id="btn-copiar"', html)
        self.assertEqual(html.count('class="recurso '), 3)

    def test_html_del_usuario_se_escapa_en_nombres_y_rotulos(self):
        html = self.c.post('/metodo_grafico/', data=self.datos(nombre_x1='<img src=x onerror=1>',
                                                               **{'r_n[]': ['<b>x</b>', '', '']})).get_data(as_text=True)
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('<b>x</b>', html)

    def test_formulario_conserva_nombres_y_rotulos(self):
        html = self.c.post('/metodo_grafico/', data=self.datos(z_x='abc')).get_data(as_text=True)
        self.assertIn('value="puertas"', html)
        self.assertIn('value="la ganancia total"', html)
        self.assertIn('value="Planta 3"', html)


class ConclusionAmpliadaTests(unittest.TestCase):
    def test_respuesta_final_formal(self):
        c = redactar(sol('max', (3, 5), PRODUCCION, ('puertas', 'ventanas'), 'la ganancia total'))
        self.assertEqual(c['respuesta_final'],
                         'Se concluye que, para maximizar la ganancia total, se debe elegir 2 puertas y 6 ventanas, '
                         'con lo que el valor máximo de la ganancia total es Z = 36.')
        self.assertIn('donde se cruzan R2 (horas de la planta 2) y R3', c['parrafos'][0])

    def test_comparacion_de_vertices(self):
        c = redactar(sol('max', (3, 5), PRODUCCION))
        self.assertEqual([f['z'] for f in c['comparacion']], ['36', '30', '27', '12', '0'])
        self.assertTrue(c['comparacion'][0]['optimo'])
        self.assertEqual(c['comparacion'][0]['ancho'], 100.0)
        self.assertIn('ninguno supera 36', c['frase_comparacion'])
        c = redactar(sol('min', (3, 2), [R('R1', 2, 1, '>=', 8), R('R2', 1, 3, '>=', 9)]))
        self.assertEqual([f['z'] for f in c['comparacion']], ['13', '16', '27'])
        self.assertIn('ninguno baja de 13', c['frase_comparacion'])

    def test_recomendacion_prioriza_el_mayor_precio_sombra(self):
        c = redactar(sol('max', (3, 5), PRODUCCION))
        r = c['recomendaciones']
        self.assertIn('ampliar el límite de R2', r[0])
        self.assertIn('3/2', r[0])
        self.assertTrue(any('R3' in t and 'aunque menos' in t for t in r))
        self.assertTrue(any('No tiene sentido invertir en R1' in t for t in r))

    def test_recomendacion_en_minimizacion_con_minimos(self):
        c = redactar(sol('min', (3, 2), [R('R1', 2, 1, '>=', 8), R('R2', 1, 3, '>=', 9)]))
        self.assertIn('reducir el mínimo exigido en R1', c['recomendaciones'][0])

    def test_comprobacion(self):
        c = redactar(sol('max', (3, 5), PRODUCCION))
        self.assertIn('el punto (2, 6) cumple todas las restricciones', c['verificacion'])
        self.assertIn('R2 (horas de la planta 2): 12 ≤ 12 ✔', c['verificacion'])

    def test_los_tres_estados_traen_respuesta_final(self):
        for s in (sol('max', (1, 1), [R('R1', 1, -1, '<=', 3), R('R2', 1, 0, '>=', 1)]),
                  sol('max', (1, 1), [R('R1', 1, 1, '<=', 4), R('R2', 1, 1, '>=', 6)])):
            c = redactar(s)
            self.assertTrue(c['respuesta_final'].startswith('Se concluye que'))
            self.assertTrue(c['recomendaciones'])

    def test_pagina_sin_chips_de_ejemplos_pero_con_la_conclusion_nueva(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        c = app.test_client()
        self.assertNotIn('class="chip" data-ejemplo', c.get('/metodo_grafico/').get_data(as_text=True))
        d = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'],
             'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18']}
        html = c.post('/metodo_grafico/', data=d).get_data(as_text=True)
        for texto in ('class="concl-respuesta"', '¿Por qué este y no otro?', 'class="cmp-fila es-optimo"',
                      'class="concl-caja recom"', 'class="verificacion"'):
            self.assertIn(texto, html)
