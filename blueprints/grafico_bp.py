# blueprints/grafico_bp.py
import gzip

from flask import Blueprint, jsonify, render_template, request

from .grafico_conclusion import redactar
from .grafico_extractor import ErrorExtraccion, extraer
from .grafico_plot import clave_punto, color_de, graficar
from .grafico_solver import (
    SIMBOLO, EntradaInvalida, expresion, fmt, fmt_exacto, leer_problema,
    resolver, cortes_con_ejes,
)

grafico_bp = Blueprint('grafico_bp', __name__)

FILAS_POR_DEFECTO = 2


def _formulario_vacio():
    return {
        'tipo_opt': 'max', 'z_x': '', 'z_y': '', 'z_k': '', 'contexto': '',
        'nombre_x1': '', 'nombre_x2': '', 'objetivo_nombre': '', 'extraccion': '',
        'filas': [{'x': '', 'y': '', 'op': '<=', 'c': '', 'n': ''} for _ in range(FILAS_POR_DEFECTO)],
    }


def _formulario_enviado(form):
    """Conserva lo que escribió la persona para no obligarla a repetirlo."""
    rotulos = form.getlist('r_n[]')
    filas = [
        {'x': x, 'y': y, 'op': op, 'c': c, 'n': rotulos[i] if i < len(rotulos) else ''}
        for i, (x, y, op, c) in enumerate(zip(
            form.getlist('r_x[]'), form.getlist('r_y[]'),
            form.getlist('r_op[]'), form.getlist('r_c[]'),
        ))
    ]
    return {
        'tipo_opt': form.get('tipo_opt', 'max'),
        'z_x': form.get('z_x', ''), 'z_y': form.get('z_y', ''), 'z_k': form.get('z_k', ''),
        'nombre_x1': form.get('nombre_x1', ''), 'nombre_x2': form.get('nombre_x2', ''),
        'extraccion': form.get('extraccion', ''),
        'objetivo_nombre': form.get('objetivo_nombre', ''),
        'contexto': form.get('contexto', ''),
        'filas': filas or _formulario_vacio()['filas'],
    }


def _termino(coef, valor):
    return f'{fmt(coef)}·({fmt(valor)})'


def _calculo_z(sol, e):
    """'3·(2) + 2·(4) = 14' con los signos bien escritos."""
    texto = f'{_termino(sol["zx"], e["x"])} + {_termino(sol["zy"], e["y"])}'
    if sol['zk']:
        texto += f' + {fmt(sol["zk"])}'
    return f'{texto.replace("+ -", "− ")} = {fmt(e["z"])}'


def _info_recta(sol, r, indice):
    c1, c2 = cortes_con_ejes(r)
    if r.c != 0:
        punto, etiqueta = (0, 0), 'el origen (0, 0)'
    elif r.a != 0:
        punto, etiqueta = (1, 0), 'el punto (1, 0)'
    else:
        punto, etiqueta = (0, 1), 'el punto (0, 1)'
    valor = r.valor(*punto)
    return {
        'recta': r, 'color': color_de(indice), 'indice': indice,
        'figura': graficar(sol, 'semiplano', solo=indice,
                           descripcion=f'{r.nombre}: {r.texto}'),
        'corte_x1': c1, 'corte_x2': c2,
        'prueba': etiqueta, 'valor_prueba': valor,
        'prueba_cumple': r.cumple(*punto),
    }


def _pasos(sol):
    """Lista ordenada (id, título) de los pasos que aplican a este problema."""
    pasos = [('planteamiento', 'Plantear el modelo'),
             ('rectas', 'Convertir las restricciones en rectas'),
             ('semiplanos', 'Decidir hacia qué lado es factible cada una'),
             ('region', 'Marcar la región factible')]
    if sol['factible']:
        pasos += [('vertices', 'Hallar los vértices de la región'),
                  ('evaluacion', 'Evaluar Z en cada vértice')]
        pasos.append(('optimo', 'Elegir el valor óptimo'
                      if sol['estado'] == 'optimo' else 'Revisar si Z tiene límite'))
    pasos.append(('respuesta', 'Conclusión'))
    return pasos


def _contexto_resultado(sol):
    figuras = {}
    for etapa in ('rectas', 'semiplanos', 'region', 'vertices', 'optimo'):
        if etapa == 'region' or sol['rectas']:
            figuras[etapa] = graficar(sol, etapa)
    for e in sol['vertices']:
        e['calculo'] = _calculo_z(sol, e)
        e['clave'] = clave_punto(e['x'], e['y'])
    pasos = _pasos(sol)
    return {
        'sol': sol,
        'conclusion': redactar(sol),
        'figuras': figuras,
        'pasos': pasos,
        'numero': {pid: n for n, (pid, _) in enumerate(pasos, start=1)},
        'info_rectas': [_info_recta(sol, r, i) for i, r in enumerate(sol['rectas'])],
        'forma_region': _forma_region(sol),
    }


def _forma_region(sol):
    n = len(sol['vertices'])
    if not sol['factible']:
        return 'vacía'
    if not sol['acotada']:
        return 'no acotada'
    return {1: 'un único punto', 2: 'un segmento'}.get(n, f'un polígono de {n} vértices')


@grafico_bp.route('/', methods=['GET', 'POST'])
def vista_principal():
    contexto = {
        'form': _formulario_vacio(), 'error': None, 'resultado': None,
        'fmt': fmt, 'fmt_exacto': fmt_exacto, 'expresion': expresion,
        'SIMBOLO': SIMBOLO, 'color_de': color_de, 'clave_punto': clave_punto,
    }

    # POST: el formulario. GET con datos (?z_x=…&r_x[]=…): un enlace compartido que abre el ejercicio resuelto.
    datos = request.form if request.method == 'POST' else (
        request.args if 'z_x' in request.args else None)
    if datos is not None:
        contexto['form'] = _formulario_enviado(datos)
        try:
            problema = leer_problema(datos)
            sol = resolver(problema)
            contexto['resultado'] = _contexto_resultado(sol)
        except EntradaInvalida as exc:
            contexto['error'] = str(exc)

    return render_template('metodo_grafico/resolucion.html', **contexto)


@grafico_bp.route('/extraer', methods=['POST'])
def extraer_datos():
    """Lee un enunciado y devuelve variables, objetivo y restricciones en JSON."""
    datos = request.get_json(silent=True) or {}
    try:
        resultado = extraer(datos.get('texto'))
    except ErrorExtraccion as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 200
    except Exception:  # un fallo inesperado no debe romper la página
        return jsonify({'ok': False, 'error': 'No pude leer el enunciado por un error interno. Escribe los datos a mano.'}), 200
    return jsonify(resultado)


@grafico_bp.after_request
def _comprimir(respuesta):
    """Comprime (gzip) las respuestas de esta sección: la página de resultados pesa ~170 KB y baja a ~20 KB."""
    if (respuesta.direct_passthrough or respuesta.status_code != 200 or 'Content-Encoding' in respuesta.headers
            or 'gzip' not in request.headers.get('Accept-Encoding', '')
            or not respuesta.mimetype.startswith(('text/', 'application/json'))):
        return respuesta
    datos = respuesta.get_data()
    if len(datos) < 1024:
        return respuesta
    respuesta.set_data(gzip.compress(datos, compresslevel=6))
    respuesta.headers['Content-Encoding'] = 'gzip'
    respuesta.headers['Content-Length'] = str(len(respuesta.get_data()))
    respuesta.headers.add('Vary', 'Accept-Encoding')
    return respuesta
