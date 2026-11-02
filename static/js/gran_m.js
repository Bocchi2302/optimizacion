// static/js/gran_m.js
(function () {
    'use strict';

    const OPCIONES_MATH = {
        delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false }
        ],
        throwOnError: false
    };

    // Datos generados por Python: lista de pasos con títulos, explicaciones, tablas y pivote
    const pasos = JSON.parse(document.getElementById('datos-pasos').textContent);
    let indiceActual = 0;

    const elementos = {
        visor: document.getElementById('visor'),
        titulo: document.getElementById('titulo-paso'),
        indicador: document.getElementById('indicador'),
        progreso: document.getElementById('progreso-relleno'),
        explicacion: document.getElementById('explicacion'),
        formulas: document.getElementById('formulas'),
        tablaPrincipal: document.getElementById('tabla-principal'),
        tablaResultado: document.getElementById('tabla-resultado'),
        anterior: document.getElementById('btn-anterior'),
        siguiente: document.getElementById('btn-siguiente')
    };

    function renderizarMath(elemento) {
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(elemento, OPCIONES_MATH);
        }
    }

    // Construye una tabla Simplex y aplica las clases de resaltado del pivote
    function crearTabla(datos, pivote, etiqueta) {
        const bloque = document.createElement('div');
        bloque.className = 'bloque-tabla';

        if (etiqueta) {
            const titulo = document.createElement('h4');
            titulo.textContent = etiqueta;
            bloque.appendChild(titulo);
        }

        const envoltorio = document.createElement('div');
        envoltorio.className = 'tabla-envoltorio';

        const tabla = document.createElement('table');
        tabla.className = 'tabla-simplex';

        // Encabezado: la columna 0 es "Base"; las columnas de datos van desde la 1
        const encabezado = tabla.createTHead().insertRow();
        ['Base'].concat(datos.columnas).forEach(function (texto, j) {
            const th = document.createElement('th');
            th.textContent = texto;
            if (pivote && j - 1 === pivote.columna) {
                th.classList.add('columna-pivote');
            }
            encabezado.appendChild(th);
        });

        // Cuerpo: fila i (0 = Z) y columna j (0 = Z, ..., 7 = Solución)
        const cuerpo = tabla.createTBody();
        datos.filas.forEach(function (fila, i) {
            const tr = cuerpo.insertRow();
            if (pivote && i === pivote.fila) {
                tr.classList.add('fila-pivote');
            }

            const celdaBase = tr.insertCell();
            celdaBase.textContent = fila.base;
            celdaBase.className = 'celda-base';

            fila.celdas.forEach(function (valor, j) {
                const td = tr.insertCell();
                td.textContent = valor;
                if (pivote && j === pivote.columna) {
                    td.classList.add('columna-pivote');
                }
                if (pivote && i === pivote.fila && j === pivote.columna) {
                    td.classList.add('elemento-pivote');
                }
            });
        });

        envoltorio.appendChild(tabla);
        bloque.appendChild(envoltorio);
        return bloque;
    }

    function mostrarPaso() {
        const paso = pasos[indiceActual];

        elementos.indicador.textContent = `Paso ${indiceActual + 1} de ${pasos.length}`;
        elementos.progreso.style.width = `${((indiceActual + 1) / pasos.length) * 100}%`;
        elementos.titulo.textContent = paso.titulo;
        elementos.explicacion.innerHTML = paso.explicacion;

        elementos.formulas.innerHTML = '';
        paso.formulas.forEach(function (texto) {
            const div = document.createElement('div');
            div.className = 'formula';
            div.textContent = texto;
            elementos.formulas.appendChild(div);
        });

        elementos.tablaPrincipal.innerHTML = '';
        elementos.tablaResultado.innerHTML = '';

        if (paso.tabla) {
            const etiqueta = paso.tabla_resultado ? 'Tabla antes del pivoteo' : null;
            elementos.tablaPrincipal.appendChild(crearTabla(paso.tabla, paso.pivote, etiqueta));
        }
        if (paso.tabla_resultado) {
            elementos.tablaResultado.appendChild(
                crearTabla(paso.tabla_resultado, null, 'Tabla después del pivoteo')
            );
        }

        elementos.anterior.disabled = indiceActual === 0;
        elementos.siguiente.disabled = indiceActual === pasos.length - 1;

        renderizarMath(elementos.visor);
    }

    function irAnterior() {
        if (indiceActual > 0) {
            indiceActual--;
            mostrarPaso();
        }
    }

    function irSiguiente() {
        if (indiceActual < pasos.length - 1) {
            indiceActual++;
            mostrarPaso();
        }
    }

    elementos.anterior.addEventListener('click', irAnterior);
    elementos.siguiente.addEventListener('click', irSiguiente);

    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'ArrowRight') {
            irSiguiente();
        } else if (evento.key === 'ArrowLeft') {
            irAnterior();
        }
    });

    // Agrega una fila de restricción clonando la plantilla del HTML
    const btnAgregar = document.getElementById('btn-agregar-restriccion');
    if (btnAgregar) {
        btnAgregar.addEventListener('click', function () {
            const plantilla = document.getElementById('plantilla-restriccion');
            const contenedor = document.getElementById('restricciones-container');
            contenedor.appendChild(plantilla.content.cloneNode(true));
        });
    }

    // Renderiza las fórmulas de la teoría y arranca el visor solo si hay resultados
    renderizarMath(document.body);
    if (pasos.length > 0) {
        mostrarPaso();
    }
})();
