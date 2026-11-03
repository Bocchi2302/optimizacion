# Método de las Dos Fases

Resuelve problemas de programación lineal con restricciones **≤, ≥ e =** mediante el Método de las
Dos Fases (procedimiento de la Ing. Diana Linena Velásquez Romero). Es el módulo al que remite
`SIMPLEX.md` para los modelos con restricciones ≥ o =. La sección se encuentra en `/metodo_dos_fases/`.

## Características principales

1. **Editor como en el cuaderno**: `Max/Min Z = c₁x₁ + …`, de 1 a 8 variables y de 1 a 12 restricciones;
   admite enteros, decimales (punto o coma) y fracciones como `1/3`. Vista previa en vivo y lista
   «Lo que hará el método» (holguras, excedentes y artificiales antes de resolver).
2. **Cálculo exacto** con `fractions.Fraction`, convención `Z − Σcⱼxⱼ = 0`. Fase 1: se minimiza
   `r = ΣA` (r original y r reducida). Fase 2: se conserva la base, se retiran r y las artificiales, se
   escribe Z original con K = 0 y luego se reduce respecto de la base.
3. **Todas las tablas**, con la razón mínima (solo coeficientes positivos), la variable que entra y la que
   sale, el pivote encerrado, la normalización y cada operación por componente.
4. **Bitácora en cada tabla**: qué se hizo, qué muestra la tabla, quién entra y quién sale.
5. **Recorrido guiado** para exponer (una diapositiva por paso, teclas ← →, pantalla completa).
6. **Comprobación** en las restricciones originales y **conclusión destacada** con los nombres, unidades
   y valores del modelo (decisión, valor de Z, restricciones que limitan el resultado).
7. **Casos especiales**: infactible, no acotado (punto y dirección), degeneración, filas redundantes,
   artificiales básicas en cero, K negativos, óptimos alternativos y regla de Bland contra ciclos.
8. Informe HTML descargable (funciona sin internet) e impresión a PDF.

## Estructura de archivos

- `blueprints/dos_fases_bp.py`: Blueprint `dos_fases_bp`, rutas y recepción de datos.
- `blueprints/dos_fases_solver.py`: Procedimiento matemático, bitácora, conclusión y ejemplos.
- `templates/metodo_dos_fases/index.html`: Formulario, tablas, operaciones, resultados y recorrido guiado.
- `static/css/dos_fases.css`: Estilos del módulo (todas las clases llevan el prefijo `df-`; no afectan a otras páginas).
- `static/js/dos_fases.js`: Interacción del formulario, pestañas y recorrido guiado.
- `static/fonts/dos_fases/`: Fuentes locales con licencia OFL (sin CDN).
- `tests/test_dos_fases*.py`: Pruebas unitarias, auditoría exacta de cada pivote, contraste opcional con SciPy
  (se omite si SciPy no está instalado) e integración con `app.py`.
- `tests/e2e_dos_fases_navegador.py`: Prueba opcional en navegador (requiere Playwright; no la ejecuta `unittest`).

## Ejecución de pruebas

```sh
python -m unittest discover -s tests -v
```

No requiere dependencias nuevas: solo Flask, que ya está en `requirements.txt`.
