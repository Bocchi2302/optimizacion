"""Módulo de regresión lineal minimax por Simplex de dos fases."""
from flask import Blueprint, jsonify, render_template, request

from .regresion_solver import regress

regresion_bp = Blueprint("regresion_bp", __name__)


@regresion_bp.get("/")
def vista_principal():
    return render_template("regresion/index.html")


@regresion_bp.post("/api/regression")
def calcular():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Envía un JSON con la lista 'points'."}), 400
    try:
        return jsonify(regress(payload.get("points")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
