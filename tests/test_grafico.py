import os
import re
import sys
import unittest
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.datastructures import MultiDict

from blueprints.grafico_solver import EntradaInvalida, fmt, leer_problema, parse_numero, resolver


def resolver_form(tipo, z, filas):
    form = MultiDict([('tipo_opt', tipo), ('z_x', z[0]), ('z_y', z[1])])
    for x, y, op, c in filas:
        form.add('r_x[]', x), form.add('r_y[]', y), form.add('r_op[]', op), form.add('r_c[]', c)
    return resolver(leer_problema(form))


class MetodoGraficoTests(unittest.TestCase):
    def test_produccion_maximiza(self):
        s = resolver_form('max', ('3', '5'), [('1', '0', '<=', '4'), ('0', '2', '<=', '12'), ('3', '2', '<=', '18')])
        self.assertEqual(s['estado'], 'optimo')
        o = s['optimos'][0]
        self.assertEqual((o['x'], o['y'], o['z']), (2, 6, 36))
        self.assertTrue(s['acotada'])
        self.assertEqual(len(s['vertices']), 5)

    def test_dieta_minimiza_region_no_acotada(self):
        s = resolver_form('min', ('3', '2'), [('2', '1', '>=', '8'), ('1', '3', '>=', '9')])
        self.assertEqual(s['estado'], 'optimo')
        self.assertFalse(s['acotada'])
        o = s['optimos'][0]
        self.assertEqual((o['x'], o['y'], o['z']), (3, 2, 13))

    def test_maximizar_en_region_no_acotada_es_ilimitado(self):
        s = resolver_form('max', ('3', '2'), [('2', '1', '>=', '8'), ('1', '3', '>=', '9')])
        self.assertEqual(s['estado'], 'no_acotado')

    def test_ilimitado(self):
        s = resolver_form('max', ('1', '1'), [('1', '-1', '<=', '3'), ('1', '0', '>=', '1')])
        self.assertEqual(s['estado'], 'no_acotado')

    def test_ilimitado_pero_minimo_existe(self):
        s = resolver_form('min', ('1', '1'), [('1', '-1', '<=', '3'), ('1', '0', '>=', '1')])
        self.assertEqual(s['estado'], 'optimo')
        self.assertEqual(s['optimos'][0]['z'], 1)

    def test_infactible(self):
        s = resolver_form('max', ('1', '1'), [('1', '1', '<=', '4'), ('1', '1', '>=', '6')])
        self.assertEqual(s['estado'], 'infactible')
        self.assertFalse(s['factible'])

    def test_restriccion_trivial_falsa(self):
        s = resolver_form('max', ('1', '1'), [('0', '0', '>=', '5'), ('1', '1', '<=', '4')])
        self.assertEqual(s['estado'], 'infactible')

    def test_optimos_multiples(self):
        s = resolver_form('max', ('2', '4'), [('1', '2', '<=', '8'), ('1', '0', '<=', '6')])
        self.assertEqual(s['estado'], 'optimo')
        self.assertTrue(s['multiples'])
        self.assertEqual({(o['x'], o['y']) for o in s['optimos']}, {(0, 4), (6, 1)})
        self.assertTrue(all(o['z'] == 16 for o in s['optimos']))

    def test_optimo_en_rayo_con_z_constante(self):
        s = resolver_form('min', ('0', '1'), [('1', '0', '>=', '2')])
        self.assertEqual(s['estado'], 'optimo')
        self.assertTrue(s['multiples'])

    def test_igualdad(self):
        s = resolver_form('max', ('1', '2'), [('1', '1', '=', '4'), ('1', '0', '<=', '3')])
        self.assertEqual(s['estado'], 'optimo')
        o = s['optimos'][0]
        self.assertEqual((o['x'], o['y'], o['z']), (0, 4, 8))

    def test_exactitud_con_fracciones(self):
        s = resolver_form('max', ('1', '1'), [('3', '1', '<=', '10'), ('1', '3', '<=', '10')])
        o = s['optimos'][0]
        self.assertEqual((o['x'], o['y']), (F(5, 2), F(5, 2)))

    def test_vertice_degenerado_no_se_duplica(self):
        s = resolver_form('max', ('1', '1'), [('1', '0', '<=', '2'), ('0', '1', '<=', '2'), ('1', '1', '<=', '4')])
        puntos = [(e['x'], e['y']) for e in s['vertices']]
        self.assertEqual(len(puntos), len(set(puntos)))
        self.assertEqual(s['optimos'][0]['z'], 4)

    def test_origen_unico_punto(self):
        s = resolver_form('max', ('1', '1'), [('1', '1', '<=', '0')])
        self.assertEqual(s['estado'], 'optimo')
        self.assertEqual(len(s['vertices']), 1)

    def test_validacion(self):
        for malo in ('abc', '', '1e999', 'nan', 'inf', '1/0', '99999999999'):
            with self.assertRaises(EntradaInvalida, msg=malo):
                parse_numero(malo, 'campo')
        self.assertEqual(parse_numero('2,5', 'c'), F(5, 2))
        self.assertEqual(parse_numero('-3/4', 'c'), F(-3, 4))

    def test_formato(self):
        self.assertEqual(fmt(F(7, 3)), '2.3333')
        self.assertEqual(fmt(F(4, 1)), '4')
        self.assertEqual(fmt(F(-1, 100000)), '0')


class RutaTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        self.c = app.test_client()

    def datos(self, **extra):
        d = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'contexto': '<b>x</b>',
             'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'],
             'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18']}
        d.update(extra)
        return d

    def test_get(self):
        r = self.c.get('/metodo_grafico/')
        self.assertEqual(r.status_code, 200)

    def test_post_ok_muestra_pasos_y_escapa_html(self):
        r = self.c.post('/metodo_grafico/', data=self.datos())
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('<svg', html)
        self.assertIn('Z = 36', html)
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)
        self.assertNotIn('<b>x</b>', html)
        for pid in ('planteamiento', 'rectas', 'semiplanos', 'region', 'vertices', 'evaluacion', 'optimo', 'respuesta'):
            self.assertIn(f'id="paso-{pid}"', html)

    def test_post_error_conserva_valores(self):
        r = self.c.post('/metodo_grafico/', data=self.datos(z_x='abc'))
        html = r.get_data(as_text=True)
        self.assertIn('no es un número válido', html)
        self.assertIn('value="abc"', html)

    def test_post_casos_especiales(self):
        inf = self.c.post('/metodo_grafico/', data=self.datos(**{'r_op[]': ['<=', '>=', '<='], 'r_c[]': ['4', '20', '18']})).get_data(as_text=True)
        self.assertIn('No existe región factible', inf)
        ilim = self.c.post('/metodo_grafico/', data={
            'tipo_opt': 'max', 'z_x': '1', 'z_y': '1', 'r_x[]': ['1', '1'], 'r_y[]': ['-1', '0'],
            'r_op[]': ['<=', '>='], 'r_c[]': ['3', '1']}).get_data(as_text=True)
        self.assertIn('Z no tiene límite', ilim)

    def test_cantidad_de_restricciones_limitada(self):
        n = 13
        r = self.c.post('/metodo_grafico/', data={
            'tipo_opt': 'max', 'z_x': '1', 'z_y': '1', 'r_x[]': ['1'] * n, 'r_y[]': ['1'] * n,
            'r_op[]': ['<='] * n, 'r_c[]': ['5'] * n})
        self.assertIn('máximo es 12', r.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()


class RobustezTests(unittest.TestCase):
    """Problemas aleatorios: nada debe romperse y todo SVG debe ser XML válido."""

    def test_graficas_y_pagina_con_problemas_aleatorios(self):
        import random
        import xml.etree.ElementTree as ET
        from flask import Flask
        from blueprints.grafico_bp import _contexto_resultado, grafico_bp
        from blueprints.grafico_solver import Restriccion

        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        azar = random.Random(11)
        estados = set()
        for _ in range(250):
            rs = [Restriccion(f'R{i + 1}', F(azar.randint(-4, 6)), F(azar.randint(-4, 6)),
                              azar.choice(['<=', '>=', '<=', '=']), F(azar.randint(-5, 20)))
                  for i in range(azar.randint(1, 5))]
            sol = resolver({'tipo': azar.choice(['max', 'min']), 'zx': F(azar.randint(-5, 5)), 'zy': F(azar.randint(-5, 5)),
                            'zk': F(azar.randint(-3, 3)), 'nombres': ['', ''], 'contexto': '', 'restricciones': rs})
            estados.add(sol['estado'])
            with app.test_request_context():
                ctx = _contexto_resultado(sol)
            for fig in list(ctx['figuras'].values()) + [i['figura'] for i in ctx['info_rectas']]:
                ET.fromstring(str(fig))          # XML bien formado
        self.assertEqual(estados, {'optimo', 'infactible', 'no_acotado'})

    def test_rango_de_z_para_la_recta_interactiva(self):
        s = resolver_form('max', ('3', '5'), [('1', '0', '<=', '4'), ('0', '2', '<=', '12'), ('3', '2', '<=', '18')])
        self.assertEqual((s['z_lo'], s['z_hi']), (0, 36))
        s = resolver_form('min', ('3', '2'), [('2', '1', '>=', '8'), ('1', '3', '>=', '9')])
        self.assertEqual((s['z_lo'], s['z_hi']), (13, None))       # sin tope por arriba
        s = resolver_form('max', ('1', '1'), [('1', '1', '<=', '4'), ('1', '1', '>=', '6')])
        self.assertEqual((s['z_lo'], s['z_hi']), (None, None))

    def test_pagina_enlaza_colores_y_mapas(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        d = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'],
             'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18']}
        html = app.test_client().post('/metodo_grafico/', data=d).get_data(as_text=True)
        self.assertEqual(html.count('class="semi-card"'), 3)        # un mapa por restricción
        self.assertIn('data-leyenda', html)
        self.assertIn('data-r="R2"', html)
        self.assertIn('data-p="2,6"', html)
        self.assertIn('data-z-control', html)
        self.assertIn('id="iso-movil"', html)


class NuevoEjercicioTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        self.c = app.test_client()

    def test_no_hay_ejemplos_ni_cinta(self):
        html = self.c.get('/metodo_grafico/').get_data(as_text=True)
        for rastro in ('cinta', 'data-ejemplo', 'Empieza con un ejemplo', 'datos-ejemplos'):
            self.assertNotIn(rastro, html)

    def test_otro_ejercicio_lleva_a_la_pagina_en_blanco(self):
        d = {'tipo_opt': 'max', 'z_x': '1', 'z_y': '1', 'contexto': 'viejo', 'r_x[]': ['1'], 'r_y[]': ['1'],
             'r_op[]': ['<='], 'r_c[]': ['4']}
        html = self.c.post('/metodo_grafico/', data=d).get_data(as_text=True)
        self.assertIn('id="btn-otro" href="/metodo_grafico/?nuevo=1"', html)
        vacio = self.c.get('/metodo_grafico/').get_data(as_text=True)
        self.assertNotIn('viejo', vacio)
        self.assertNotIn('class="resumen', vacio)


class TemaTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        app = Flask(__name__, root_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        self.c = app.test_client()
        self.css = open(os.path.join(app.root_path, 'static', 'css', 'grafico.css'), encoding='utf8').read()

    def test_pagina_con_boton_de_tema_y_script_anti_parpadeo(self):
        html = self.c.get('/metodo_grafico/').get_data(as_text=True)
        self.assertIn('id="btn-tema"', html)
        self.assertIn("localStorage.getItem('tema-optilab')", html)
        self.assertIn('prefers-color-scheme: dark', html)
        self.assertLess(html.index("dataset.tema = t"), html.index('<link rel="stylesheet"'))   # se aplica antes de cargar el CSS

    def test_las_graficas_usan_variables_css_y_no_colores_fijos(self):
        d = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'],
             'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18']}
        html = self.c.post('/metodo_grafico/', data=d).get_data(as_text=True)
        svg = ''.join(re.findall(r'<svg class="grafica-svg.*?</svg>', html, re.S))
        self.assertIn('var(--r0)', svg)
        self.assertIn('var(--tinta)', svg)
        self.assertEqual(re.findall(r'(?:stroke|fill)="#[0-9a-fA-F]{3,6}"', svg), [])

    def test_modo_oscuro_define_todos_los_tokens_del_claro(self):
        def tokens(bloque):
            return set(re.findall(r'(--[a-z0-9-]+):', bloque))
        claro = re.search(r':root \{(.*?)\n\}', self.css, re.S).group(1)
        oscuro = re.search(r":root\[data-tema='oscuro'\] \{(.*?)\n\}", self.css, re.S).group(1)
        # los tokens que cambian de color deben existir en ambos modos
        sin_cambio = {'--radio', '--fuente-t', '--fuente', '--linea', '--linea-fuerte'}   # las líneas se derivan de --tinta-rgb
        faltan = {t for t in tokens(claro) - tokens(oscuro) - sin_cambio}
        self.assertEqual(faltan, set())

    def test_sin_colores_de_texto_fijos_que_rompan_el_oscuro(self):
        fuera_de_tokens = self.css.split("* { box-sizing", 1)[1]
        for rastro in ('color: #2c2c44', 'color: #23233b', 'background: #fff;'):    # (el logo institucional sí lleva fondo blanco fijo)
            self.assertNotIn(rastro, fuera_de_tokens)


class IdentidadYRendimientoTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from blueprints.grafico_bp import grafico_bp
        self.raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app = Flask(__name__, root_path=self.raiz)
        app.register_blueprint(grafico_bp, url_prefix='/metodo_grafico')
        app.add_url_rule('/', 'index', lambda: 'inicio')
        self.c = app.test_client()
        self.datos = {'tipo_opt': 'max', 'z_x': '3', 'z_y': '5', 'r_x[]': ['1', '0', '3'], 'r_y[]': ['0', '2', '2'],
                      'r_op[]': ['<=', '<=', '<='], 'r_c[]': ['4', '12', '18']}

    def test_logo_de_la_universidad_en_cabecera_hero_y_pie(self):
        html = self.c.get('/metodo_grafico/').get_data(as_text=True)
        for archivo in ('usta-logo.webp', 'usta-emblema.webp', 'usta-favicon.png'):
            self.assertTrue(os.path.exists(os.path.join(self.raiz, 'static', 'img', archivo)), archivo)
            self.assertIn(archivo, html)
        self.assertIn('class="marca-emblema"', html)
        self.assertIn('class="usta-tile"', html)
        self.assertIn('class="pie"', html)
        self.assertEqual(html.count('alt="Universidad Santo Tomás · Villavicencio"'), 2)    # hero + pie

    def test_escena_animada_del_estado_vacio(self):
        html = self.c.get('/metodo_grafico/').get_data(as_text=True)
        for clase in ('data-escena', 've-l1', 've-l2', 've-l3', 've-region', 've-iso', 've-opt'):
            self.assertIn(clase, html)

    def test_ids_unicos_en_toda_la_pagina(self):
        html = self.c.post('/metodo_grafico/', data=self.datos).get_data(as_text=True)
        ids = re.findall(r'\sid="([^"]+)"', html)
        repetidos = {i for i in ids if ids.count(i) > 1}
        self.assertEqual(repetidos, set())

    def test_accesibilidad_basica(self):
        html = self.c.post('/metodo_grafico/', data=self.datos).get_data(as_text=True)
        self.assertIn('aria-label="Enunciado del ejercicio"', html)
        self.assertIn('<h2 class="sr">Resultado y procedimiento paso a paso</h2>', html)
        self.assertEqual(len(re.findall(r'<img(?![^>]*\balt=)', html)), 0)

    def test_respuestas_comprimidas_con_gzip(self):
        import gzip
        sin = self.c.post('/metodo_grafico/', data=self.datos)
        con = self.c.post('/metodo_grafico/', data=self.datos, headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(con.headers['Content-Encoding'], 'gzip')
        self.assertIn('Accept-Encoding', con.headers['Vary'])
        self.assertLess(len(con.data), len(sin.data) / 4)
        self.assertEqual(gzip.decompress(con.data), sin.data)
        self.assertNotIn('Content-Encoding', sin.headers)
        # una respuesta pequeña (error JSON) no se comprime
        chica = self.c.post('/metodo_grafico/extraer', json={'texto': ''}, headers={'Accept-Encoding': 'gzip'})
        self.assertNotIn('Content-Encoding', chica.headers)

    def test_sin_efectos_costosos_en_el_scroll(self):
        css = open(os.path.join(self.raiz, 'static', 'css', 'grafico.css'), encoding='utf8').read()
        fondo = css[css.index('.fondo-vivo {'):css.index('/* Barra de progreso de lectura */')]
        self.assertNotIn('animation', fondo)          # fondo estático
        self.assertNotIn('mask', fondo)
        self.assertNotIn('filter', fondo)
        self.assertEqual(len(re.findall(r'(?<!none) backdrop-filter: blur', css)), 0)

    def test_marca_usta_en_los_tokens(self):
        css = open(os.path.join(self.raiz, 'static', 'css', 'grafico.css'), encoding='utf8').read()
        self.assertIn('--acento: #004387', css)         # azul institucional
        self.assertIn('--dorado: #ffcc00', css)         # oro institucional
        self.assertIn('--papel: #1b1b1f', css)          # grafito neutro del modo oscuro
