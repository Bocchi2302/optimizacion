"""Método de las Dos Fases: Blueprint, rutas y recepción de datos.

Sigue la convención de los demás módulos: `dos_fases_bp` se registra en app.py,
la vista principal es `vista_principal`, el procedimiento matemático vive en
`dos_fases_solver.py`, la plantilla en `templates/metodo_dos_fases/index.html`
y los recursos en `static/css/dos_fases.css` y `static/js/dos_fases.js`.

Aquí solo hay presentación (el formato de los números y el informe descargable);
ningún resultado matemático se calcula en este archivo.
"""
import base64
import re
from pathlib import Path

from flask import (Blueprint, Response, current_app, get_template_attribute, jsonify,
                   render_template, request)

from .dos_fases_solver import EXAMPLES, ModelError, solve

dos_fases_bp = Blueprint("dos_fases_bp", __name__)

PLANTILLA = "metodo_dos_fases/index.html"
MAX_BYTES = 100_000
_MENOS = re.compile(r"(?<![A-Za-z0-9)])-(?=[\d(])")
_FUENTES_INFORME = (("DF Atkinson", 400, "atkinson-hyperlegible-latin-400-normal.woff2"),
                    ("DF Atkinson", 700, "atkinson-hyperlegible-latin-700-normal.woff2"),
                    ("DF Fraunces", 600, "fraunces-latin-600-normal.woff2"),
                    ("DF Mono", 500, "jetbrains-mono-latin-500-normal.woff2"))


def fmt(valor):
    """Muestra el signo menos tipográfico (−) en números y cálculos; no altera los datos."""
    return _MENOS.sub("−", str(valor)) if valor is not None else ""


def _css_autonomo():
    """CSS del módulo con las fuentes mínimas incrustadas, para un informe sin recursos externos."""
    estatica = Path(current_app.static_folder)
    css = (estatica / "css" / "dos_fases.css").read_text(encoding="utf-8")
    css = re.sub(r"@font-face\{[^}]*\}", "", css)  # las rutas relativas no existen fuera del servidor
    caras = ""
    for familia, peso, nombre in _FUENTES_INFORME:
        datos = base64.b64encode((estatica / "fonts" / "dos_fases" / nombre).read_bytes()).decode("ascii")
        caras += (f'@font-face{{font-family:"{familia}";font-weight:{peso};font-style:normal;'
                  f'src:url(data:font/woff2;base64,{datos}) format("woff2")}}')
    return caras + css


def _calcular_solicitud():
    if request.content_length and request.content_length > MAX_BYTES:
        return None, (jsonify(error="El modelo supera el tamaño permitido (100 kB)."), 413)
    datos = request.get_json(silent=True)
    try:
        return solve(datos), None
    except ModelError as exc:
        return None, (jsonify(error=str(exc), field=getattr(exc, "field", None)), 400)


def _informe(resultado, autonomo=False):
    informe = get_template_attribute(PLANTILLA, "informe")
    return str(informe(resultado, fmt, autonomo, _css_autonomo() if autonomo else ""))


@dos_fases_bp.get("/")
def vista_principal():
    return render_template(PLANTILLA, examples=EXAMPLES)


@dos_fases_bp.post("/api/resolver")
def calcular():
    resultado, error = _calcular_solicitud()
    if error:
        return error
    return jsonify(**resultado, html=_informe(resultado))


@dos_fases_bp.post("/informe")
def descargar_informe():
    resultado, error = _calcular_solicitud()
    if error:
        return error
    return Response(_informe(resultado, autonomo=True), content_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="informe_dos_fases.html"'})
