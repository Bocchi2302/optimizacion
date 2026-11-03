"""Módulo del Simplex normal (restricciones ≤, variables de holgura)."""
from flask import Blueprint, jsonify, render_template, request

from .simplex_solver import MAX_RESTRICCIONES, MAX_VARIABLES, resolver

simplex_bp = Blueprint("simplex_bp", __name__)


@simplex_bp.get("/")
def vista_principal():
    return render_template("simplex/index.html", max_variables=MAX_VARIABLES,
                           max_restricciones=MAX_RESTRICCIONES)


@simplex_bp.post("/api/simplex")
def calcular():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Envía un JSON con el problema."}), 400
    try:
        return jsonify(resolver(payload))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
