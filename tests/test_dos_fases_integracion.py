"""Prueba de integración con el app.py REAL del proyecto (la ejecuta el compañero).

Se omite mientras el Blueprint no esté registrado en app.py; después de aplicar
INTEGRACION.md debe pasar sin cambios. Sigue el estilo de tests/test_regresion_simplex.py.
"""
import unittest

try:
    from app import app
except ImportError:  # carpeta independiente: no existe app.py del proyecto
    app = None


@unittest.skipUnless(app is not None and "dos_fases_bp" in app.blueprints,
                     "dos_fases_bp aún no está registrado en el app.py del proyecto")
class DosFasesIntegracionTests(unittest.TestCase):
    def test_vista_principal_y_menu(self):
        client = app.test_client()
        self.assertEqual(client.get("/metodo_dos_fases/").status_code, 200)
        menu = client.get("/").data.decode()
        self.assertIn("/metodo_dos_fases/", menu)

    def test_calculo_y_error(self):
        client = app.test_client()
        modelo = {"sense": "max", "objective": ["5", "8"], "constraints": [
            {"coefficients": ["2", "1"], "operator": "=", "rhs": "12"},
            {"coefficients": ["1", "1"], "operator": ">=", "rhs": "8"},
            {"coefficients": ["0", "1"], "operator": "<=", "rhs": "8"}]}
        respuesta = client.post("/metodo_dos_fases/api/resolver", json=modelo)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json["objective_value"], "74")
        self.assertEqual(client.post("/metodo_dos_fases/api/resolver", json={"objective": [1], "constraints": []}).status_code, 400)

    def test_otros_modulos_siguen_respondiendo(self):
        client = app.test_client()
        rutas = [r.rule for r in app.url_map.iter_rules() if r.rule.endswith("/") and "<" not in r.rule
                 and r.endpoint.endswith("vista_principal") and not r.endpoint.startswith("dos_fases_bp")]
        for ruta in ["/"] + rutas:  # menú y vista principal de cada módulo existente
            respuesta = client.get(ruta)
            self.assertEqual(respuesta.status_code, 200, ruta)
            self.assertNotIn("dos_fases.css", respuesta.data.decode(), ruta)  # los estilos del módulo no se filtran


if __name__ == "__main__":
    unittest.main()
