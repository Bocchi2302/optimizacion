"""Blueprint para el Método MOD / MODI (Distribución Modificada)."""

import re
from flask import Blueprint, jsonify, render_template, request

from blueprints.mod_solver import resolver_metodo_mod

mod_bp = Blueprint(
    "mod_bp",
    __name__,
    static_folder="../templates/metodo_mod/assets",
    static_url_path="/assets",
)
MAX_DIGITOS = 200
MAX_DIMENSION = 10


def _entero(valor, nombre):
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ValueError(f"{nombre} debe ser un número entero.")
    texto = str(valor).strip()
    if not re.fullmatch(r"[+-]?[0-9]+", texto):
        raise ValueError(f"{nombre} debe ser un número entero.")
    if len(texto.lstrip("+-")) > MAX_DIGITOS:
        raise ValueError(f"{nombre} admite hasta {MAX_DIGITOS} dígitos.")
    return int(texto)


def calcular_mod(dividendo, divisor):
    """Devuelve a = b*q + r, con 0 <= r < abs(b), usando enteros exactos."""
    a = _entero(dividendo, "El dividendo")
    b = _entero(divisor, "El divisor")
    if b == 0:
        raise ValueError("El divisor no puede ser cero.")
    q, r = divmod(a, abs(b))
    if b < 0:
        q = -q
    return {
        "dividendo": str(a),
        "divisor": str(b),
        "cociente": str(q),
        "residuo": str(r),
        "divisible": r == 0,
        "par": a % 2 == 0,
    }


def _dimension_formulario(nombre, predeterminado):
    try:
        val = int(request.form.get(nombre, predeterminado))
    except (TypeError, ValueError):
        val = predeterminado
    return max(1, min(val, MAX_DIMENSION))


@mod_bp.route("/", methods=["GET", "POST"])
def vista_principal():
    filas = 3
    columnas = 3
    tipo_opt = "max"
    contexto = ""
    resultados = None
    error = None

    if request.method == "POST":
        try:
            contexto = request.form.get("contexto", "").strip()
            tipo_opt = request.form.get("tipo_opt", "max")
            if tipo_opt not in ("max", "min"):
                tipo_opt = "max"

            filas = _dimension_formulario("num_origenes", 3)
            columnas = _dimension_formulario("num_destinos", 3)

            costos = [
                [
                    request.form.get(f"costo_{i}_{j}", "").strip()
                    for j in range(columnas)
                ]
                for i in range(filas)
            ]
            oferta = [
                request.form.get(f"oferta_{i}", "").strip()
                for i in range(filas)
            ]
            demanda = [
                request.form.get(f"demanda_{j}", "").strip()
                for j in range(columnas)
            ]

            nombres_o = [
                request.form.get(f"nombre_origen_{i}", f"Origen {i + 1}").strip()
                or f"Origen {i + 1}"
                for i in range(filas)
            ]
            nombres_d = [
                request.form.get(f"nombre_destino_{j}", f"Destino {j + 1}").strip()
                or f"Destino {j + 1}"
                for j in range(columnas)
            ]

            resultados = resolver_metodo_mod(
                costos_raw=costos,
                oferta_raw=oferta,
                demanda_raw=demanda,
                tipo_opt=tipo_opt,
                contexto=contexto,
                nombres_origenes=nombres_o,
                nombres_destinos=nombres_d,
            )
        except Exception as exc:
            error = str(exc)

    return render_template(
        "metodo_mod/index.html",
        resultados=resultados,
        error=error,
        contexto=contexto,
        tipo_opt=tipo_opt,
        filas=filas,
        columnas=columnas,
        max_dimension=MAX_DIMENSION,
    )


@mod_bp.post("/calcular")
def calcular():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="Envía un objeto JSON válido."), 400

    # Compatibilidad con pruebas previas si incluye dividendo y divisor
    if "dividendo" in datos and "divisor" in datos:
        try:
            resultado = calcular_mod(datos.get("dividendo"), datos.get("divisor"))
            return jsonify(resultado)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    # Soporte API para resolver problemas de transporte con MOD
    try:
        resultado = resolver_metodo_mod(
            costos_raw=datos.get("costos", []),
            oferta_raw=datos.get("oferta", []),
            demanda_raw=datos.get("demanda", []),
            tipo_opt=datos.get("tipo_opt", "max"),
            contexto=datos.get("contexto", ""),
            nombres_origenes=datos.get("nombres_origenes"),
            nombres_destinos=datos.get("nombres_destinos"),
        )
        return jsonify(resultado)
    except Exception as exc:
        return jsonify(error=str(exc)), 400
