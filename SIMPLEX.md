# Módulo: Simplex normal

Se integra en la aplicación Flask del curso mediante `blueprints/simplex_bp.py`. La página está en `/metodo_simplex/` y el endpoint JSON en `POST /metodo_simplex/api/simplex`.

Resuelve `max/min Z = c·x` sujeto a `A·x ≤ b`, `x ≥ 0`, con `b ≥ 0`, usando el Simplex de tabla con variables de holgura. **No usa variables artificiales**: las restricciones `≥` o `=` y los lados derechos negativos pertenecen al Simplex de dos fases (otro módulo), y aquí se rechazan con HTTP 400 y un mensaje claro. Para minimizar se maximiza `−Z`.

- `blueprints/simplex_solver.py`: validación, algoritmo (aritmética exacta con `Fraction`, regla de Dantzig y Bland como respaldo anti-ciclos), detección de no acotado, óptimos múltiples y degeneración, y análisis de sensibilidad (precios sombra, rangos de `b` y de `c`, costos reducidos). No usa SciPy.
- `blueprints/simplex_interpretacion.py`: redacta la interpretación a partir del contexto escrito por el usuario, las unidades y la sensibilidad. Funciona sin conexión.
- Interfaz: `templates/simplex/index.html`, `static/css/simplex.css`, `static/js/simplex.js`, con el mismo estilo del módulo de regresión (tema oscuro/claro).

El endpoint recibe `{sentido, unidad_z, contexto, variables:[{nombre, unidad, costo}], restricciones:[{nombre, unidad, coefs, tipo:"<=", rhs}]}` y devuelve estado, `z`, `x`, holguras, sensibilidad, `interpretacion` y `iterations` (tablas con la misma forma que las del módulo de regresión: `label`, `columns`, `basis`, `rows`, `pivot`). Un problema no acotado responde 200 con `estado: "no_acotado"`.

Para probar: `python -m unittest discover -s tests -p test_simplex.py`. El caso `max 3x+5y; x≤4, 2y≤12, 3x+2y≤18` da `Z = 36` en `(2, 6)`. La prueba aleatoria contra SciPy se omite sola si SciPy no está instalado.
