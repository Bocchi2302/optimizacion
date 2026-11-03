from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request

vogel_bp = Blueprint("vogel_bp", __name__)
MAX_DIMENSION = 10


def resolver_vogel(costos, oferta, demanda):
    """Calcula una solución inicial factible usando el método de Vogel."""
    filas = len(oferta)
    columnas = len(demanda)
    if filas == 0 or columnas == 0:
        raise ValueError("La tabla debe tener al menos un origen y un destino.")
    if len(costos) != filas or any(len(fila) != columnas for fila in costos):
        raise ValueError("Las dimensiones de costos, oferta y demanda no coinciden.")
    if any(valor < 0 for valor in oferta) or any(valor < 0 for valor in demanda):
        raise ValueError("La oferta y la demanda no pueden ser negativas.")

    costos = [fila[:] for fila in costos]
    oferta_restante = oferta[:]
    demanda_restante = demanda[:]
    nombres_origen = [f"Origen {i + 1}" for i in range(filas)]
    nombres_destino = [f"Destino {j + 1}" for j in range(columnas)]

    total_oferta = sum(oferta_restante, Decimal(0))
    total_demanda = sum(demanda_restante, Decimal(0))
    if total_oferta < total_demanda:
        costos.append([Decimal(0)] * columnas)
        oferta_restante.append(total_demanda - total_oferta)
        nombres_origen.append("Origen ficticio")
    elif total_oferta > total_demanda:
        costos = [fila + [Decimal(0)] for fila in costos]
        demanda_restante.append(total_oferta - total_demanda)
        nombres_destino.append("Destino ficticio")

    asignaciones = [
        [Decimal(0) for _ in demanda_restante] for _ in oferta_restante
    ]
    pasos = []

    while True:
        filas_activas = [
            i for i, cantidad in enumerate(oferta_restante) if cantidad > 0
        ]
        columnas_activas = [
            j for j, cantidad in enumerate(demanda_restante) if cantidad > 0
        ]
        if not filas_activas or not columnas_activas:
            break

        candidatos = []
        for tipo, indices, indice_opuesto in (
            ("origen", filas_activas, columnas_activas),
            ("destino", columnas_activas, filas_activas),
        ):
            for indice in indices:
                celdas = (
                    [(indice, j) for j in indice_opuesto]
                    if tipo == "origen"
                    else [(i, indice) for i in indice_opuesto]
                )
                ordenadas = sorted(costos[i][j] for i, j in celdas)
                penalizacion = (
                    ordenadas[1] - ordenadas[0]
                    if len(ordenadas) > 1
                    else ordenadas[0]
                )
                costo_minimo = ordenadas[0]
                celdas_minimas = [
                    (i, j) for i, j in celdas if costos[i][j] == costo_minimo
                ]
                mejor_celda = min(
                    celdas_minimas,
                    key=lambda celda: (
                        -min(
                            oferta_restante[celda[0]],
                            demanda_restante[celda[1]],
                        ),
                        celda,
                    ),
                )
                candidatos.append(
                    (
                        penalizacion,
                        -costo_minimo,
                        min(
                            oferta_restante[mejor_celda[0]],
                            demanda_restante[mejor_celda[1]],
                        ),
                        1 if tipo == "origen" else 0,
                        tipo,
                        indice,
                        mejor_celda,
                    )
                )

        _, _, _, _, tipo, indice, (i, j) = max(candidatos)
        cantidad = min(oferta_restante[i], demanda_restante[j])
        asignaciones[i][j] += cantidad
        oferta_restante[i] -= cantidad
        demanda_restante[j] -= cantidad
        pasos.append(
            {
                "numero": len(pasos) + 1,
                "tipo": tipo,
                "indice": indice + 1,
                "origen": nombres_origen[i],
                "destino": nombres_destino[j],
                "cantidad": cantidad,
                "costo_unitario": costos[i][j],
            }
        )

    costo_total = sum(
        (
            asignaciones[i][j] * costos[i][j]
            for i in range(len(asignaciones))
            for j in range(len(asignaciones[i]))
        ),
        Decimal(0),
    )
    return {
        "costos": costos,
        "asignaciones": asignaciones,
        "origenes": nombres_origen,
        "destinos": nombres_destino,
        "pasos": pasos,
        "costo_total": costo_total,
        "oferta_total": total_oferta,
        "demanda_total": total_demanda,
    }


def _decimal_formulario(nombre, etiqueta):
    valor = request.form.get(nombre, "").strip()
    try:
        numero = Decimal(valor)
    except (InvalidOperation, ValueError):
        raise ValueError(f"El campo «{etiqueta}» debe contener un número válido.")
    if not numero.is_finite():
        raise ValueError(f"El campo «{etiqueta}» debe ser un número finito.")
    return numero


def _dimension_formulario(nombre, predeterminado):
    try:
        dimension = int(request.form.get(nombre, predeterminado))
    except (TypeError, ValueError):
        raise ValueError("La cantidad de orígenes y destinos debe ser entera.")
    if not 1 <= dimension <= MAX_DIMENSION:
        raise ValueError(
            f"La cantidad de orígenes y destinos debe estar entre 1 y {MAX_DIMENSION}."
        )
    return dimension


@vogel_bp.route("/", methods=["GET", "POST"])
def vista_principal():
    filas = columnas = 2
    resultados = error = None

    if request.method == "POST":
        try:
            filas = _dimension_formulario("num_origenes", 2)
            columnas = _dimension_formulario("num_destinos", 2)
            costos = [
                [
                    _decimal_formulario(
                        f"costo_{i}_{j}",
                        f"costo del origen {i + 1} al destino {j + 1}",
                    )
                    for j in range(columnas)
                ]
                for i in range(filas)
            ]
            oferta = [
                _decimal_formulario(f"oferta_{i}", f"oferta del origen {i + 1}")
                for i in range(filas)
            ]
            demanda = [
                _decimal_formulario(f"demanda_{j}", f"demanda del destino {j + 1}")
                for j in range(columnas)
            ]
            resultados = resolver_vogel(costos, oferta, demanda)
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "metodo_vogel/resolucion.html",
        resultados=resultados,
        error=error,
        filas=filas,
        columnas=columnas,
        max_dimension=MAX_DIMENSION,
    )
