# Módulo: Simplex normal

Se integra en la aplicación Flask del curso mediante `blueprints/simplex_bp.py`. La página está en `/metodo_simplex/` y el endpoint JSON en `POST /metodo_simplex/api/simplex`.

Resuelve `max/min Z = c·x` sujeto a `A·x ≤ b`, `x ≥ 0`, con `b ≥ 0`, usando el Simplex de tabla con variables de holgura. **No usa variables artificiales**: las restricciones `≥` o `=` y los lados derechos negativos pertenecen al Simplex de dos fases (otro módulo), y aquí se rechazan con HTTP 400 y un mensaje claro. Para minimizar se maximiza `−Z`.

- `blueprints/simplex_solver.py`: validación, algoritmo (aritmética exacta con `Fraction`, regla de Dantzig y Bland como respaldo anti-ciclos), detección de no acotado, óptimos múltiples y degeneración, y análisis de sensibilidad (precios sombra, rangos de `b` y de `c`, costos reducidos). No usa SciPy.
- `blueprints/simplex_interpretacion.py`: redacta la interpretación a partir del contexto escrito por el usuario, las unidades y la sensibilidad. Funciona sin conexión.
- Interfaz: `templates/simplex/index.html`, `static/css/simplex.css`, `static/js/simplex.js`, con el mismo estilo del módulo de regresión (tema oscuro/claro).

El endpoint recibe `{sentido, unidad_z, contexto, variables:[{nombre, unidad, costo}], restricciones:[{nombre, unidad, coefs, tipo:"<=", rhs}]}` y devuelve estado, `z`, `x`, holguras, sensibilidad, `interpretacion` y `iterations` (tablas con la misma forma que las del módulo de regresión: `label`, `columns`, `basis`, `rows`, `pivot`). Un problema no acotado responde 200 con `estado: "no_acotado"`.

Para probar: `python -m unittest discover -s tests -p test_simplex.py`. El caso `max 3x+5y; x≤4, 2y≤12, 3x+2y≤18` da `Z = 36` en `(2, 6)`. La prueba aleatoria contra SciPy se omite sola si SciPy no está instalado.

## Funciones de la interfaz

- **Explicación de cada iteración** (`iterations[k].explicacion` y `ratios`): por qué entra y sale cada variable, con la columna de razones `LD ÷ col.`.
- **Ejemplos** (selector en la tarjeta de contexto): 4 problemas de aplicación y 3 casos especiales (óptimos múltiples, degenerado y no acotado). Se pueden abrir por enlace: `/metodo_simplex/?ejemplo=muebles&resolver=1` (ids: `puertas`, `muebles`, `jugos`, `inversion`, `multiples`, `degenerado`, `no_acotado`).
- **Ruta del algoritmo**: con 2 variables, un punto recorre los vértices de la región factible; la gráfica de Z funciona con cualquier número de variables.
- **El dual** (`dual` en la respuesta): modelo dual, valores `y*`, dualidad fuerte (`W* = Z*`) y holguras complementarias.
- **¿Y si…?**: deslizador sobre un recurso dentro de su rango de validez (`sens_restricciones[i].efecto_variables`); al soltar, se verifica volviendo a llamar a la API.
- **Informe en PDF**: botón «Descargar informe»; usa la impresión del navegador con una hoja de estilo propia (`@media print`).
