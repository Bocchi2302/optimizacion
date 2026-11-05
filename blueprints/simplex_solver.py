"""Simplex normal (tabla con variables de holgura) con análisis de sensibilidad.

Resuelve  max/min Z = c·x  sujeto a  A·x <= b,  x >= 0,  con b >= 0.
No usa variables artificiales: las restricciones >= o = y los lados derechos
negativos corresponden al Simplex de dos fases, que es otro módulo.
"""
from __future__ import annotations

from fractions import Fraction

MAX_VARIABLES = 10
MAX_RESTRICCIONES = 12
LIMITE = 10**9
MAX_ITER = 500
ITER_BLAND = 50      # tras estas iteraciones se usa la regla de Bland para evitar ciclos


def _numero(valor, etiqueta):
    """Convierte a Fraction aceptando números JSON, '2.5', '2,5' y '1/3'."""
    if isinstance(valor, bool) or valor is None:
        raise ValueError(f"«{etiqueta}» debe ser un número.")
    try:
        texto = str(valor).strip().replace(",", ".")
        numero = Fraction(texto)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"«{etiqueta}» debe ser un número válido.") from None
    if abs(numero) > LIMITE:
        raise ValueError(f"«{etiqueta}» está fuera del rango permitido.")
    return numero


def _flotante(v):
    return round(float(v), 9)


def _t(v):
    """Número para frases: entero, fracción sencilla (3/2) o decimal."""
    v = Fraction(v)
    if v.denominator == 1:
        texto = str(v.numerator)
    elif v.denominator <= 12:
        texto = f"{v.numerator}/{v.denominator}"
    else:
        texto = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return texto.replace("-", "−")


def _p(v):
    """Como _t, pero encierra las fracciones entre paréntesis para que 110/3 ÷ 2/3 no se lea ambiguo."""
    texto = _t(v)
    return f"({texto})" if "/" in texto else texto


def _texto(valor, defecto, largo=40):
    texto = str(valor or "").strip()[:largo]
    return texto or defecto


def validar(payload):
    """Valida el JSON recibido y devuelve un diccionario normalizado."""
    if not isinstance(payload, dict):
        raise ValueError("Envía un JSON con el problema.")
    sentido = payload.get("sentido")
    if sentido not in ("max", "min"):
        raise ValueError("El objetivo debe ser 'max' o 'min'.")
    variables = payload.get("variables")
    restricciones = payload.get("restricciones")
    if not isinstance(variables, list) or not 1 <= len(variables) <= MAX_VARIABLES:
        raise ValueError(f"Usa entre 1 y {MAX_VARIABLES} variables.")
    if not isinstance(restricciones, list) or not 1 <= len(restricciones) <= MAX_RESTRICCIONES:
        raise ValueError(f"Usa entre 1 y {MAX_RESTRICCIONES} restricciones.")
    n = len(variables)

    nombres, unidades, c = [], [], []
    for j, var in enumerate(variables, 1):
        var = var if isinstance(var, dict) else {}
        nombres.append(_texto(var.get("nombre"), f"x{j}", 20))
        unidades.append(_texto(var.get("unidad"), "", 20))
        c.append(_numero(var.get("costo"), f"coeficiente de {nombres[-1]} en Z"))

    filas, rhs, nom_res, uni_res = [], [], [], []
    for i, res in enumerate(restricciones, 1):
        res = res if isinstance(res, dict) else {}
        nom_res.append(_texto(res.get("nombre"), f"R{i}", 30))
        uni_res.append(_texto(res.get("unidad"), "", 20))
        coefs = res.get("coefs")
        if not isinstance(coefs, list) or len(coefs) != n:
            raise ValueError(f"La restricción {i} debe tener {n} coeficientes.")
        if res.get("tipo", "<=") != "<=":
            raise ValueError(
                f"La restricción {i} no es de tipo ≤. El Simplex normal solo admite ≤; "
                "para ≥ o = se necesita el Simplex de dos fases.")
        filas.append([_numero(a, f"coeficiente de la restricción {i}") for a in coefs])
        b = _numero(res.get("rhs"), f"lado derecho de la restricción {i}")
        if b < 0:
            raise ValueError(
                f"El lado derecho de la restricción {i} es negativo. El Simplex normal exige b ≥ 0; "
                "en ese caso se necesita el Simplex de dos fases.")
        rhs.append(b)

    return dict(sentido=sentido, c=c, A=filas, b=rhs, nombres=nombres, unidades=unidades,
                nom_res=nom_res, uni_res=uni_res,
                unidad_z=_texto(payload.get("unidad_z"), "", 20),
                contexto=str(payload.get("contexto") or "").strip()[:2000])


class _Tabla:
    def __init__(self, p):
        self.p = p
        self.n, self.m = len(p["c"]), len(p["b"])
        n, m = self.n, self.m
        self.signo = 1 if p["sentido"] == "max" else -1          # Z interna = signo · Z
        self.c = [self.signo * v for v in p["c"]]
        self.nombres = p["nombres"] + [f"s{i+1}" for i in range(m)]
        self.T = [fila[:] + [Fraction(int(i == k)) for k in range(m)] + [p["b"][i]]
                  for i, fila in enumerate(p["A"])]
        self.base = [n + i for i in range(m)]
        costos = self.c + [Fraction(0)] * m
        self.Z = [-v for v in costos] + [Fraction(0)]            # fila zj - cj ; último = Z
        self.historial = []

    def foto(self, etiqueta, pivote=None, explicacion="", razones=None):
        filas = [[_flotante(v) for v in fila] for fila in self.T] + [[_flotante(v) for v in self.Z]]
        self.historial.append({
            "label": etiqueta,
            "columns": self.nombres + ["LD"],
            "basis": [self.nombres[j] for j in self.base],
            "basis_idx": list(self.base),
            "rows": filas,
            "pivot": list(pivote) if pivote else None,
            "ratios": None if razones is None else [None if r is None else _flotante(r) for r in razones],
            "explicacion": explicacion,
        })

    # ------------------------------------------------------------------ explicaciones en palabras
    def _largo(self, j):
        """Nombre de la variable; las holguras indican de qué recurso son."""
        if j < self.n:
            return self.nombres[j]
        return f"{self.nombres[j]} (holgura de «{self.p['nom_res'][j - self.n]}»)"

    def _intro(self):
        texto = ("Punto de partida: las variables de decisión valen 0 y cada holgura (s) absorbe todo su "
                 "recurso, así que la solución inicial es el origen con Z = 0.")
        if self.signo == -1:
            texto += " Como se minimiza Z, el método trabaja con −Z (maximizar −Z es lo mismo)."
        return texto + " "

    def _explicar_pivote(self, entra, r, razones, candidatas, bland):
        motivo = ("es el único valor negativo de la fila Z" if len(candidatas) == 1 else
                  "se elige por la regla de Bland (menor índice) para evitar ciclos" if bland else
                  "es el más negativo de la fila Z")
        listado = "; ".join(
            f"{self.nombres[self.base[i]]}: {_p(self.T[i][-1])}/{_p(self.T[i][entra])} = {_t(razones[i])}"
            for i in range(self.m) if razones[i] is not None)
        minimo, sale = razones[r], self.base[r]
        empate = sum(1 for x in razones if x == minimo) > 1
        return " ".join([
            f"Entra {self._largo(entra)}: su zj − cj = {_t(self.Z[entra])} {motivo}, es decir, la variable "
            "que mejora Z.",
            f"Para saber hasta dónde puede crecer se divide cada LD entre el coeficiente positivo de su "
            f"columna: {listado}.",
            f"La menor razón es {_t(minimo)}, en la fila de {self._largo(sale)}: esa variable se agota primero "
            "y sale de la base." + (" Hay empate; se elige la de menor índice." if empate else ""),
            f"El pivote es {_t(self.T[r][entra])} (fila {self.nombres[sale]}, columna {self.nombres[entra]})."])

    def _explicar_optimo(self):
        valores = {self.nombres[j]: self.T[i][-1] for i, j in enumerate(self.base)}
        sol = ", ".join(f"{self.nombres[j]} = {_t(valores.get(self.nombres[j], 0))}" for j in range(self.n))
        return (f"Todos los valores de la fila Z son ≥ 0: ninguna variable que entre a la base puede mejorar Z, "
                f"así que esta tabla es óptima. Se lee la solución: {sol}; Z = {_t(self.signo * self.Z[-1])}.")

    def pivotear(self, r, c):
        piv = self.T[r][c]
        self.T[r] = [v / piv for v in self.T[r]]
        for i in range(self.m):
            if i != r and self.T[i][c] != 0:
                f = self.T[i][c]
                self.T[i] = [a - f * b for a, b in zip(self.T[i], self.T[r])]
        f = self.Z[c]
        self.Z = [a - f * b for a, b in zip(self.Z, self.T[r])]
        self.base[r] = c

    def iterar(self):
        """Devuelve ('optimo', None) o ('no_acotado', columna)."""
        for it in range(1, MAX_ITER + 1):
            candidatas = [j for j in range(self.n + self.m) if self.Z[j] < 0]
            intro = self._intro() if it == 1 else ""
            if not candidatas:
                self.foto("Tabla óptima", None, intro + self._explicar_optimo())
                return "optimo", None
            bland = it > ITER_BLAND
            entra = candidatas[0] if bland else min(candidatas, key=lambda j: (self.Z[j], j))
            razones = [self.T[i][-1] / self.T[i][entra] if self.T[i][entra] > 0 else None for i in range(self.m)]
            r = None
            for i, razon in enumerate(razones):
                if razon is not None and (r is None or razon < razones[r]
                                          or (razon == razones[r] and self.base[i] < self.base[r])):
                    r = i
            if r is None:
                texto = (f"{self._largo(entra)} tiene zj − cj = {_t(self.Z[entra])} < 0 (mejoraría Z), pero todos "
                         "los números de su columna son ≤ 0: ninguna razón lo limita, así que puede crecer "
                         "sin límite y Z no tiene tope.")
                self.foto(f"{self.nombres[entra]} puede crecer sin límite", None, intro + texto, razones)
                return "no_acotado", entra
            sale = self.base[r]
            etiqueta = ("Tabla inicial · " if it == 1 else f"Iteración {it - 1} · ") + \
                f"entra {self.nombres[entra]}, sale {self.nombres[sale]}"
            self.foto(etiqueta, (r, entra), intro + self._explicar_pivote(entra, r, razones, candidatas, bland),
                      razones)
            self.pivotear(r, entra)
        raise ValueError("Se superó el límite de iteraciones del método Simplex.")


def _sensibilidad(t: _Tabla, p):
    n, m = t.n, t.m
    resto = [j for j in range(n + m) if j not in t.base]
    sens_vars = []
    for j in range(n):
        if j in t.base:
            r = t.base.index(j)
            lo = hi = None
            for k in resto:
                a = t.T[r][k]
                if a > 0:
                    v = -t.Z[k] / a
                    lo = v if lo is None else max(lo, v)
                elif a < 0:
                    v = t.Z[k] / (-a)
                    hi = v if hi is None else min(hi, v)
            lo_i = None if lo is None else t.c[j] + lo
            hi_i = None if hi is None else t.c[j] + hi
            tipo = "básica"
        else:
            lo_i, hi_i, tipo = None, t.c[j] + t.Z[j], "no básica"
        if t.signo == 1:
            lo_o, hi_o = lo_i, hi_i
        else:
            lo_o = None if hi_i is None else -hi_i
            hi_o = None if lo_i is None else -lo_i
        sens_vars.append({"variable": p["nombres"][j], "tipo": tipo, "coeficiente": p["c"][j],
                          "minimo": lo_o, "maximo": hi_o, "costo_reducido": t.Z[j]})
    sens_res = []
    for i in range(m):
        col = n + i
        lo = hi = None
        for k in range(m):
            d, b = t.T[k][col], t.T[k][-1]
            if d > 0:
                v = -b / d
                lo = v if lo is None else max(lo, v)
            elif d < 0:
                v = b / (-d)
                hi = v if hi is None else min(hi, v)
        b0 = p["b"][i]
        # cuánto cambia cada variable de decisión por cada unidad extra de este recurso (columna de B⁻¹)
        efecto = [t.T[t.base.index(j)][col] if j in t.base else Fraction(0) for j in range(n)]
        sens_res.append({"restriccion": p["nom_res"][i], "rhs": b0,
                         "efecto_variables": efecto,
                         "precio_sombra": t.signo * t.Z[col],
                         "minimo": None if lo is None else b0 + lo,
                         "maximo": None if hi is None else b0 + hi})
    return sens_vars, sens_res


def _dual(t: _Tabla, p, x, holguras):
    """Dual del problema interno (max c'x, Ax <= b): min b·y, Aᵀy >= c', y >= 0.

    Sus valores salen de la tabla óptima: y_i es la fila Z bajo la holgura s_i y el exceso de cada
    restricción dual es el costo reducido zj − cj. Se comprueba además la dualidad fuerte (W* = Z')
    y las holguras complementarias (x_j·exceso_j = 0 y y_i·holgura_i = 0).
    """
    n, m = t.n, t.m
    y = [t.Z[n + i] for i in range(m)]
    excesos = [t.Z[j] for j in range(n)]
    w = sum((p["b"][i] * y[i] for i in range(m)), Fraction(0))

    def lineal(coefs, nombres):
        partes = [f"{_t(a)}·{nom}" for a, nom in zip(coefs, nombres) if a != 0]
        return " + ".join(partes).replace("+ −", "− ") or "0"

    nom_y = [f"y{i + 1}" for i in range(m)]
    primal = ["max Z' = " + lineal(t.c, p["nombres"]), "s.a."]
    primal += [f"   {lineal(p['A'][i], p['nombres'])}  ≤  {_t(p['b'][i])}" for i in range(m)]
    primal.append("   " + ", ".join(p["nombres"]) + " ≥ 0")
    dual = ["min W = " + lineal(p["b"], nom_y), "s.a."]
    dual += [f"   {lineal([p['A'][i][j] for i in range(m)], nom_y)}  ≥  {_t(t.c[j])}" for j in range(n)]
    dual.append("   " + ", ".join(nom_y) + " ≥ 0")
    z_interna = sum((t.c[j] * x[j] for j in range(n)), Fraction(0))
    return {
        "primal_modelo": primal, "dual_modelo": dual, "w": w, "signo": t.signo,
        "fuerte": w == z_interna,
        "y": [{"nombre": f"y{i + 1}", "recurso": p["nom_res"][i], "valor": y[i], "holgura": holguras[i],
               "complementaria": y[i] * holguras[i] == 0} for i in range(m)],
        "restricciones": [{"variable": p["nombres"][j], "x": x[j], "exceso": excesos[j],
                           "complementaria": x[j] * excesos[j] == 0} for j in range(n)],
    }


def resolver(payload):
    """Resuelve el problema y devuelve un diccionario listo para convertir a JSON."""
    from .simplex_interpretacion import interpretar   # import tardío: evita ciclo de módulos

    p = validar(payload)
    t = _Tabla(p)
    estado, columna = t.iterar()
    res = {"estado": estado, "sentido": p["sentido"], "unidad_z": p["unidad_z"],
           "contexto": p["contexto"], "iterations": t.historial, "problema": p,
           "modelo": ("Simplex normal sobre max Z." if p["sentido"] == "max"
                      else "Simplex normal sobre max(−Z): se minimiza Z maximizando su negativo.")}
    if estado == "optimo":
        valores = [Fraction(0)] * (t.n + t.m)
        for i, j in enumerate(t.base):
            valores[j] = t.T[i][-1]
        res["z"] = t.signo * t.Z[-1]
        res["x"] = valores[:t.n]
        res["holguras"] = valores[t.n:]
        res["degenerado"] = any(t.T[i][-1] == 0 for i in range(t.m))
        res["optimos_multiples"] = any(t.Z[j] == 0 for j in range(t.n + t.m) if j not in t.base)
        res["sens_variables"], res["sens_restricciones"] = _sensibilidad(t, p)
        res["dual"] = _dual(t, p, res["x"], res["holguras"])
    else:
        res["variable_no_acotada"] = t.nombres[columna]
    res["interpretacion"] = interpretar(res)
    return _a_json(res)


def _a_json(res):
    """Convierte Fractions a float y quita el diccionario interno del problema."""
    def conv(v):
        if isinstance(v, Fraction):
            return _flotante(v)
        if isinstance(v, list):
            return [conv(i) for i in v]
        if isinstance(v, dict):
            return {k: conv(i) for k, i in v.items()}
        return v
    p = res.pop("problema")
    res["variables"] = [{"nombre": n, "unidad": u} for n, u in zip(p["nombres"], p["unidades"])]
    res["restricciones"] = [{"nombre": n, "unidad": u, "rhs": b}
                            for n, u, b in zip(p["nom_res"], p["uni_res"], p["b"])]
    return conv(res)
