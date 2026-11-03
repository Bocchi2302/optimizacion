import unittest

from app import app
from blueprints.regresion_solver import regress


class RegresionSimplexTests(unittest.TestCase):
    def test_known_minimax_solution(self):
        result = regress([{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 2}])
        self.assertAlmostEqual(result["slope"], 1)
        self.assertAlmostEqual(result["intercept"], -0.5)
        self.assertAlmostEqual(result["max_error"], 0.5)
        self.assertEqual({step["phase"] for step in result["iterations"]}, {"I", "II"})

    def test_blueprint_and_error_response(self):
        client = app.test_client()
        self.assertEqual(client.get("/regresion_simplex/").status_code, 200)
        self.assertEqual(client.post("/regresion_simplex/api/regression", json={"points": []}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
