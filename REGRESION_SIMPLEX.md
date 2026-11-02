# Módulo: regresión lineal con Simplex

Se integra en la aplicación Flask del curso mediante `blueprints/regresion_bp.py`. La página está en `/regresion_simplex/` y el endpoint JSON en `POST /regresion_simplex/api/regression`.

El módulo acepta de 3 a 12 puntos `{x, y}` y minimiza el mayor error vertical `E` de `y = ax + b` mediante un Simplex de dos fases con tablas visibles. El solucionador propio está en `blueprints/regresion_solver.py`; no sustituye el método con una llamada a SciPy. La primera fase encuentra una base factible y la segunda optimiza `E`. El resultado incluye pendiente, intercepto, error máximo, predicciones y tablas de cada iteración.

La interfaz usa `templates/regresion/index.html`, `static/css/regresion.css` y `static/js/regresion.js`. La página principal enlaza el módulo. Las animaciones respetan `prefers-reduced-motion`; el botón de la barra superior cambia entre tema oscuro y claro.

Para probar: `python -m unittest discover -s tests -p test_regresion_simplex.py`. El caso `(0,0), (1,0), (2,2)` debe dar `y = x - 0.5` y `E = 0.5`. El endpoint devuelve HTTP 400 ante datos inválidos.

Solo se usa Flask, ya presente en los requisitos del repositorio. Este módulo no controla el plotter ni genera G-code.
