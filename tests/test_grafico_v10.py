"""Pruebas de las mejoras del Método Gráfico (v10)."""
import json
import os
import re
import sys
import unittest
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.datastructures import MultiDict

from app import app
from blueprints.grafico_conclusion import redactar
from blueprints.grafico_extractor import extraer
from blueprints.grafico_plot import _marca, graficar
from blueprints.grafico_solver import leer_problema, resolver


def resolver_form(tipo, z, filas):
    form = MultiDict([('tipo_opt', tipo), ('z_x', z[0]), ('z_y', z[1])])
    for x, y, op, c in filas:
        form.add('r_x[]', x), form.add('r_y[]', y), form.add('r_op[]', op), form.add('r_c[]', c)
    return resolver(leer_problema(form))


class SensibilidadConIgualdadTests(unittest.TestCase):
    """Con una restricción «=», la recomendación debe seguir el signo del precio sombra."""

    def test_maximizar_con_igualdad_recomienda_subir_el_valor(self):
        # máx 3x + 2y, x + y = 4, x ≤ 3 → óptimo (3, 1); λ(R1) = 2 > 0: subir el 4 mejora Z
        c = redactar(resolver_form('max', ('3', '2'), [('1', '1', '=', '4'), ('1', '0', '<=', '3')]))
        texto = ' '.join(c['recomendaciones'])
        self.assertIn('subir el valor exigido en R1', texto)
        self.assertNotIn('mínimo exigido en R1', texto)
        self.assertTrue(any('el valor exigido en R1 aumentara' in t for t in c['sensibilidad']))

    def test_minimizar_con_igualdad_recomienda_bajar_el_valor(self):
        # mín 4x + 3y, x + y = 10, x ≥ 2, y ≤ 6 → óptimo (4, 6); bajar el 10 abarata
        c = redactar(resolver_form('min', ('4', '3'), [('1', '1', '=', '10'), ('1', '0', '>=', '2'), ('0', '1', '<=', '6')]))
        self.assertIn('bajar el valor exigido en R1', ' '.join(c['recomendaciones']))

    def test_desigualdades_siguen_igual(self):
        c = redactar(resolver_form('max', ('3', '5'), [('1', '0', '<=', '4'), ('0', '2', '<=', '12'), ('3', '2', '<=', '18')]))
        self.assertIn('ampliar el límite de R2', c['recomendaciones'][0])
        c = redactar(resolver_form('min', ('3', '2'), [('2', '1', '>=', '8'), ('1', '3', '>=', '9')]))
        self.assertIn('reducir el mínimo exigido', c['recomendaciones'][0])


class MarcasDeEjeTests(unittest.TestCase):
    def test_sin_errores_de_redondeo(self):
        self.assertEqual([_marca(k * 0.025) for k in range(5)], ['0', '0.025', '0.05', '0.075', '0.1'])
        self.assertEqual(_marca(3 * 0.1), '0.3')

    def test_numeros_grandes_compactos(self):
        self.assertEqual(_marca(2_500_000), '2.5M')
        self.assertEqual(_marca(500_000), '500k')
        self.assertEqual(_marca(25_000), '25000')


class ExtractorSinPuntosTests(unittest.TestCase):
    def test_st_sin_puntos(self):
        r = extraer('max 3a+2b st a+b<=4, a+3b<=6')
        self.assertEqual(r['tipo'], 'max')
        self.assertEqual([f['texto'] for f in r['restricciones']], ['X1 + X2 ≤ 4', 'X1 + 3X2 ≤ 6'])

    def test_palabras_con_st_no_se_confunden(self):
        r = extraer('Maximizar Z = 3x + 2y\nsujeto a: x + y <= 4\nestas son las horas: x <= 3')
        self.assertEqual(len(r['restricciones']), 2)


class GeometriaParaElExploradorTests(unittest.TestCase):
    def test_cada_grafica_trae_datos_validos(self):
        sol = resolver_form('max', ('3', '5'), [('1', '0', '<=', '4'), ('0', '2', '<=', '12'), ('3', '2', '<=', '18')])
        for etapa in ('rectas', 'semiplanos', 'region', 'vertices', 'optimo'):
            svg = str(graficar(sol, etapa))
            geo = json.loads(unescape(re.search(r'data-geo="([^"]*)"', svg).group(1)))
            self.assertEqual(geo['etapa'], etapa)
            self.assertEqual(len(geo['rectas']), 3)
            self.assertGreater(geo['X'], 4)
        geo = json.loads(unescape(re.search(r'data-geo="([^"]*)"', str(graficar(sol, 'optimo'))).group(1)))
        self.assertIn([2.0, 6.0, '2', '6', '36', True], geo['vertices'])
        mini = str(graficar(sol, 'semiplano', solo=1))
        geo = json.loads(unescape(re.search(r'data-geo="([^"]*)"', mini).group(1)))
        self.assertEqual([r[4] for r in geo['rectas']], ['R2'])

    def test_titulo_x2_no_choca_con_las_marcas(self):
        svg = str(graficar(resolver_form('max', ('70', '50'), [('4', '3', '<=', '240'), ('2', '1', '<=', '100')]), 'region'))
        y_titulo = float(re.search(r'<text class="et" x="[\d.]+" y="([\d.]+)" text-anchor="start">X2', svg).group(1))
        y_marcas = [float(y) for y in re.findall(r'<text class="my" x="[\d.]+" y="([\d.]+)"', svg)]
        self.assertLess(y_titulo, min(y_marcas) - 10)


class EnlaceCompartidoTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.c = app.test_client()

    def test_get_con_datos_abre_el_ejercicio_resuelto(self):
        q = ('tipo_opt=max&z_x=3&z_y=5&r_x[]=1&r_y[]=0&r_op[]=%3C%3D&r_c[]=4&r_n[]='
             '&r_x[]=0&r_y[]=2&r_op[]=%3C%3D&r_c[]=12&r_n[]=&r_x[]=3&r_y[]=2&r_op[]=%3C%3D&r_c[]=18&r_n[]=')
        html = self.c.get('/metodo_grafico/?' + q).get_data(as_text=True)
        self.assertIn('class="resumen estado-optimo', html)
        self.assertIn('data-contar="36"', html)
        self.assertIn('id="btn-enlace"', html)

    def test_get_con_datos_invalidos_muestra_el_error(self):
        html = self.c.get('/metodo_grafico/?tipo_opt=max&z_x=abc&z_y=1&r_x[]=1&r_y[]=1&r_op[]=%3C%3D&r_c[]=4').get_data(as_text=True)
        self.assertIn('class="alerta"', html)
        self.assertNotIn('class="resumen', html)

    def test_get_sin_datos_es_la_pagina_en_blanco(self):
        html = self.c.get('/metodo_grafico/?nuevo=1').get_data(as_text=True)
        self.assertNotIn('class="resumen', html)


if __name__ == '__main__':
    unittest.main()
