"""Operación módulo con enteros y residuo euclídeo no negativo."""

import re

from flask import Blueprint, jsonify, render_template, request


mod_bp = Blueprint(
    'mod_bp', __name__,
    static_folder='../templates/metodo_mod/assets', static_url_path='/assets',
)
MAX_DIGITOS = 200


def _entero(valor, nombre):
    # Rechazar booleanos, decimales y notación científica sin redondear datos.
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ValueError(f'{nombre} debe ser un número entero.')
    texto = str(valor).strip()
    if not re.fullmatch(r'[+-]?[0-9]+', texto):
        raise ValueError(f'{nombre} debe ser un número entero.')
    if len(texto.lstrip('+-')) > MAX_DIGITOS:
        raise ValueError(f'{nombre} admite hasta {MAX_DIGITOS} dígitos.')
    return int(texto)


def calcular_mod(dividendo, divisor):
    """Devuelve a = b*q + r, con 0 <= r < abs(b), usando enteros exactos.

    Las cadenas en la respuesta conservan la precisión en el navegador,
    incluso para valores mayores que Number.MAX_SAFE_INTEGER.
    """
    a = _entero(dividendo, 'El dividendo')
    b = _entero(divisor, 'El divisor')
    if b == 0:
        raise ValueError('El divisor no puede ser cero.')
    q, r = divmod(a, abs(b))
    if b < 0:
        q = -q
    return {
        'dividendo': str(a), 'divisor': str(b),
        'cociente': str(q), 'residuo': str(r),
        'divisible': r == 0, 'par': a % 2 == 0,
    }


@mod_bp.get('/')
def vista_principal():
    return render_template('metodo_mod/index.html')


@mod_bp.post('/calcular')
def calcular():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error='Envía un objeto JSON con dividendo y divisor.'), 400
    try:
        resultado = calcular_mod(datos.get('dividendo'), datos.get('divisor'))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(resultado)
