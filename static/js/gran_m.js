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

    const movimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

    function renderizarMath(elemento) {
        if (typeof renderMathInElement === 'function') {
            renderMathInElement(elemento, OPCIONES_MATH);
        }
    }

    function renderizarTex(elemento, tex) {
        if (window.katex) {
            window.katex.render(tex, elemento, { throwOnError: false });
        } else {
            elemento.textContent = tex;
        }
    }

    // ── Números: acepta lo mismo que el servidor (2, 1.5, 1,5, 1/3, -2) ──────────
    const PATRON_DECIMAL = /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?$/;
    const PATRON_FRACCION = /^[+-]?\d+\/\d+$/;

    function leerNumero(texto) {
        const limpio = texto.trim();
        if (PATRON_FRACCION.test(limpio)) {
            const partes = limpio.split('/').map(Number);
            return partes[1] === 0 ? null : partes[0] / partes[1];
        }
        return PATRON_DECIMAL.test(limpio) ? Number(limpio.replace(',', '.')) : null;
    }

    function magnitudTex(texto) {
        const limpio = texto.trim().replace(/^[+-]/, '').replace(',', '.');
        if (limpio.includes('/')) {
            const partes = limpio.split('/');
            return `\\frac{${partes[0]}}{${partes[1]}}`;
        }
        return limpio;
    }

    function variableTex(nombre) {
        return nombre.replace(/^([A-Za-z])(\d+)$/, '$1_{$2}');
    }

    // Arma "2x_{1} - x_{2}" desde los campos; un campo incompleto se ve como un cuadro vacío
    function expresionTex(campos) {
        let salida = '';
        campos.forEach(function (campo) {
            const valor = leerNumero(campo.value);
            const variable = variableTex(campo.dataset.var);
            if (valor === 0) {
                return;
            }
            if (valor === null) {
                salida += `${salida ? ' + ' : ''}\\square\\,${variable}`;
                return;
            }
            const coeficiente = Math.abs(valor) === 1 ? '' : magnitudTex(campo.value);
            const signo = valor < 0 ? '-' : '+';
            salida += salida
                ? ` ${signo} ${coeficiente}${variable}`
                : `${valor < 0 ? '-' : ''}${coeficiente}${variable}`;
        });
        return salida || '0';
    }

    function ladoDerechoTex(campo) {
        const valor = leerNumero(campo.value);
        if (valor === null) {
            return '\\square';
        }
        return `${valor < 0 ? '-' : ''}${magnitudTex(campo.value)}`;
    }

    // ── Formulario ───────────────────────────────────────────────────────────────
    function iniciarFormulario() {
        const formEnunciado = document.getElementById('form-enunciado');
        const formModelo = document.getElementById('form-modelo');
        const campoContexto = document.getElementById('campo-contexto');
        const errorContexto = document.getElementById('error-contexto');
        const textosOriginales = new Map();

        function huellaActual() {
            const datos = formModelo ? new URLSearchParams(new FormData(formModelo)).toString() : '';
            return `${campoContexto.value}|${datos}`;
        }

        // Evita el doble envío. El botón deshabilitado ya no viaja en el POST, por eso
        // su valor de "accion" se copia a un campo oculto.
        function bloquearEnvio(form, boton, textoCarga) {
            if (boton && boton.name) {
                const oculto = document.createElement('input');
                oculto.type = 'hidden';
                oculto.name = boton.name;
                oculto.value = boton.value;
                oculto.dataset.temporal = '';
                form.appendChild(oculto);
            }
            form.setAttribute('aria-busy', 'true');
            document.querySelectorAll('form button[type="submit"]').forEach(function (b) {
                b.disabled = true;
            });
            if (boton) {
                textosOriginales.set(boton, boton.textContent);
                boton.textContent = textoCarga;
                boton.classList.add('cargando');
            }
        }

        // Al volver con el botón "atrás" del navegador, la página reaparece como quedó
        window.addEventListener('pageshow', function () {
            document.querySelectorAll('[data-temporal]').forEach(function (campo) {
                campo.remove();
            });
            document.querySelectorAll('form[aria-busy]').forEach(function (form) {
                form.removeAttribute('aria-busy');
            });
            document.querySelectorAll('form button[type="submit"]').forEach(function (b) {
                b.disabled = false;
            });
            textosOriginales.forEach(function (texto, boton) {
                boton.textContent = texto;
                boton.classList.remove('cargando');
            });
            textosOriginales.clear();
        });

        formEnunciado.addEventListener('submit', function (evento) {
            if (!campoContexto.value.trim()) {
                evento.preventDefault();
                errorContexto.textContent = 'Escribe el ejercicio para extraer el modelo. Por ejemplo: Maximizar Z = 3x + 5y.';
                errorContexto.hidden = false;
                campoContexto.setAttribute('aria-invalid', 'true');
                campoContexto.focus();
                return;
            }
            bloquearEnvio(formEnunciado, evento.submitter, 'Extrayendo modelo…');
        });

        campoContexto.addEventListener('input', function () {
            errorContexto.hidden = true;
            campoContexto.removeAttribute('aria-invalid');
        });

        iniciarEjemplo(huellaActual);

        if (formModelo) {
            iniciarModelo(formModelo, campoContexto, bloquearEnvio);
        }
    }

    // "Cargar ejemplo" recarga la ruta; si hay cambios sin calcular, pide confirmar en línea
    function iniciarEjemplo(huellaActual) {
        const form = document.getElementById('form-ejemplo');
        const boton = document.getElementById('btn-ejemplo');
        const panel = document.getElementById('confirmar-ejemplo');
        const confirmar = document.getElementById('btn-ejemplo-confirmar');
        const cancelar = document.getElementById('btn-ejemplo-cancelar');
        const huellaInicial = huellaActual();

        form.addEventListener('submit', function (evento) {
            if (panel.hidden && huellaActual() !== huellaInicial) {
                evento.preventDefault();
                boton.hidden = true;
                panel.hidden = false;
                confirmar.focus();
            }
        });

        cancelar.addEventListener('click', function () {
            panel.hidden = true;
            boton.hidden = false;
            boton.focus();
        });
    }

    function iniciarModelo(form, campoContexto, bloquearEnvio) {
        const contenedor = document.getElementById('restricciones-container');
        const plantilla = document.getElementById('plantilla-restriccion');
        const btnAgregar = document.getElementById('btn-agregar-restriccion');
        const grupoObjetivo = form.querySelector('[data-grupo-objetivo]');
        const camposZ = Array.from(form.querySelectorAll('input[name="z[]"]'));
        const tipo = document.getElementById('tipo-opt');
        const vistaPrevia = document.getElementById('vista-previa');
        const estadoEnvio = document.getElementById('estado-envio');
        const resumen = document.getElementById('resumen-modelo');
        let cuadroPendiente = null;

        function filas() {
            return Array.from(contenedor.querySelectorAll('[data-restriccion]:not(.saliendo)'));
        }

        function camposDe(fila) {
            return Array.from(fila.querySelectorAll('input[name="a[]"]'));
        }

        function ladoDerecho(fila) {
            return fila.querySelector('input[name="b[]"]');
        }

        function operador(fila) {
            return fila.querySelector('select[name="op[]"]');
        }

        // El solver invierte la desigualdad si el lado derecho es negativo; la artificial
        // depende del operador ya normalizado, no del que está escrito.
        function operadorNormalizado(fila) {
            const op = operador(fila).value;
            const b = leerNumero(ladoDerecho(fila).value);
            const invertida = b !== null && b < 0 && op !== '=';
            const efectivo = invertida ? { '<=': '>=', '>=': '<=' }[op] : op;
            return { efectivo: efectivo, invertida: invertida };
        }

        function subindice(n) {
            return String(n).replace(/\d/g, function (d) {
                return '₀₁₂₃₄₅₆₇₈₉'[Number(d)];
            });
        }

        function describirCampos(fila, numero) {
            fila.querySelector('[data-nombre]').textContent = `R${numero}`;
            camposDe(fila).forEach(function (campo) {
                campo.dataset.desc = `el coeficiente de ${campo.dataset.visible} en la restricción ${numero}`;
                campo.setAttribute('aria-label', `Coeficiente de ${campo.dataset.visible} en la restricción ${numero}`);
            });
            operador(fila).setAttribute('aria-label', `Tipo de la restricción ${numero}`);
            const b = ladoDerecho(fila);
            b.dataset.desc = `el lado derecho de la restricción ${numero}`;
            b.setAttribute('aria-label', `Lado derecho de la restricción ${numero}`);
            fila.querySelector('[data-eliminar]').setAttribute('aria-label', `Eliminar la restricción ${numero}`);
            const error = fila.querySelector('[data-error]');
            error.id = `error-restriccion-${numero}`;
            fila.querySelectorAll('input').forEach(function (campo) {
                campo.setAttribute('aria-describedby', error.id);
            });
        }

        function marcarArtificiales() {
            let artificiales = 0;
            filas().forEach(function (fila) {
                const estado = operadorNormalizado(fila);
                const marca = fila.querySelector('[data-lleva]');
                if (estado.efectivo === '<=' && !estado.invertida) {
                    marca.hidden = true;
                    return;
                }
                marca.hidden = false;
                if (estado.efectivo === '<=') {
                    marca.textContent = 'se invierte, sin artificial';
                    return;
                }
                artificiales += 1;
                const nombre = `A${subindice(artificiales)}`;
                marca.textContent = estado.invertida ? `se invierte y lleva ${nombre}` : `lleva ${nombre}`;
            });
        }

        function actualizarVistaPrevia() {
            const verbo = tipo.value === 'max' ? '\\max' : '\\min';
            const objetivo = `${verbo}\\ Z = ${expresionTex(camposZ)}`;
            const signos = { '<=': '\\le', '>=': '\\ge', '=': '=' };
            const lineas = [objetivo];
            filas().forEach(function (fila) {
                lineas.push(`${expresionTex(camposDe(fila))} ${signos[operador(fila).value]} ${ladoDerechoTex(ladoDerecho(fila))}`);
            });
            lineas.push(`${camposZ.map(function (c) { return variableTex(c.dataset.var); }).join(',\\ ')} \\ge 0`);

            vistaPrevia.replaceChildren();
            lineas.forEach(function (tex) {
                const linea = document.createElement('div');
                linea.className = 'linea-modelo';
                renderizarTex(linea, tex);
                vistaPrevia.appendChild(linea);
            });

            if (resumen) {
                const n = filas().length;
                const conteo = document.createElement('span');
                conteo.textContent = ` · ${n} ${n === 1 ? 'restricción' : 'restricciones'}`;
                const formula = document.createElement('span');
                renderizarTex(formula, objetivo);
                resumen.replaceChildren(formula, conteo);
            }
        }

        function actualizar() {
            const lista = filas();
            lista.forEach(function (fila, i) {
                describirCampos(fila, i + 1);
                fila.querySelector('[data-eliminar]').disabled = lista.length === 1;
            });
            marcarArtificiales();
            actualizarVistaPrevia();
        }

        function programarActualizacion() {
            if (cuadroPendiente === null) {
                cuadroPendiente = requestAnimationFrame(function () {
                    cuadroPendiente = null;
                    actualizar();
                });
            }
        }

        // ── Validación en línea ──────────────────────────────────────────────────
        function mensajeDeCampo(campo) {
            const texto = campo.value.trim();
            const esCoeficiente = campo.name !== 'b[]';
            if (!texto) {
                return `Falta ${campo.dataset.desc}. Escribe un número${esCoeficiente ? '; usa 0 si la variable no aparece' : ''}.`;
            }
            if (/\/[+-]?0+$/.test(texto)) {
                return `En ${campo.dataset.desc}, "${texto}" divide entre 0. Cambia el denominador.`;
            }
            if (leerNumero(texto) === null) {
                return `En ${campo.dataset.desc}, "${texto}" no es un número. Usa un formato como 2, 1.5 o 1/3.`;
            }
            return '';
        }

        // Mientras se escribe solo se juzgan los campos ya tocados; al enviar, todos
        function validarGrupo(grupo, campos, soloTocados) {
            const salida = grupo.querySelector('[data-error]');
            const mensajes = [];
            campos.forEach(function (campo) {
                const mensaje = soloTocados && !('tocado' in campo.dataset) ? '' : mensajeDeCampo(campo);
                if (mensaje) {
                    mensajes.push(mensaje);
                    campo.setAttribute('aria-invalid', 'true');
                } else {
                    campo.removeAttribute('aria-invalid');
                }
            });
            salida.textContent = mensajes.join('\n');
            salida.hidden = mensajes.length === 0;
            return mensajes.length;
        }

        function validarGrupoDe(campo) {
            const fila = campo.closest('[data-restriccion]');
            if (fila) {
                validarGrupo(fila, camposDe(fila).concat(ladoDerecho(fila)), true);
            } else if (campo.closest('[data-grupo-objetivo]')) {
                validarGrupo(grupoObjetivo, camposZ, true);
            }
        }

        function esCampoNumerico(objetivo) {
            return objetivo.matches('input[type="text"]');
        }

        form.addEventListener('input', function (evento) {
            if (esCampoNumerico(evento.target)) {
                evento.target.dataset.tocado = '';
                const grupo = evento.target.closest('[data-restriccion], [data-grupo-objetivo]');
                if (!grupo.querySelector('[data-error]').hidden) {
                    validarGrupoDe(evento.target);
                }
            }
            programarActualizacion();
        });

        form.addEventListener('change', programarActualizacion);

        form.addEventListener('focusout', function (evento) {
            if (esCampoNumerico(evento.target) && 'tocado' in evento.target.dataset) {
                validarGrupoDe(evento.target);
            }
        });

        form.addEventListener('submit', function (evento) {
            contenedor.querySelectorAll('.saliendo').forEach(function (fila) {
                fila.remove();
            });
            actualizar();

            let errores = validarGrupo(grupoObjetivo, camposZ, false);
            filas().forEach(function (fila) {
                errores += validarGrupo(fila, camposDe(fila).concat(ladoDerecho(fila)), false);
            });

            if (errores > 0) {
                evento.preventDefault();
                estadoEnvio.textContent = errores === 1
                    ? 'Corrige el campo marcado para calcular.'
                    : `Corrige los ${errores} campos marcados para calcular.`;
                form.querySelector('[aria-invalid="true"]').focus();
                return;
            }

            estadoEnvio.textContent = '';
            document.getElementById('contexto-oculto').value = campoContexto.value;
            bloquearEnvio(form, evento.submitter, 'Calculando…');
        });

        // ── Agregar y eliminar restricciones ─────────────────────────────────────
        btnAgregar.addEventListener('click', function () {
            const nueva = plantilla.content.firstElementChild.cloneNode(true);
            nueva.classList.add('entrando');
            nueva.addEventListener('animationend', function () {
                nueva.classList.remove('entrando');
            }, { once: true });
            contenedor.appendChild(nueva);
            actualizar();
            camposDe(nueva)[0].focus();
        });

        contenedor.addEventListener('click', function (evento) {
            const boton = evento.target.closest('[data-eliminar]');
            if (!boton || boton.disabled) {
                return;
            }
            const fila = boton.closest('[data-restriccion]');
            const lista = filas();
            const vecina = lista[lista.indexOf(fila) + 1] || lista[lista.indexOf(fila) - 1];

            function quitar() {
                fila.remove();
            }

            if (movimiento.matches) {
                quitar();
            } else {
                fila.classList.add('saliendo');
                fila.addEventListener('animationend', quitar, { once: true });
            }
            actualizar();

            const destino = vecina.querySelector('[data-eliminar]');
            (destino.disabled ? btnAgregar : destino).focus();
        });

        actualizar();
    }

    // ── Visor paso a paso ────────────────────────────────────────────────────────
    function iniciarVisor() {
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

        if (pasos.length > 0) {
            mostrarPaso();
        }
    }

    renderizarMath(document.getElementById('teoria'));
    iniciarFormulario();
    iniciarVisor();
})();
