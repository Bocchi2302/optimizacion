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
    const FASES = [
        { nombre: 'Estandarizar', patron: /estandariz/i },
        { nombre: 'Tabla inicial', patron: /tabla inicial/i },
        { nombre: 'Preparar fila Z', patron: /eliminaci[oó]n/i },
        { nombre: 'Iteraciones', patron: /iteraci[oó]n/i },
        { nombre: 'Resultado', patron: /soluci[oó]n|diagn[oó]stico/i }
    ];
    const FASE_POR_DEFECTO = 3;

    function limpiarTitulo(titulo) {
        return titulo.replace(/^Paso\s+\d+\s*:\s*/i, '');
    }

    // Si el solver agrega un título desconocido, el paso cae en la fase del anterior
    function faseDe(titulo, faseAnterior) {
        const indice = FASES.findIndex(function (fase) {
            return fase.patron.test(titulo);
        });
        if (indice !== -1) {
            return indice;
        }
        return faseAnterior === null ? FASE_POR_DEFECTO : faseAnterior;
    }

    function esArtificial(nombre) {
        return /^A[₀-₉]/.test(nombre);
    }

    // Quita el ruido de los decimales periódicos sin tocar el valor exacto
    function acortarNumero(texto) {
        const decimales = (texto.split('.')[1] || '').length;
        if (decimales <= 4 && !/e/i.test(texto)) {
            return texto;
        }
        const redondeado = Number(Number(texto).toFixed(4));
        return redondeado === 0 ? texto : String(redondeado);
    }

    function acortarDecimales(texto) {
        return texto.replace(/-?\d+\.\d{5,}/g, acortarNumero);
    }

    // Solo el coeficiente citado entre paréntesis: "(40M + 15)". El resto de las M vive en KaTeX
    function resaltarTerminosM(html) {
        return html.replace(/\((-?[\d.]*M)((?: [+-] [\d.]+)?)\)/g, '(<span class="termino-m">$1</span>$2)');
    }

    function iniciarVisor() {
        // Datos generados por Python: lista de pasos con títulos, explicaciones, tablas y pivote
        const pasos = JSON.parse(document.getElementById('datos-pasos').textContent);
        if (pasos.length === 0) {
            return;
        }

        const elementos = {
            visor: document.getElementById('visor'),
            fases: document.getElementById('fases'),
            contador: document.getElementById('contador'),
            aviso: document.getElementById('aviso-final'),
            irDiagnostico: document.getElementById('btn-diagnostico'),
            anuncio: document.getElementById('anuncio'),
            titulo: document.getElementById('titulo-paso'),
            hechos: document.getElementById('hechos-paso'),
            indicador: document.getElementById('indicador'),
            faseActual: document.getElementById('fase-actual'),
            explicacion: document.getElementById('explicacion'),
            formulas: document.getElementById('formulas'),
            tablas: document.getElementById('tablas'),
            controlTablas: document.getElementById('control-tablas'),
            conteoCambios: document.getElementById('conteo-cambios'),
            botonesVista: Array.from(document.querySelectorAll('[data-vista]')),
            leyenda: document.getElementById('leyenda'),
            leyendaColumna: document.getElementById('leyenda-columna'),
            anterior: document.getElementById('btn-anterior'),
            siguiente: document.getElementById('btn-siguiente')
        };

        let indiceActual = 0;
        let vista = 'juntas';

        // Datos derivados de cada paso, sin tocar el contrato del solver
        const tablaInicial = pasos.find(function (paso) { return paso.tabla; }).tabla;
        const artificiales = tablaInicial.columnas.filter(esArtificial);

        let faseAnterior = null;
        const derivados = pasos.map(function (paso, i) {
            const fase = faseDe(limpiarTitulo(paso.titulo), faseAnterior);
            faseAnterior = fase;
            const tablaFinal = paso.tabla_resultado || paso.tabla || tablaInicial;
            const base = tablaFinal.filas.slice(1).map(function (fila) { return fila.base; });
            const antes = paso.tabla ? paso.tabla.filas.slice(1).map(function (fila) { return fila.base; }) : base;
            return {
                indice: i,
                fase: fase,
                artificialesEnBase: base.filter(esArtificial),
                salen: antes.filter(function (nombre) {
                    return esArtificial(nombre) && !base.includes(nombre);
                })
            };
        });

        // Serie del contador sin repetidos seguidos: 2 → 1 → 0
        const serie = [];
        derivados.forEach(function (d) {
            const cuenta = d.artificialesEnBase.length;
            if (serie.length === 0 || serie[serie.length - 1].cuenta !== cuenta) {
                serie.push({ cuenta: cuenta, desde: d.indice });
            }
        });

        const botonesFase = FASES.map(function (fase, f) {
            const delaFase = derivados.filter(function (d) { return d.fase === f; });
            const item = document.createElement('li');
            item.className = 'fase';
            item.style.setProperty('--pasos', Math.max(delaFase.length, 1));

            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'fase-boton';
            boton.disabled = delaFase.length === 0;

            const pista = document.createElement('span');
            pista.className = 'fase-pista';
            const marcas = delaFase.map(function (d) {
                const marca = document.createElement('span');
                marca.className = 'fase-marca';
                marca.dataset.paso = d.indice;
                pista.appendChild(marca);
                return marca;
            });
            if (delaFase.length === 0) {
                const vacia = document.createElement('span');
                vacia.className = 'fase-marca';
                pista.appendChild(vacia);
            }

            const nombre = document.createElement('span');
            nombre.className = 'fase-nombre';
            nombre.textContent = fase.nombre;

            boton.append(pista, nombre);
            boton.setAttribute('aria-label', delaFase.length === 0
                ? `${fase.nombre}: sin pasos en este problema`
                : `Ir a ${fase.nombre}`);
            boton.addEventListener('click', function () {
                irA(delaFase[0].indice);
            });

            item.appendChild(boton);
            elementos.fases.appendChild(item);
            return { boton: boton, marcas: marcas };
        });

        function actualizarFases() {
            const faseVigente = derivados[indiceActual].fase;
            botonesFase.forEach(function (fase, f) {
                if (f === faseVigente) {
                    fase.boton.setAttribute('aria-current', 'step');
                } else {
                    fase.boton.removeAttribute('aria-current');
                }
                fase.boton.classList.toggle('fase-vigente', f === faseVigente);
                fase.marcas.forEach(function (marca) {
                    const paso = Number(marca.dataset.paso);
                    marca.classList.toggle('hecha', paso < indiceActual);
                    marca.classList.toggle('actual', paso === indiceActual);
                });
            });
            elementos.faseActual.textContent = FASES[faseVigente].nombre;
        }

        function actualizarContador(animar) {
            const contador = elementos.contador;
            contador.replaceChildren();

            if (artificiales.length === 0) {
                contador.textContent = 'Este problema no usa variables artificiales: arranca con las holguras en la base.';
                contador.classList.add('contador-vacio');
                return;
            }

            const actual = derivados[indiceActual];
            const etiqueta = document.createElement('span');
            etiqueta.textContent = 'Artificiales en la base:';

            const cifras = document.createElement('span');
            cifras.className = 'contador-serie';
            let vigente = 0;
            serie.forEach(function (tramo, i) {
                if (tramo.desde <= indiceActual) {
                    vigente = i;
                }
            });
            serie.forEach(function (tramo, i) {
                if (i > 0) {
                    const flecha = document.createElement('span');
                    flecha.className = 'contador-flecha';
                    flecha.setAttribute('aria-hidden', 'true');
                    flecha.textContent = '→';
                    cifras.appendChild(flecha);
                }
                const cifra = document.createElement('span');
                cifra.className = 'contador-cifra';
                cifra.textContent = tramo.cuenta;
                cifra.classList.toggle('vigente', i === vigente);
                cifra.classList.toggle('futura', i > vigente);
                if (i === vigente) {
                    cifra.setAttribute('aria-current', 'true');
                }
                cifras.appendChild(cifra);
            });

            const nombres = document.createElement('span');
            nombres.className = 'contador-nombres';
            artificiales.forEach(function (nombre) {
                const chip = document.createElement('span');
                chip.className = 'artificial';
                chip.textContent = nombre;
                if (!actual.artificialesEnBase.includes(nombre)) {
                    chip.classList.add('tachada');
                    const estado = document.createElement('span');
                    estado.className = 'solo-lector';
                    estado.textContent = ' fuera de la base';
                    chip.appendChild(estado);
                    if (animar && actual.salen.includes(nombre)) {
                        chip.classList.add('animar');
                    }
                }
                nombres.appendChild(chip);
            });

            contador.append(etiqueta, cifras, nombres);
        }

        function datosDeIteracion(titulo) {
            const partes = /^(Iteraci[oó]n \d+)\s*\(Columna pivote (.+), Fila pivote (.+), Elemento pivote (.+)\)$/.exec(titulo);
            return partes
                ? { titulo: partes[1], entra: partes[2], sale: partes[3], pivote: partes[4] }
                : null;
        }

        function mostrarHechos(iteracion) {
            elementos.hechos.replaceChildren();
            elementos.hechos.hidden = !iteracion;
            if (!iteracion) {
                return;
            }
            [['entra', iteracion.entra], ['sale', iteracion.sale], ['pivote', acortarDecimales(iteracion.pivote)]]
                .forEach(function (hecho) {
                    const parte = document.createElement('span');
                    const valor = document.createElement('strong');
                    parte.textContent = `${hecho[0]} `;
                    valor.textContent = hecho[1];
                    parte.appendChild(valor);
                    elementos.hechos.appendChild(parte);
                });
        }

        function anunciar(paso) {
            const d = derivados[indiceActual];
            let texto = `Paso ${indiceActual + 1} de ${pasos.length}, fase ${FASES[d.fase].nombre}.`;
            if (d.salen.length > 0) {
                texto += ` Sale ${d.salen.join(' y ')}. Artificiales en la base: ${d.artificialesEnBase.length}.`;
            }
            elementos.anuncio.textContent = texto;
        }

        function aMenos(texto) {
            return texto.replace(/^-/, '−');
        }

        // Escribe un valor de celda: "40M + 15" separa el término con M; los decimales
        // largos se acortan y el valor exacto queda en title y para el lector de pantalla.
        function pintarValor(celda, crudo) {
            const conM = /^(-?(?:[\d.]+(?:e[+-]?\d+)?)?)M(?: ([+-]) (.+))?$/.exec(crudo);
            const visible = document.createElement('span');
            let acortado = false;

            function numero(texto) {
                const corto = acortarNumero(texto);
                acortado = acortado || corto !== texto;
                return corto;
            }

            if (conM) {
                const coeficiente = conM[1] === '-' || conM[1] === '' ? conM[1] : numero(conM[1]);
                const termino = document.createElement('span');
                termino.className = 'termino-m';
                termino.textContent = `${aMenos(coeficiente)}M`;
                visible.appendChild(termino);
                if (conM[2]) {
                    visible.append(` ${conM[2] === '-' ? '−' : '+'} ${numero(conM[3])}`);
                }
            } else {
                visible.textContent = aMenos(numero(crudo));
            }

            celda.appendChild(visible);
            if (acortado) {
                celda.title = crudo;
                visible.setAttribute('aria-hidden', 'true');
                const exacto = document.createElement('span');
                exacto.className = 'solo-lector';
                exacto.textContent = crudo;
                celda.appendChild(exacto);
            }
        }

        function marcaEje(texto) {
            const marca = document.createElement('span');
            marca.className = 'marca-eje';
            marca.textContent = texto;
            return marca;
        }

        function textoOculto(texto) {
            const oculto = document.createElement('span');
            oculto.className = 'solo-lector';
            oculto.textContent = texto;
            return oculto;
        }

        function revisarDesborde(marco) {
            const envoltorio = marco.querySelector('.tabla-envoltorio');
            const pista = marco.parentElement.querySelector('.pista-desliza');
            const hay = envoltorio.scrollWidth > envoltorio.clientWidth + 1;
            const fin = envoltorio.scrollWidth - envoltorio.clientWidth - 1;
            marco.classList.toggle('hay-izquierda', hay && envoltorio.scrollLeft > 1);
            marco.classList.toggle('hay-derecha', hay && envoltorio.scrollLeft < fin);
            pista.hidden = !hay;
            if (hay) {
                envoltorio.tabIndex = 0;
                envoltorio.setAttribute('role', 'region');
                envoltorio.setAttribute('aria-label', 'Tabla con desplazamiento horizontal');
            } else {
                envoltorio.removeAttribute('tabindex');
                envoltorio.removeAttribute('role');
                envoltorio.removeAttribute('aria-label');
            }
        }

        function revisarTodosLosDesbordes() {
            elementos.tablas.querySelectorAll('.tabla-marco').forEach(revisarDesborde);
        }

        // opciones: etiqueta, rol ("antes" o "despues"), pivote, previa (tabla anterior
        // para comparar celdas) y animar (dibuja el tachado de la artificial que sale)
        function crearTabla(datos, opciones) {
            const pivote = opciones.pivote;
            const previa = opciones.previa;
            const bloque = document.createElement('div');
            bloque.className = 'bloque-tabla';
            if (opciones.rol) {
                bloque.dataset.rol = opciones.rol;
            }

            if (opciones.etiqueta) {
                const titulo = document.createElement('h4');
                titulo.textContent = opciones.etiqueta;
                bloque.appendChild(titulo);
            }

            const marco = document.createElement('div');
            marco.className = 'tabla-marco';
            const envoltorio = document.createElement('div');
            envoltorio.className = 'tabla-envoltorio';
            envoltorio.addEventListener('scroll', function () {
                revisarDesborde(marco);
            }, { passive: true });

            const tabla = document.createElement('table');
            tabla.className = 'tabla-simplex';

            const titulo = tabla.createCaption();
            titulo.className = 'solo-lector';
            titulo.textContent = opciones.etiqueta || 'Tabla Simplex';

            // El mismo ancho en ambas tablas: una columna se compara a la misma altura visual
            const columnas = document.createElement('colgroup');
            opciones.anchos.forEach(function (ancho) {
                const columna = document.createElement('col');
                columna.style.width = `calc(${ancho}ch + 1.5rem)`;
                columnas.appendChild(columna);
            });
            tabla.appendChild(columnas);

            // Encabezado: la columna 0 es "Base"; las columnas de datos van desde la 1
            const encabezado = tabla.createTHead().insertRow();
            ['Base'].concat(datos.columnas).forEach(function (texto, j) {
                const th = document.createElement('th');
                th.scope = 'col';
                th.textContent = texto;
                if (j === 0) {
                    th.classList.add('celda-base');
                }
                if (esArtificial(texto)) {
                    th.classList.add('col-artificial');
                }
                if (j === datos.columnas.length) {
                    th.classList.add('col-solucion');
                }
                if (pivote && j - 1 === pivote.columna) {
                    th.classList.add('columna-pivote');
                    th.appendChild(marcaEje(pivote.fila === null ? 'sin límite' : 'entra'));
                }
                encabezado.appendChild(th);
            });

            // Cuerpo: fila i (0 = Z) y columna j (0 = Z, ..., última = Solución)
            const cuerpo = tabla.createTBody();
            datos.filas.forEach(function (fila, i) {
                const tr = cuerpo.insertRow();
                if (i === 0) {
                    tr.classList.add('fila-z');
                }
                if (pivote && i === pivote.fila) {
                    tr.classList.add('fila-pivote');
                }

                const celdaBase = document.createElement('th');
                celdaBase.scope = 'row';
                celdaBase.className = 'celda-base';
                celdaBase.textContent = fila.base;
                if (esArtificial(fila.base)) {
                    celdaBase.classList.add('col-artificial');
                }
                if (pivote && i === pivote.fila) {
                    celdaBase.appendChild(marcaEje('sale'));
                }
                if (previa && previa.filas[i].base !== fila.base) {
                    const anterior = previa.filas[i].base;
                    celdaBase.classList.add('cambiada');
                    if (esArtificial(anterior)) {
                        const salida = document.createElement('span');
                        salida.className = 'base-salida';
                        const nombre = document.createElement('span');
                        nombre.className = opciones.animar ? 'tachada animar' : 'tachada';
                        nombre.textContent = anterior;
                        salida.append('sale ', nombre);
                        celdaBase.appendChild(salida);
                    }
                }
                tr.appendChild(celdaBase);

                fila.celdas.forEach(function (valor, j) {
                    const td = tr.insertCell();
                    const esElemento = pivote && i === pivote.fila && j === pivote.columna;
                    if (esElemento) {
                        const etiqueta = document.createElement('span');
                        etiqueta.className = 'etiqueta-pivote';
                        etiqueta.textContent = 'pivote';
                        td.appendChild(etiqueta);
                        td.classList.add('elemento-pivote');
                    }
                    pintarValor(td, valor);
                    if (pivote && j === pivote.columna && !esElemento) {
                        td.classList.add('columna-pivote');
                    }
                    if (j === fila.celdas.length - 1) {
                        td.classList.add('col-solucion');
                    }
                    if (previa && previa.filas[i].celdas[j] !== valor) {
                        td.classList.add('cambiada');
                        td.appendChild(textoOculto(', cambió'));
                    }
                });
            });

            envoltorio.appendChild(tabla);
            marco.appendChild(envoltorio);
            bloque.appendChild(marco);

            const pista = document.createElement('p');
            pista.className = 'nota pista-desliza';
            pista.textContent = 'Desliza la tabla para ver todas las columnas.';
            pista.hidden = true;
            bloque.appendChild(pista);
            return bloque;
        }

        function anchosDeColumna(tablas) {
            const anchos = ['Base'].concat(tablas[0].columnas).map(function (texto) {
                return Math.max(texto.length, 4);
            });
            tablas.forEach(function (tabla) {
                tabla.filas.forEach(function (fila) {
                    anchos[0] = Math.max(anchos[0], fila.base.length);
                    fila.celdas.forEach(function (valor, j) {
                        anchos[j + 1] = Math.max(anchos[j + 1], acortarDecimales(valor).length);
                    });
                });
            });
            if (tablas.length > 1) {
                anchos[0] = Math.max(anchos[0], 'sale A₁'.length);
            }
            return anchos;
        }

        function contarCambios(antes, despues) {
            let cambios = 0;
            despues.filas.forEach(function (fila, i) {
                fila.celdas.forEach(function (valor, j) {
                    if (antes.filas[i].celdas[j] !== valor) {
                        cambios += 1;
                    }
                });
            });
            return cambios;
        }

        function aplicarVista() {
            elementos.botonesVista.forEach(function (boton) {
                boton.setAttribute('aria-pressed', String(boton.dataset.vista === vista));
            });
            elementos.tablas.querySelectorAll('.bloque-tabla[data-rol]').forEach(function (bloque) {
                bloque.hidden = vista !== 'juntas' && bloque.dataset.rol !== vista;
            });
            elementos.tablas.classList.toggle('juntas', vista === 'juntas');
            revisarTodosLosDesbordes();
        }

        function actualizarLeyenda(paso) {
            const tablas = [paso.tabla, paso.tabla_resultado].filter(Boolean);
            const hayM = tablas.some(function (tabla) {
                return tabla.filas.some(function (fila) {
                    return fila.celdas.some(function (valor) { return valor.includes('M'); });
                });
            });
            const pivote = paso.pivote;
            const visibles = {
                fila: Boolean(pivote) && pivote.fila !== null,
                columna: Boolean(pivote),
                elemento: Boolean(pivote) && pivote.fila !== null,
                cambio: Boolean(paso.tabla_resultado),
                m: hayM
            };
            elementos.leyendaColumna.textContent = pivote && pivote.fila === null
                ? 'Columna sin límite'
                : 'Columna que entra';
            let alguna = false;
            elementos.leyenda.querySelectorAll('[data-leyenda]').forEach(function (item) {
                item.hidden = !visibles[item.dataset.leyenda];
                alguna = alguna || !item.hidden;
            });
            elementos.leyenda.hidden = !alguna;
        }

        function dibujarTablas(paso, animar) {
            const comparar = Boolean(paso.tabla_resultado);
            elementos.tablas.replaceChildren();
            elementos.controlTablas.hidden = !comparar;
            elementos.tablas.classList.toggle('lado-a-lado', comparar && paso.tabla.columnas.length <= 7);
            const anchos = paso.tabla ? anchosDeColumna([paso.tabla, paso.tabla_resultado].filter(Boolean)) : [];

            if (paso.tabla) {
                elementos.tablas.appendChild(crearTabla(paso.tabla, {
                    etiqueta: comparar ? 'Antes del pivoteo' : null,
                    rol: comparar ? 'antes' : null,
                    pivote: paso.pivote,
                    anchos: anchos
                }));
            }
            if (comparar) {
                const cambios = contarCambios(paso.tabla, paso.tabla_resultado);
                elementos.conteoCambios.textContent = cambios === 1
                    ? '1 celda cambió'
                    : `${cambios} celdas cambiaron`;
                elementos.tablas.appendChild(crearTabla(paso.tabla_resultado, {
                    etiqueta: 'Después del pivoteo',
                    rol: 'despues',
                    previa: paso.tabla,
                    animar: animar,
                    anchos: anchos
                }));
            }
            actualizarLeyenda(paso);
            aplicarVista();
        }

        function mostrarPaso(opciones) {
            const paso = pasos[indiceActual];
            const titulo = limpiarTitulo(paso.titulo);
            const iteracion = datosDeIteracion(titulo);

            elementos.indicador.textContent = `Paso ${indiceActual + 1} de ${pasos.length}`;
            elementos.titulo.textContent = iteracion ? iteracion.titulo : titulo;
            mostrarHechos(iteracion);
            actualizarFases();
            actualizarContador(opciones.animar);

            elementos.explicacion.innerHTML = resaltarTerminosM(acortarDecimales(paso.explicacion));

            elementos.formulas.replaceChildren();
            paso.formulas.forEach(function (texto) {
                const div = document.createElement('div');
                div.className = 'formula';
                div.textContent = acortarDecimales(texto);
                elementos.formulas.appendChild(div);
            });

            dibujarTablas(paso, opciones.animar);

            if (elementos.aviso) {
                elementos.aviso.hidden = indiceActual === pasos.length - 1;
            }
            elementos.anterior.disabled = indiceActual === 0;
            elementos.siguiente.disabled = indiceActual === pasos.length - 1;

            renderizarMath(elementos.explicacion);
            renderizarMath(elementos.formulas);

            if (opciones.foco) {
                elementos.titulo.focus({ preventScroll: true });
                const posicion = elementos.titulo.getBoundingClientRect().top;
                if (posicion < 0 || posicion > window.innerHeight * 0.5) {
                    elementos.fases.scrollIntoView({ block: 'start', behavior: movimiento.matches ? 'auto' : 'smooth' });
                }
                anunciar(paso);
            }
        }

        function irA(indice) {
            if (indice < 0 || indice >= pasos.length || indice === indiceActual) {
                return;
            }
            const animar = indice > indiceActual;
            indiceActual = indice;
            mostrarPaso({ foco: true, animar: animar });
        }

        elementos.anterior.addEventListener('click', function () {
            irA(indiceActual - 1);
        });
        elementos.siguiente.addEventListener('click', function () {
            irA(indiceActual + 1);
        });
        if (elementos.irDiagnostico) {
            elementos.irDiagnostico.addEventListener('click', function () {
                irA(pasos.length - 1);
            });
        }

        elementos.botonesVista.forEach(function (boton) {
            boton.addEventListener('click', function () {
                vista = boton.dataset.vista;
                aplicarVista();
            });
        });

        window.addEventListener('resize', revisarTodosLosDesbordes);
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(revisarTodosLosDesbordes);
        }

        // Las flechas no secuestran la escritura ni el desplazamiento de una tabla
        document.addEventListener('keydown', function (evento) {
            if (evento.altKey || evento.ctrlKey || evento.metaKey || evento.shiftKey) {
                return;
            }
            const destinos = {
                ArrowRight: indiceActual + 1,
                ArrowLeft: indiceActual - 1,
                Home: 0,
                End: pasos.length - 1
            };
            if (!(evento.key in destinos)) {
                return;
            }
            if (evento.target.closest('input, select, textarea, [contenteditable], .tabla-envoltorio[tabindex]')) {
                return;
            }
            evento.preventDefault();
            irA(destinos[evento.key]);
        });

        mostrarPaso({ foco: true, animar: false });
    }

    renderizarMath(document.getElementById('teoria'));
    iniciarFormulario();
    iniciarVisor();
})();
