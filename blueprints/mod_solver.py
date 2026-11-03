"""Módulo del Método MOD / MODI (Distribución Modificada) para Problemas de Transporte.

Resuelve problemas de transporte en minimización o maximización, calculando:
- Solución inicial factible (balanceo automático y método Vogel o asignación directa).
- Multiplicadores u_i y v_j.
- Costes de mejora (índices de mejora) para celdas no básicas.
- Ciclos cerrados (stepping-stone) para redistribución theta.
- Conclusión detallada basada en el contexto del ejercicio y análisis de los costes de mejora.
"""

from fractions import Fraction
import re


def _a_fraccion(valor, nombre="Valor"):
    """Convierte un valor numérico o cadena a Fraction exacta."""
    if valor is None:
        raise ValueError(f"{nombre} no puede estar vacío.")
    if isinstance(valor, Fraction):
        return valor
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        raise ValueError(f"{nombre} no puede estar vacío.")
    try:
        return Fraction(texto)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"{nombre} «{valor}» debe ser un número válido.")


def _formato_num(frac):
    """Devuelve representación legible en cadena para enteros o decimales."""
    if frac is None:
        return "—"
    f = Fraction(frac)
    if f.denominator == 1:
        return str(f.numerator)
    val = float(f)
    texto = f"{val:.4f}".rstrip("0").rstrip(".")
    return texto


def completar_base(m, n, celdas_basicas):
    """Garantiza exactamente m + n - 1 celdas básicas sin ciclos (árbol generador)."""
    parent = list(range(m + n))

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
            return True
        return False

    base = set()
    for r, c in celdas_basicas:
        if union(r, m + c):
            base.add((r, c))

    # Conectar componentes desconectadas con celdas de asignación 0 (degeneración)
    for r in range(m):
        for c in range(n):
            if len(base) == m + n - 1:
                break
            if union(r, m + c):
                base.add((r, c))

    return base


def calcular_solucion_inicial_vogel(costos, oferta, demanda, tipo_opt="min"):
    """Genera una solución básica factible inicial usando aproximación de Vogel."""
    m = len(oferta)
    n = len(demanda)
    rem_s = [Fraction(s) for s in oferta]
    rem_d = [Fraction(d) for d in demanda]
    alloc = [[Fraction(0) for _ in range(n)] for _ in range(m)]
    celdas_basicas = set()

    activas_filas = set(range(m))
    activas_cols = set(range(n))

    while activas_filas and activas_cols:
        if len(activas_filas) == 1:
            r = list(activas_filas)[0]
            for c in sorted(activas_cols):
                q = min(rem_s[r], rem_d[c])
                alloc[r][c] += q
                celdas_basicas.add((r, c))
                rem_s[r] -= q
                rem_d[c] -= q
            break

        if len(activas_cols) == 1:
            c = list(activas_cols)[0]
            for r in sorted(activas_filas):
                q = min(rem_s[r], rem_d[c])
                alloc[r][c] += q
                celdas_basicas.add((r, c))
                rem_s[r] -= q
                rem_d[c] -= q
            break

        # Calcular penalizaciones
        candidatos = []
        for r in activas_filas:
            vals = sorted([costos[r][c] for c in activas_cols], reverse=(tipo_opt == "max"))
            pen = abs(vals[0] - vals[1]) if len(vals) > 1 else vals[0]
            candidatos.append((pen, "r", r))

        for c in activas_cols:
            vals = sorted([costos[r][c] for r in activas_filas], reverse=(tipo_opt == "max"))
            pen = abs(vals[0] - vals[1]) if len(vals) > 1 else vals[0]
            candidatos.append((pen, "c", c))

        candidatos.sort(key=lambda item: item[0], reverse=True)
        _, tipo, idx = candidatos[0]

        if tipo == "r":
            r = idx
            if tipo_opt == "max":
                c = max(activas_cols, key=lambda col: costos[r][col])
            else:
                c = min(activas_cols, key=lambda col: costos[r][col])
        else:
            c = idx
            if tipo_opt == "max":
                r = max(activas_filas, key=lambda row: costos[row][c])
            else:
                r = min(activas_filas, key=lambda row: costos[row][c])

        q = min(rem_s[r], rem_d[c])
        alloc[r][c] += q
        celdas_basicas.add((r, c))
        rem_s[r] -= q
        rem_d[c] -= q

        if rem_s[r] == 0 and rem_d[c] == 0:
            activas_filas.remove(r)
        elif rem_s[r] == 0:
            activas_filas.remove(r)
        else:
            activas_cols.remove(c)

    base_completa = completar_base(m, n, celdas_basicas)
    return alloc, base_completa


def encontrar_ciclo_stepping_stone(m, n, celdas_basicas, celda_entrante):
    """Encuentra el ciclo cerrado único entre la celda entrante y las básicas."""
    celdas = set(celdas_basicas) | {celda_entrante}

    # Poda recursiva de hojas (celdas con menos de 2 vecinas en fila o columna)
    while True:
        conteo_filas = {r: 0 for r in range(m)}
        conteo_cols = {c: 0 for c in range(n)}
        for r, c in celdas:
            conteo_filas[r] += 1
            conteo_cols[c] += 1
        removibles = {c for c in celdas if conteo_filas[c[0]] < 2 or conteo_cols[c[1]] < 2}
        if not removibles:
            break
        celdas -= removibles

    ciclo = [celda_entrante]

    def dfs(actual, buscar_horizontal):
        if len(ciclo) >= 4 and len(ciclo) % 2 == 0:
            if buscar_horizontal and actual[0] == celda_entrante[0]:
                return True
            if not buscar_horizontal and actual[1] == celda_entrante[1]:
                return True
        for siguiente in celdas:
            if siguiente in ciclo:
                continue
            if buscar_horizontal and siguiente[0] == actual[0]:
                ciclo.append(siguiente)
                if dfs(siguiente, False):
                    return True
                ciclo.pop()
            elif not buscar_horizontal and siguiente[1] == actual[1]:
                ciclo.append(siguiente)
                if dfs(siguiente, True):
                    return True
                ciclo.pop()
        return False

    if not dfs(celda_entrante, True):
        dfs(celda_entrante, False)

    return ciclo


def generar_conclusion_mod(
    contexto,
    tipo_opt,
    z_optimo,
    asignaciones_finales,
    costos_finales,
    nombres_origenes,
    nombres_destinos,
    costes_mejora,
    iteraciones_totales,
    hay_alternas=False,
):
    """Genera la conclusión e interpretación gerencial del Método MOD."""
    tipo_texto = "Maximización de Utilidades / Beneficios" if tipo_opt == "max" else "Minimización de Costos"
    verbo = "maximizar" if tipo_opt == "max" else "minimizar"
    sustantivo = "la ganancia o beneficio total" if tipo_opt == "max" else "el costo total de transporte"
    z_str = _formato_num(z_optimo)

    # 1. Párrafo inicial contextualizado
    ctx = contexto.strip()
    if ctx:
        p1 = f"Para el ejercicio planteado: «{ctx}», se aplicó el Método MOD (Método de Distribución Modificada) con el objetivo de {verbo} {sustantivo}."
    else:
        p1 = f"Se ha completado con éxito la optimización mediante el Método MOD (Distribución Modificada) con el objetivo de {verbo} {sustantivo}."

    # 2. Resultado óptimo y asignaciones
    p2 = f"El valor óptimo alcanzado de la función objetivo es Z = {z_str}."

    rutas_asignadas = []
    for i, orig in enumerate(nombres_origenes):
        for j, dest in enumerate(nombres_destinos):
            cant = asignaciones_finales[i][j]
            if cant > 0:
                costo_u = costos_finales[i][j]
                sub = cant * costo_u
                rutas_asignadas.append(
                    f"Desde {orig} hacia {dest}: {_formato_num(cant)} unidades (costo/utilidad unitario: {_formato_num(costo_u)}, subtotal: {_formato_num(sub)})."
                )

    # 3. Análisis explícito de los costes de mejora
    lista_costes = []
    for item in costes_mejora:
        orig = item["origen"]
        dest = item["destino"]
        delta_str = _formato_num(item["delta"])
        lista_costes.append(f"• Ruta {orig} → {dest}: Coste de mejora Δ = {delta_str}")

    texto_costes_detalle = "\n".join(lista_costes)

    if tipo_opt == "max":
        p_costes = (
            f"En este ejercicio de maximización, los costes de mejora calculados (índices Δ_ij = c_ij - u_i - v_j) "
            f"para todas las rutas no utilizadas resultaron menores o iguales a cero (Δ_ij ≤ 0):\n"
            f"{texto_costes_detalle}\n"
            f"Interpretación de los costes de mejora: Cada valor negativo indica que habilitar envíos en esa ruta "
            f"provocaría una pérdida o reducción neta de utilidad por unidad igual a dicho valor absoluto. "
            f"Al no existir ningún coste de mejora positivo, se certifica formalmente que no es posible incrementar "
            f"más las ganancias y la solución es óptima."
        )
    else:
        p_costes = (
            f"En este ejercicio de minimización, los costes de mejora calculados (índices Δ_ij = c_ij - u_i - v_j) "
            f"para todas las rutas no utilizadas resultaron mayores o iguales a cero (Δ_ij ≥ 0):\n"
            f"{texto_costes_detalle}\n"
            f"Interpretación de los costes de mejora: Cada valor positivo representa el costo adicional unitario en el que "
            f"se incurriría si se decidiera enviar mercancía por esa ruta. Al ser todos los costes de mejora no negativos, "
            f"ninguna reasignación puede reducir el costo actual, demostrando matemáticamente que se alcanzó el costo mínimo."
        )

    # 4. Soluciones alternativas y recomendación
    if hay_alternas:
        p_alternas = (
            "Nota sobre soluciones múltiples: Al menos una ruta no básica presenta un coste de mejora exactamente igual a 0.00. "
            "Esto significa que existe una solución óptima alternativa que logra el mismo valor de Z pero con una distribución diferente de rutas."
        )
    else:
        p_alternas = "La solución óptima encontrada es única, ya que todos los costes de mejora son estrictamente distintos de cero."

    p_recomendacion = (
        f"Recomendación: Implementar el plan de distribución obtenido ({len(rutas_asignadas)} rutas asignadas) para asegurar "
        f"{sustantivo} de {z_str}. La convergencia óptima se alcanzó en {iteraciones_totales} iteración(es) del Método MOD."
    )

    parrafos = [p1, p2, p_costes, p_alternas, p_recomendacion]

    return {
        "resumen": f"Solución óptima alcanzada por Método MOD ({'Maximización' if tipo_opt == 'max' else 'Minimización'}): Z = {z_str}.",
        "parrafos": parrafos,
        "analisis_costes_mejora": p_costes,
        "rutas_asignadas": rutas_asignadas,
        "tipo_texto": tipo_texto,
        "z_str": z_str,
    }


def resolver_metodo_mod(
    costos_raw,
    oferta_raw,
    demanda_raw,
    tipo_opt="min",
    contexto="",
    nombres_origenes=None,
    nombres_destinos=None,
):
    """Resuelve el problema de transporte completo mediante el Método MOD / MODI."""
    if tipo_opt not in ("min", "max"):
        tipo_opt = "min"

    m_orig = len(oferta_raw)
    n_orig = len(demanda_raw)

    if m_orig == 0 or n_orig == 0:
        raise ValueError("Debe ingresar al menos un origen y un destino.")
    if len(costos_raw) != m_orig or any(len(fila) != n_orig for fila in costos_raw):
        raise ValueError("Las dimensiones de la matriz de costos no coinciden con la oferta y demanda.")

    # Convertir a Fraction
    costos = [[_a_fraccion(costos_raw[i][j], f"Costo O{i+1}-D{j+1}") for j in range(n_orig)] for i in range(m_orig)]
    oferta = [_a_fraccion(oferta_raw[i], f"Oferta O{i+1}") for i in range(m_orig)]
    demanda = [_a_fraccion(demanda_raw[j], f"Demanda D{j+1}") for j in range(n_orig)]

    if any(o < 0 for o in oferta):
        raise ValueError("Los valores de oferta no pueden ser negativos.")
    if any(d < 0 for d in demanda):
        raise ValueError("Los valores de demanda no pueden ser negativos.")

    nombres_o = list(nombres_origenes) if nombres_origenes else [f"Origen {i + 1}" for i in range(m_orig)]
    nombres_d = list(nombres_destinos) if nombres_destinos else [f"Destino {j + 1}" for j in range(n_orig)]

    total_oferta = sum(oferta, Fraction(0))
    total_demanda = sum(demanda, Fraction(0))

    if total_oferta == 0 and total_demanda == 0:
        raise ValueError("La oferta y la demanda total no pueden ser cero.")

    balanceado = False
    ficticio_tipo = None
    ficticio_cantidad = Fraction(0)

    # Balancear el problema
    if total_oferta < total_demanda:
        balanceado = True
        ficticio_tipo = "origen"
        ficticio_cantidad = total_demanda - total_oferta
        costos.append([Fraction(0)] * n_orig)
        oferta.append(ficticio_cantidad)
        nombres_o.append("Origen Ficticio")
    elif total_oferta > total_demanda:
        balanceado = True
        ficticio_tipo = "destino"
        ficticio_cantidad = total_oferta - total_demanda
        for i in range(len(costos)):
            costos[i].append(Fraction(0))
        demanda.append(ficticio_cantidad)
        nombres_d.append("Destino Ficticio")

    m = len(oferta)
    n = len(demanda)

    # 1. Obtener solución inicial con Vogel
    alloc, b_cells = calcular_solucion_inicial_vogel(costos, oferta, demanda, tipo_opt)

    iteraciones = []
    iter_max = 50
    iter_count = 0

    while iter_count < iter_max:
        iter_count += 1

        # Resolver multiplicadores u_i y v_j mediante BFS fijando u_0 = 0
        u = [None] * m
        v = [None] * n
        u[0] = Fraction(0)
        cola = [("u", 0)]
        visitados_u = {0}
        visitados_v = set()

        while cola:
            tipo_nodo, idx = cola.pop(0)
            if tipo_nodo == "u":
                r = idx
                for c in range(n):
                    if (r, c) in b_cells and c not in visitados_v:
                        v[c] = costos[r][c] - u[r]
                        visitados_v.add(c)
                        cola.append(("v", c))
            else:
                c = idx
                for r in range(m):
                    if (r, c) in b_cells and r not in visitados_u:
                        u[r] = costos[r][c] - v[c]
                        visitados_u.add(r)
                        cola.append(("u", r))

        # En caso de subgrafos desconectados por alguna razón, fijar u restante a 0
        for r in range(m):
            if u[r] is None:
                u[r] = Fraction(0)
        for c in range(n):
            if v[c] is None:
                v[c] = Fraction(0)

        # Calcular costes de mejora (índices Δ_ij) para celdas no básicas
        deltas = {}
        costes_mejora_lista = []
        for r in range(m):
            for c in range(n):
                if (r, c) not in b_cells:
                    delta = costos[r][c] - (u[r] + v[c])
                    deltas[(r, c)] = delta
                    costes_mejora_lista.append(
                        {
                            "origen": nombres_o[r],
                            "destino": nombres_d[c],
                            "i": r,
                            "j": c,
                            "costo": costos[r][c],
                            "u": u[r],
                            "v": v[c],
                            "delta": delta,
                            "delta_str": _formato_num(delta),
                        }
                    )

        z_actual = sum(alloc[r][c] * costos[r][c] for r in range(m) for c in range(n))

        # Determinar si la solución actual es óptima
        es_optimo = False
        celda_entrante = None
        if tipo_opt == "max":
            # Para maximizar: óptimo si todos los Δ_ij <= 0
            if not deltas or all(d <= 0 for d in deltas.values()):
                es_optimo = True
            else:
                # Entra la celda con el mayor Δ_ij positivo
                celda_entrante = max(deltas.items(), key=lambda item: item[1])[0]
        else:
            # Para minimizar: óptimo si todos los Δ_ij >= 0
            if not deltas or all(d >= 0 for d in deltas.values()):
                es_optimo = True
            else:
                # Entra la celda con el menor Δ_ij negativo
                celda_entrante = min(deltas.items(), key=lambda item: item[1])[0]

        registro_iter = {
            "numero": iter_count,
            "asignaciones": [[alloc[r][c] for c in range(n)] for r in range(m)],
            "u": list(u),
            "v": list(v),
            "u_str": [_formato_num(x) for x in u],
            "v_str": [_formato_num(x) for x in v],
            "costes_mejora": costes_mejora_lista,
            "z": z_actual,
            "z_str": _formato_num(z_actual),
            "es_optimo": es_optimo,
            "celda_entrante": celda_entrante,
            "celda_entrante_nombre": (
                f"{nombres_o[celda_entrante[0]]} → {nombres_d[celda_entrante[1]]}"
                if celda_entrante
                else None
            ),
            "celda_saliente": None,
            "theta": None,
            "theta_str": None,
            "circuito": None,
        }

        if es_optimo:
            iteraciones.append(registro_iter)
            break

        # Buscar el ciclo stepping-stone para la celda entrante
        ciclo = encontrar_ciclo_stepping_stone(m, n, b_cells, celda_entrante)
        registro_iter["circuito"] = ciclo

        # Posiciones con signo menos
        celdas_menos = [ciclo[idx] for idx in range(1, len(ciclo), 2)]
        theta = min(alloc[r][c] for r, c in celdas_menos)
        registro_iter["theta"] = theta
        registro_iter["theta_str"] = _formato_num(theta)

        # Actualizar asignaciones
        for idx, (r, c) in enumerate(ciclo):
            if idx % 2 == 0:
                alloc[r][c] += theta
            else:
                alloc[r][c] -= theta

        # Celda saliente: primera celda con signo menos cuya asignación queda en 0
        celda_saliente = next((r, c) for r, c in celdas_menos if alloc[r][c] == 0)
        registro_iter["celda_saliente"] = celda_saliente
        registro_iter["celda_saliente_nombre"] = (
            f"{nombres_o[celda_saliente[0]]} → {nombres_d[celda_saliente[1]]}"
        )

        b_cells.remove(celda_saliente)
        b_cells.add(celda_entrante)

        iteraciones.append(registro_iter)

    # Evaluar solución óptima final
    hay_alternas = any(item["delta"] == 0 for item in iteraciones[-1]["costes_mejora"])

    conclusion = generar_conclusion_mod(
        contexto=contexto,
        tipo_opt=tipo_opt,
        z_optimo=iteraciones[-1]["z"],
        asignaciones_finales=iteraciones[-1]["asignaciones"],
        costos_finales=costos,
        nombres_origenes=nombres_o,
        nombres_destinos=nombres_d,
        costes_mejora=iteraciones[-1]["costes_mejora"],
        iteraciones_totales=len(iteraciones),
        hay_alternas=hay_alternas,
    )

    return {
        "tipo_opt": tipo_opt,
        "contexto": contexto,
        "nombres_origenes": nombres_o,
        "nombres_destinos": nombres_d,
        "costos": [[_formato_num(c) for c in fila] for fila in costos],
        "oferta": [_formato_num(o) for o in oferta],
        "demanda": [_formato_num(d) for d in demanda],
        "oferta_total": _formato_num(total_oferta),
        "demanda_total": _formato_num(total_demanda),
        "balanceado": balanceado,
        "ficticio_tipo": ficticio_tipo,
        "ficticio_cantidad": _formato_num(ficticio_cantidad),
        "iteraciones": iteraciones,
        "solucion_optima": {
            "z": iteraciones[-1]["z"],
            "z_str": iteraciones[-1]["z_str"],
            "asignaciones": [[_formato_num(c) for c in fila] for fila in iteraciones[-1]["asignaciones"]],
            "costes_mejora": iteraciones[-1]["costes_mejora"],
            "u_str": iteraciones[-1]["u_str"],
            "v_str": iteraciones[-1]["v_str"],
            "hay_alternas": hay_alternas,
        },
        "conclusion": conclusion,
    }

