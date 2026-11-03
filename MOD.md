# Método MOD (Distribución Modificada - MODI)

El **Método MOD** (o Método MODI) optimiza problemas de transporte tanto en **Minimización de Costos** como en **Maximización de Utilidades**. La sección se encuentra disponible en `/metodo_mod/`.

## Características Principales

1. **Cuadro de Contexto del Ejercicio**: Permite al usuario redactar el enunciado o situación real (empresa, plantas, centros de distribución, etc.) para personalizar automáticamente la conclusión e interpretación.
2. **Sentido de Optimización**: Soporta tanto `Maximizar` (beneficios/utilidades) como `Minimizar` (costos de flete).
3. **Cálculo de Multiplicadores**: Resuelve el sistema $u_i + v_j = c_{ij}$ para todas las celdas básicas (fijando $u_1 = 0$).
4. **Costes de Mejora ($\Delta_{ij}$)**:
   - Evalúa cada celda no básica mediante $\Delta_{ij} = c_{ij} - u_i - v_j$.
   - **En Maximización**: El óptimo requiere $\Delta_{ij} \le 0$ para todas las rutas vacías. Cada coste negativo indica la reducción de ganancia si se forzara esa ruta.
   - **En Minimización**: El óptimo requiere $\Delta_{ij} \ge 0$ para todas las rutas vacías. Cada coste positivo indica el sobrecosto unitario si se usara esa ruta.
   - Si $\Delta_{ij} = 0$, indica la existencia de **soluciones óptimas alternativas**.
5. **Iteraciones y Ciclo Stepping-Stone**: Determina la celda entrante, traza el camino cerrado ortogonal alternando signos $+$ y $-$, calcula el valor de ajuste $\theta$ y reasigna unidades hasta alcanzar la optimalidad.
6. **Conclusión Detallada e Interpretación Gerencial**:
   - Expone el contexto ingresado del ejercicio.
   - Detalla el valor óptimo de $Z$ y el plan de distribución.
   - Explica explícitamente **cuáles fueron los costes de mejora** de las rutas no utilizadas y su significado económico.
   - Proporciona recomendaciones gerenciales para la toma de decisiones.

## Estructura de Archivos

- `blueprints/mod_bp.py`: Controlador Flask del blueprint `/metodo_mod`.
- `blueprints/mod_solver.py`: Algoritmo de resolución exacta, cálculo de multiplicadores, ciclos y generador de conclusiones.
- `templates/metodo_mod/index.html`: Interfaz web interactiva con cuadro de contexto, matriz dinámica y panel de conclusión destacada.
- `templates/metodo_mod/assets/mod.css`: Estilos visuales con diseño responsivo y tarjetas de resultados.
- `templates/metodo_mod/assets/mod.js`: Lógica del cliente para agregar/quitar orígenes y destinos, balance dinámico y carga de ejemplos.
- `tests/test_mod.py`: Suite de pruebas unitarias.

## Ejecución de Pruebas

```sh
python -m unittest discover -s tests -v
```
