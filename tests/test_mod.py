import unittest

from app import app
from blueprints.mod_bp import calcular_mod


class ModTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_ejemplos_y_signos(self):
        for a, b, q, r in [(10, 3, 3, 1), (20, 5, 4, 0), (0, 3, 0, 0),
                           (2, 5, 0, 2), (-10, 3, -4, 2), (10, -3, -3, 1),
                           (-10, -3, 4, 2), (17, 2, 8, 1)]:
            with self.subTest(a=a, b=b):
                result = calcular_mod(a, b)
                self.assertEqual((result['cociente'], result['residuo']), (str(q), str(r)))
                self.assertEqual(result['divisible'], r == 0)
                self.assertEqual(result['par'], a % 2 == 0)

    def test_identidad_y_rango(self):
        for a in range(-40, 41):
            for b in range(-12, 13):
                if b == 0:
                    continue
                result = calcular_mod(a, b)
                q, r = int(result['cociente']), int(result['residuo'])
                self.assertEqual(a, b * q + r)
                self.assertTrue(0 <= r < abs(b))

    def test_precision_enteros_grandes(self):
        a = '9' * 200
        response = self.client.post('/metodo_mod/calcular', json={'dividendo': a, 'divisor': '7'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['dividendo'], a)
        self.assertEqual(int(a), 7 * int(data['cociente']) + int(data['residuo']))

    def test_entradas_invalidas(self):
        for a, b in [('10', '0'), ('1.5', '3'), ('1e3', '2'), ('', '2'),
                     (True, 2), (1.0, 2), (None, 2), ('9' * 201, 2),
                     ('10', '٢'), ([], 2), ('10', '--2')]:
            with self.subTest(a=a, b=b):
                response = self.client.post('/metodo_mod/calcular', json={'dividendo': a, 'divisor': b})
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.get_json())
        for body in [[], None, 'texto', {}]:
            self.assertEqual(self.client.post('/metodo_mod/calcular', json=body).status_code, 400)
        self.assertEqual(self.client.post('/metodo_mod/calcular', data='{', content_type='application/json').status_code, 400)

    def test_paginas_y_recursos(self):
        self.assertIn(b'/metodo_mod/', self.client.get('/').data)
        self.assertEqual(self.client.get('/metodo_grafico/').status_code, 200)
        page = self.client.get('/metodo_mod/')
        self.assertEqual(page.status_code, 200)
        for resource, content_type in [('mod.css', 'text/css'), ('mod.js', 'javascript')]:
            with self.client.get('/metodo_mod/assets/' + resource) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response.content_type)


if __name__ == '__main__':
    unittest.main()
