# blueprints/grafico_bp.py
from flask import Blueprint, render_template, request
import matplotlib
matplotlib.use('Agg') # Usar backend sin interfaz gráfica para evitar errores en hilos (threads)
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import itertools

grafico_bp = Blueprint('grafico_bp', __name__)

def calcular_interseccion(eq1, eq2):
    """
    Calcula la intersección entre dos rectas de la forma ax + by = c.
    eq1 y eq2 son tuplas (a, b, c).
    """
    A = np.array([[eq1[0], eq1[1]], [eq2[0], eq2[1]]])
    B = np.array([eq1[2], eq2[2]])
    try:
        # np.linalg.solve lanza error si la matriz es singular (rectas paralelas)
        punto = np.linalg.solve(A, B)
        return float(punto[0]), float(punto[1])
    except np.linalg.LinAlgError:
        return None

def es_factible(x, y, restricciones):
    """Verifica si un punto (x, y) cumple con todas las restricciones del problema"""
    # Restricción implícita de no negatividad (con tolerancia por precisión decimal)
    if x < -1e-5 or y < -1e-5:
        return False
        
    for a, b, op, c in restricciones:
        valor = a * x + b * y
        if op == '<=' and valor > c + 1e-5:
            return False
        if op == '>=' and valor < c - 1e-5:
            return False
    return True

@grafico_bp.route('/', methods=['GET', 'POST'])
def vista_principal():
    grafica_base64 = None
    resultados = None
    error = None
    
    if request.method == 'POST':
        try:
            # 1. Recoger Función Objetivo
            tipo_opt = request.form.get('tipo_opt', 'max')
            z_x = float(request.form.get('z_x', 0))
            z_y = float(request.form.get('z_y', 0))
            
            # 2. Recoger Restricciones enviadas por el formulario
            r_x = request.form.getlist('r_x[]')
            r_y = request.form.getlist('r_y[]')
            r_op = request.form.getlist('r_op[]')
            r_c = request.form.getlist('r_c[]')
            
            restricciones = []
            
            # Ecuaciones base para calcular intersecciones: incluye el eje X (y=0) y eje Y (x=0)
            ecuaciones = [
                (1, 0, 0), # Ecuación del eje Y: x = 0
                (0, 1, 0)  # Ecuación del eje X: y = 0
            ]
            
            for i in range(len(r_x)):
                a = float(r_x[i])
                b = float(r_y[i])
                op = r_op[i]
                c = float(r_c[i])
                restricciones.append((a, b, op, c))
                ecuaciones.append((a, b, c)) # Tratamos cada inecuación como una recta (ecuación)
                
            # 3. Calcular todos los puntos de intersección entre todos los pares de rectas
            puntos_interseccion = []
            for eq1, eq2 in itertools.combinations(ecuaciones, 2):
                punto = calcular_interseccion(eq1, eq2)
                if punto:
                    puntos_interseccion.append(punto)
                    
            # 4. Encontrar la región factible filtrando los vértices que no cumplen todas las restricciones
            vertices_factibles = []
            for p in puntos_interseccion:
                if es_factible(p[0], p[1], restricciones):
                    # Evitar agregar puntos duplicados
                    if not any(np.allclose(p, vf, atol=1e-5) for vf in vertices_factibles):
                        vertices_factibles.append(p)
                        
            if not vertices_factibles:
                error = "El problema no tiene región factible o las restricciones son incompatibles."
            else:
                # 5. Evaluar la función objetivo (Z) en cada vértice de la región factible
                evaluaciones = []
                for x, y in vertices_factibles:
                    z = z_x * x + z_y * y
                    evaluaciones.append({'x': x, 'y': y, 'z': z})
                    
                # 6. Determinar cuál es el vértice óptimo
                if tipo_opt == 'max':
                    optimo = max(evaluaciones, key=lambda item: item['z'])
                else:
                    optimo = min(evaluaciones, key=lambda item: item['z'])
                    
                resultados = {
                    'vertices': evaluaciones,
                    'optimo': optimo,
                    'tipo': tipo_opt
                }
                
                # 7. Trazado de la gráfica con Matplotlib
                fig, ax = plt.subplots(figsize=(8, 6))
                
                # Ajustar los límites de los ejes basándose en los vértices factibles encontrados
                max_x = max(v[0] for v in vertices_factibles) * 1.5 if vertices_factibles else 10
                max_y = max(v[1] for v in vertices_factibles) * 1.5 if vertices_factibles else 10
                if max_x == 0: max_x = 10
                if max_y == 0: max_y = 10
                
                x_vals = np.linspace(0, max_x, 400)
                
                # Dibujar las rectas de cada restricción
                for i, (a, b, op, c) in enumerate(restricciones):
                    if b != 0:
                        y_vals = (c - a * x_vals) / b
                        ax.plot(x_vals, y_vals, label=f'R{i+1}: {a}X1 + {b}X2 {op} {c}')
                    elif a != 0:
                        # Si b es 0, es una línea vertical
                        ax.axvline(x=c/a, label=f'R{i+1}: {a}X1 {op} {c}', color=np.random.rand(3,))
                        
                # Colorear la región factible usando el método del centroide para el polígono
                if len(vertices_factibles) >= 3:
                    cx = sum(v[0] for v in vertices_factibles) / len(vertices_factibles)
                    cy = sum(v[1] for v in vertices_factibles) / len(vertices_factibles)
                    # Ordenamos los vértices por ángulo respecto al centroide para armar el polígono
                    vertices_ordenados = sorted(vertices_factibles, key=lambda p: np.arctan2(p[1]-cy, p[0]-cx))
                    poly_x = [p[0] for p in vertices_ordenados]
                    poly_y = [p[1] for p in vertices_ordenados]
                    ax.fill(poly_x, poly_y, alpha=0.3, color='green', label='Región Factible')
                elif len(vertices_factibles) == 2:
                    ax.plot([v[0] for v in vertices_factibles], [v[1] for v in vertices_factibles], color='green', linewidth=4, alpha=0.5, label='Región Factible (Línea)')
                elif len(vertices_factibles) == 1:
                    ax.plot(vertices_factibles[0][0], vertices_factibles[0][1], 'go', markersize=10, label='Región Factible (Punto único)')
                    
                # Puntos de los vértices factibles
                for v in vertices_factibles:
                    ax.plot(v[0], v[1], 'ko', markersize=4)
                    
                # Resaltar el Punto Óptimo
                ax.plot(optimo['x'], optimo['y'], 'r*', markersize=12, label=f'Óptimo: Z={optimo["z"]:.2f}')
                
                # Configuraciones de presentación
                ax.set_xlim(0, max_x)
                ax.set_ylim(0, max_y)
                ax.set_xlabel('X1')
                ax.set_ylabel('X2')
                ax.set_title('Resolución por Método Gráfico')
                ax.legend(loc='upper right', bbox_to_anchor=(1.4, 1))
                ax.grid(True, linestyle='--', alpha=0.6)
                
                # Exportar la gráfica como imagen en Base64
                img = io.BytesIO()
                plt.savefig(img, format='png', bbox_inches='tight')
                img.seek(0)
                grafica_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
                plt.close() # Limpiar memoria de la figura
                
        except Exception as e:
            error = f"Ocurrió un error al procesar el cálculo: {str(e)}"
            
    return render_template('metodo_grafico/resolucion.html', grafica=grafica_base64, resultados=resultados, error=error)
