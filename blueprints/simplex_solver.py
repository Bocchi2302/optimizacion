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

    def foto(self, etiqueta, pivote=None):
        filas = [[_flotante(v) for v in fila] for fila in self.T] + [[_flotante(v) for v in self.Z]]
        self.historial.append({
            "label": etiqueta,
            "columns": self.nombres + ["LD"],
            "basis": [self.nombres[j] for j in self.base],
            "rows": filas,
            "pivot": list(pivote) if pivote else None,
        })

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
            if not candidatas:
                self.foto("Tabla óptima")
                return "optimo", None
            entra = candidatas[0] if it > ITER_BLAND else min(candidatas, key=lambda j: (self.Z[j], j))
            r = None
            mejor = None
            for i in range(self.m):
                a = self.T[i][entra]
                if a > 0:
                    razon = self.T[i][-1] / a
                    if mejor is None or razon < mejor or (razon == mejor and self.base[i] < self.base[r]):
                        mejor, r = razon, i
            if r is None:
                self.foto(f"{self.nombres[entra]} puede crecer sin límite", None)
                return "no_acotado", entra
            sale = self.base[r]
            etiqueta = ("Tabla inicial · " if it == 1 else f"Iteración {it - 1} · ") + \
                f"entra {self.nombres[entra]}, sale {self.nombres[sale]}"
            self.foto(etiqueta, (r, entra))
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
        sens_res.append({"restriccion": p["nom_res"][i], "rhs": b0,
                         "precio_sombra": t.signo * t.Z[col],
                         "minimo": None if lo is None else b0 + lo,
                         "maximo": None if hi is None else b0 + hi})
    return sens_vars, sens_res


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
