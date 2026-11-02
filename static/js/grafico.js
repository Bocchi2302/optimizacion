document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('#form-grafico');
    const contenedor = document.querySelector('#restricciones');
    const botonAgregar = document.querySelector('#btn-agregar');
    const plantilla = document.querySelector('#tpl-fila');
    if (!form || !contenedor || !botonAgregar || !plantilla) return;

    const maximo = Number(contenedor.dataset.max) || 12;

    // ── Filas de restricciones ──────────────────────────────────────
    const filas = () => [...contenedor.querySelectorAll('[data-fila]')];

    const renumerar = () => {
        filas().forEach((fila, i) => {
            const n = i + 1;
            fila.querySelector('.fila-nombre').textContent = `R${n}`;
            fila.querySelector('[data-quitar]').setAttribute('aria-label', `Quitar restricción R${n}`);
        });
        botonAgregar.disabled = filas().length >= maximo;
    };

    const agregarFila = (valores = ['', '', '<=', '', '']) => {
        if (filas().length >= maximo) return null;
        const html = plantilla.innerHTML.replaceAll('__N__', filas().length + 1);
        const aux = document.createElement('div');
        aux.innerHTML = html.trim();
        const fila = aux.firstElementChild;
        const [x, y, op, c, rotulo] = valores;
        const campos = fila.querySelectorAll('input');
        campos[0].value = x; campos[1].value = y; campos[2].value = c; campos[3].value = rotulo || '';
        fila.querySelector('select').value = op;
        contenedor.appendChild(fila);
        renumerar();
        return fila;
    };

    botonAgregar.addEventListener('click', () => {
        const fila = agregarFila();
        if (fila) fila.querySelector('input').focus();
    });

    contenedor.addEventListener('click', (e) => {
        const quitar = e.target.closest('[data-quitar]');
        if (!quitar || filas().length <= 1) return;
        const fila = quitar.closest('[data-fila]');
        fila.classList.add('saliendo');
        setTimeout(() => { fila.remove(); renumerar(); }, 200);
    });


    // ── Extraer datos del enunciado ─────────────────────────────────
    const caja = document.querySelector('#revision');
    const botones = [...document.querySelectorAll('.btn-ia')];
    const urlExtraer = form.dataset.urlExtraer;

    const ocultarRevision = () => { if (caja) { caja.hidden = true; caja.innerHTML = ''; } };

    const el = (tag, clase, texto) => {
        const nodo = document.createElement(tag);
        if (clase) nodo.className = clase;
        if (texto !== undefined) nodo.textContent = texto;
        return nodo;
    };

    const pintarRevision = (datos, mensajeFinal) => {
        caja.innerHTML = '';
        caja.hidden = false;
        caja.className = 'revision ' + (datos.ok ? (datos.requiere_revision ? 'atencion' : 'bien') : 'mal');

        if (!datos.ok) {
            caja.append(el('strong', '', 'No pude leer el enunciado'), el('p', '', datos.error));
            return;
        }
        const cab = el('div', 'revision-cab');
        cab.append(el('strong', '', 'Esto entendí'),
            el('span', 'insignia', 'por reglas'));
        const lista = el('ul', 'revision-lista');
        datos.resumen.forEach((linea) => lista.append(el('li', '', linea)));
        caja.append(cab, lista);

        const extras = [...datos.advertencias.map((t) => ['aviso-li', t]), ...(datos.notas || []).map((t) => ['nota-li', t])];
        if (extras.length) {
            const ul = el('ul', 'revision-extra');
            extras.forEach(([clase, t]) => ul.append(el('li', clase, t)));
            caja.append(ul);
        }
        if (mensajeFinal) caja.append(el('p', 'revision-final', mensajeFinal));
    };

    const flash = (nodo) => {
        nodo.classList.remove('rellenado');
        void nodo.offsetWidth;
        nodo.classList.add('rellenado');
    };

    const rellenar = (datos) => {
        if (datos.tipo) form.querySelector(datos.tipo === 'max' ? '#t-max' : '#t-min').checked = true;
        const campos = { z_x: datos.z[0], z_y: datos.z[1], z_k: datos.z_k === '0' ? '' : datos.z_k };
        Object.entries(campos).forEach(([nombre, valor]) => {
            const input = form.querySelector(`[name=${nombre}]`);
            input.value = valor;
            flash(input);
        });
        datos.variables.forEach((v, i) => {
            const campo = form.querySelector(`#nombre_x${i + 1}`);
            campo.value = v.descripcion || '';
            if (v.descripcion) flash(campo);
        });
        const objetivo = form.querySelector('#objetivo_nombre');
        objetivo.value = datos.objetivo_nombre || '';
        if (datos.objetivo_nombre) flash(objetivo);
        form.querySelector('#extraccion').value = datos.metodo;
        filas().forEach((f) => f.remove());
        datos.restricciones.slice(0, maximo).forEach((r) => {
            const fila = agregarFila([r.x, r.y, r.op, r.c, r.rotulo]);
            if (fila) fila.querySelectorAll('input').forEach((i) => { if (i.value) flash(i); });
        });
        form.querySelectorAll('.invalido').forEach((i) => i.classList.remove('invalido'));
    };

    const extraer = async (resolver, silencioso = false) => {
        const texto = form.querySelector('#contexto').value;
        const boton = document.querySelector(resolver ? '#btn-extraer-resolver' : '#btn-extraer');
        botones.forEach((b) => { b.disabled = true; });
        boton.classList.add('cargando');
        try {
            const resp = await fetch(urlExtraer, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ texto }),
            });
            const datos = await resp.json();
            if (!datos.ok) {
                if (!silencioso) pintarRevision(datos);
                return;
            }
            rellenar(datos);
            if (resolver && !datos.requiere_revision) {
                pintarRevision(datos, 'Resolviendo…');
                form.requestSubmit();
                return;
            }
            pintarRevision(datos, datos.requiere_revision
                ? 'Revisa lo marcado arriba, corrige el formulario si hace falta y pulsa «Resolver paso a paso».'
                : 'Listo: el formulario quedó lleno. Pulsa «Resolver paso a paso».');
        } catch (err) {
            if (!silencioso) pintarRevision({ ok: false, error: 'No pude comunicarme con el servidor. Revisa que la aplicación siga corriendo.' });
        } finally {
            botones.forEach((b) => { b.disabled = false; b.classList.remove('cargando'); });
            if (!caja.hidden) caja.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    };

    botones.forEach((b) => b.addEventListener('click', () => extraer(b.dataset.resolver === '1')));

    const enunciado = form.querySelector('#contexto');
    enunciado.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); extraer(true); }
    });
    // Al pegar un modelo, lo lee de inmediato (sin molestar si no lo entiende)
    enunciado.addEventListener('paste', () => {
        setTimeout(() => {
            const t = enunciado.value;
            if (/(max|min)/i.test(t) && /[<>=≤≥]|\\le|\\ge/.test(t)) extraer(false, true);
        }, 40);
    });

    // Ctrl/⌘ + Enter en cualquier campo resuelve
    form.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && e.target !== enunciado) {
            e.preventDefault();
            form.requestSubmit();
        }
    });

    // ── Validación ligera antes de enviar ───────────────────────────
    const NUMERO = /^[+-]?(\d+([.,]\d+)?|[.,]\d+)(\/\d+)?$/;
    form.addEventListener('input', (e) => e.target.classList.remove('invalido'));
    form.addEventListener('submit', (e) => {
        let primero = null;
        form.querySelectorAll('input[inputmode=decimal]').forEach((input) => {
            if (input.name === 'z_k' && !input.value.trim()) return;   // la constante es opcional
            const bueno = NUMERO.test(input.value.trim());
            input.classList.toggle('invalido', !bueno);
            if (!bueno && !primero) primero = input;
        });
        if (primero) {
            e.preventDefault();
            primero.focus();
            return;
        }
        document.querySelector('#btn-calcular').classList.add('cargando');
    });

    renumerar();

    // ── Animación de pasos al entrar en pantalla + índice activo ────
    const pasos = [...document.querySelectorAll('[data-paso]')];
    const enlaces = new Map([...document.querySelectorAll('[data-nav]')].map((a) => [a.dataset.nav, a]));

    if ('IntersectionObserver' in window) {
        const revelar = new IntersectionObserver((entradas) => {
            entradas.forEach((en) => {
                if (en.isIntersecting) {
                    en.target.classList.add('visible');
                    revelar.unobserve(en.target);
                }
            });
        }, { threshold: 0.12 });
        pasos.forEach((p) => revelar.observe(p));

        const activo = new IntersectionObserver((entradas) => {
            entradas.forEach((en) => {
                if (!en.isIntersecting) return;
                enlaces.forEach((a) => a.classList.remove('activo'));
                const a = enlaces.get(en.target.id.replace('paso-', ''));
                if (a) {
                    a.classList.add('activo');
                    a.scrollIntoView({ block: 'nearest', inline: 'center' });
                }
            });
        }, { rootMargin: '-30% 0px -60% 0px' });
        pasos.forEach((p) => activo.observe(p));
    } else {
        pasos.forEach((p) => p.classList.add('visible'));
    }


    // ═══ Vida visual del resultado ═══════════════════════════════════
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ═══ Modo claro / oscuro ═════════════════════════════════════════
    const raiz = document.documentElement;
    const botonTema = document.querySelector('#btn-tema');
    const metaTema = document.querySelector('meta[name=theme-color]');
    const temaActual = () => (raiz.dataset.tema === 'oscuro' ? 'oscuro' : 'claro');
    const refrescarTema = () => {
        const oscuro = temaActual() === 'oscuro';
        if (botonTema) {
            botonTema.setAttribute('aria-label', oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
            botonTema.title = oscuro ? 'Modo claro' : 'Modo oscuro';
        }
        if (metaTema) metaTema.content = oscuro ? '#0b0e16' : '#f7f7f4';
    };
    const aplicarTema = (tema, guardar) => {
        raiz.dataset.tema = tema;
        if (guardar) { try { localStorage.setItem('tema-optilab', tema); } catch (err) { /* sin almacenamiento */ } }
        refrescarTema();
        window.dispatchEvent(new Event('cambio-tema'));
    };
    refrescarTema();
    if (botonTema) botonTema.addEventListener('click', () => {
        const nuevo = temaActual() === 'oscuro' ? 'claro' : 'oscuro';
        const r = botonTema.getBoundingClientRect();
        const x = r.left + r.width / 2, y = r.top + r.height / 2;
        if (document.startViewTransition && !sinMovimiento) {
            const radio = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
            const transicion = document.startViewTransition(() => aplicarTema(nuevo, true));
            transicion.ready.then(() => raiz.animate(
                { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radio}px at ${x}px ${y}px)`] },
                { duration: 750, easing: 'cubic-bezier(.16, 1, .3, 1)', pseudoElement: '::view-transition-new(root)' },
            )).catch(() => {});
        } else {
            aplicarTema(nuevo, true);
        }
    });
    // Mientras no haya una elección guardada, sigue al sistema
    if (window.matchMedia) {
        matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            let guardado = null;
            try { guardado = localStorage.getItem('tema-optilab'); } catch (err) { /* nada */ }
            if (!guardado) aplicarTema(e.matches ? 'oscuro' : 'claro', false);
        });
    }

    const zonaPasos = document.querySelector('#pasos');

    // Intersecciones: ver solo las factibles
    document.querySelectorAll('[data-solo-factibles]').forEach((casilla) => {
        const tabla = casilla.closest('details').querySelector('.tabla-cand');
        casilla.addEventListener('change', () => tabla.classList.toggle('solo-factibles', casilla.checked));
    });

    // Barra de progreso de lectura + avance del riel de pasos
    const barraProgreso = document.querySelector('#progreso-scroll');
    const riel = document.querySelector('.riel-progreso');
    const cabecera = document.querySelector('.barra');
    const botonArriba = document.querySelector('#btn-arriba');
    // Un solo manejador de scroll, limitado a un cálculo por cuadro y sin variables CSS heredadas
    // (cambiar una variable en #pasos obligaba a recalcular el estilo de miles de nodos en cada cuadro).
    let programado = false;
    const alDesplazar = () => {
        programado = false;
        const y = window.scrollY;
        const alto = document.documentElement.scrollHeight - window.innerHeight;
        if (barraProgreso) barraProgreso.style.transform = `scaleX(${alto > 0 ? Math.min(1, y / alto) : 0})`;
        if (riel && zonaPasos) {
            const r = zonaPasos.getBoundingClientRect();
            const avance = (window.innerHeight * 0.55 - r.top) / Math.max(1, r.height);
            riel.style.transform = `scaleY(${Math.max(0, Math.min(1, avance)).toFixed(3)})`;
        }
        if (cabecera) cabecera.classList.toggle('scrolled', y > 8);
        if (botonArriba) botonArriba.classList.toggle('visible', y > 700);
    };
    const pedirDesplazar = () => { if (!programado) { programado = true; requestAnimationFrame(alDesplazar); } };
    window.addEventListener('scroll', pedirDesplazar, { passive: true });
    window.addEventListener('resize', pedirDesplazar);
    alDesplazar();

    // Filas de tabla que entran una tras otra
    document.querySelectorAll('.tabla tbody').forEach((tb) => {
        [...tb.rows].forEach((tr, i) => tr.style.setProperty('--i', Math.min(i, 14)));
    });

    // Resaltar por color: tarjetas, filas, leyendas y gráficas hablan el mismo idioma
    const enfocar = (raiz, nombre) => {
        raiz.querySelectorAll('svg [data-r]').forEach((n) => {
            const propio = !!nombre && n.dataset.r === nombre;
            n.classList.toggle('atenuado', !!nombre && !propio);
            n.classList.toggle('resaltado', propio);
        });
        raiz.querySelectorAll('.ley-chip, .semi-card, tr[data-r]').forEach((n) => {
            n.classList.toggle('foco', !!nombre && n.dataset.r === nombre);
            n.classList.toggle('apagada', !!nombre && n.dataset.r !== nombre);
        });
    };
    if (zonaPasos) {
        const objetivo = (e) => e.target.closest('[data-r]');
        zonaPasos.addEventListener('pointerover', (e) => {
            const el = objetivo(e);
            const paso = el && el.closest('.paso');
            if (e.pointerType === 'touch') {      // con el dedo no hay «salir»: se limpia al tocar otra cosa
                zonaPasos.querySelectorAll('.paso').forEach((p) => { if (!p.dataset.fijo && p !== paso) enfocar(p, null); });
            }
            if (paso && !paso.dataset.fijo) enfocar(paso, el.dataset.r);
        });
        zonaPasos.addEventListener('pointerout', (e) => {
            if (e.pointerType === 'touch') return;
            const el = objetivo(e);
            const paso = el && el.closest('.paso');
            if (paso && !paso.dataset.fijo && !(e.relatedTarget && el.contains(e.relatedTarget))) enfocar(paso, null);
        });
        zonaPasos.addEventListener('click', (e) => {
            const chip = e.target.closest('.ley-chip');
            if (!chip) return;
            const paso = chip.closest('.paso');
            const mismo = paso.dataset.fijo === chip.dataset.r;
            paso.querySelectorAll('.ley-chip').forEach((c) => c.setAttribute('aria-pressed', 'false'));
            if (mismo) { delete paso.dataset.fijo; enfocar(paso, null); return; }
            paso.dataset.fijo = chip.dataset.r;
            chip.setAttribute('aria-pressed', 'true');
            enfocar(paso, chip.dataset.r);
        });

        // Vértices: una fila o un chip ilumina el punto en todas las gráficas
        const marcarPunto = (clave, on) => {
            zonaPasos.querySelectorAll('[data-p]').forEach((n) => {
                n.classList.toggle('foco-punto', on && n.dataset.p === clave);
            });
        };
        zonaPasos.addEventListener('pointerover', (e) => {
            const el = e.target.closest('[data-p]');
            if (e.pointerType === 'touch') marcarPunto(el ? el.dataset.p : null, !!el);
            else if (el) marcarPunto(el.dataset.p, true);
        });
        zonaPasos.addEventListener('pointerout', (e) => {
            if (e.pointerType === 'touch') return;
            const el = e.target.closest('[data-p]');
            if (el) marcarPunto(el.dataset.p, false);
        });
    }

    // Números que "corren" hasta su valor cuando entran en pantalla
    const contar = (nodo) => {
        const meta = parseFloat(nodo.dataset.contar);
        const final = nodo.dataset.final;
        if (sinMovimiento || !Number.isFinite(meta)) return;
        const entero = Number.isInteger(meta);
        const t0 = performance.now();
        const dur = 1800;
        const paso = (t) => {
            const k = Math.min(1, (t - t0) / dur);
            const v = meta * (1 - Math.pow(1 - k, 4));
            nodo.textContent = entero ? Math.round(v).toString() : v.toFixed(2);
            if (k < 1) requestAnimationFrame(paso); else nodo.textContent = final;
        };
        requestAnimationFrame(paso);
    };
    const contadores = document.querySelectorAll('[data-contar]');
    if ('IntersectionObserver' in window && !sinMovimiento) {
        contadores.forEach((n) => { n.textContent = n.dataset.contar.includes('.') ? '0.00' : '0'; });
        const verContador = new IntersectionObserver((entradas) => {
            entradas.forEach((en) => {
                if (en.isIntersecting) { contar(en.target); verContador.unobserve(en.target); }
            });
        }, { threshold: 0.6 });
        contadores.forEach((n) => verContador.observe(n));
    }

    window.addEventListener('beforeprint', () => contadores.forEach((n) => { n.textContent = n.dataset.final; }));

    // Foco de luz que sigue al mouse (tarjetas) e inclinación suave de las cifras
    document.addEventListener('pointermove', (e) => {
        const tarjeta = e.target.closest('.semi-card, .decision-card');
        if (!tarjeta) return;
        const r = tarjeta.getBoundingClientRect();
        tarjeta.style.setProperty('--mx', `${e.clientX - r.left}px`);
        tarjeta.style.setProperty('--my', `${e.clientY - r.top}px`);
        if (tarjeta.classList.contains('decision-card') && !sinMovimiento) {
            const rx = ((e.clientY - r.top) / r.height - 0.5) * -6;
            const ry = ((e.clientX - r.left) / r.width - 0.5) * 8;
            tarjeta.style.transform = `perspective(700px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateY(-3px)`;
        }
    }, { passive: true });
    document.addEventListener('pointerout', (e) => {
        const tarjeta = e.target.closest('.decision-card');
        if (tarjeta && !tarjeta.contains(e.relatedTarget)) tarjeta.style.transform = '';
    });

    // La escena del estado vacío se inclina suavemente siguiendo el mouse
    document.querySelectorAll('[data-escena]').forEach((escena) => {
        const caja = escena.closest('.vacio') || escena;
        if (sinMovimiento) return;
        caja.addEventListener('pointermove', (e) => {
            const r = caja.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
            escena.style.setProperty('--ry', `${(x * 10).toFixed(2)}deg`);
            escena.style.setProperty('--rx', `${(-y * 8).toFixed(2)}deg`);
        }, { passive: true });
        caja.addEventListener('pointerleave', () => { escena.style.setProperty('--rx', '0deg'); escena.style.setProperty('--ry', '0deg'); });
    });

    // Volver arriba
    if (botonArriba) {
        botonArriba.addEventListener('click', () => window.scrollTo({ top: 0, behavior: sinMovimiento ? 'auto' : 'smooth' }));
    }

    // Confeti cuando se encuentra el óptimo
    const festejo = document.querySelector('[data-festejo]');
    if (festejo && !sinMovimiento) {
        const colores = ['#2563eb', '#ea580c', '#9333ea', '#16a34a', '#e11d48', '#ca8a04', '#0891b2'];
        const capa = document.createElement('div');
        capa.className = 'confeti';
        capa.setAttribute('aria-hidden', 'true');
        for (let i = 0; i < 34; i++) {
            const pieza = document.createElement('i');
            pieza.style.cssText = `left:${Math.random() * 100}%;background:${colores[i % colores.length]};` +
                `animation-delay:${(Math.random() * 0.5).toFixed(2)}s;animation-duration:${(1.8 + Math.random() * 1.6).toFixed(2)}s;` +
                `--giro:${Math.round(Math.random() * 720 - 360)}deg;--deriva:${Math.round(Math.random() * 160 - 80)}px;`;
            capa.append(pieza);
        }
        document.body.append(capa);
        setTimeout(() => capa.remove(), 4200);
    }

    // Recta de Z interactiva
    const figZ = document.querySelector('[data-figura-z]');
    if (figZ && figZ.querySelector('[data-z-control]')) {
        const svg = figZ.querySelector('svg.grafica-svg');
        const d = svg.dataset;
        const rango = figZ.querySelector('.z-rango');
        const lectura = figZ.querySelector('.z-valor');
        const estado = figZ.querySelector('.z-estado');
        const recta = svg.querySelector('#iso-movil');
        let geo = {};
        try { geo = JSON.parse(d.geo || '{}'); } catch (err) { geo = {}; }
        const [ML, MT, PW, PH] = [geo.ml ?? 58, geo.mt ?? 36, geo.pw ?? 598, geo.ph ?? 396];
        const X = +d.xmax, Y = +d.ymax, zx = +d.zx, zy = +d.zy, zk = +d.zk;
        const zmin = +d.zmin, zmax = +d.zmax;
        const lo = d.zlo === '' ? null : +d.zlo;
        const hi = d.zhi === '' ? null : +d.zhi;
        const zopt = d.zopt === '' ? null : +d.zopt;
        const eps = Math.max(1e-9, (zmax - zmin) * 0.004);
        const num = (v) => String(Number(v.toFixed(4)));

        rango.min = zmin; rango.max = zmax;
        rango.step = (zmax - zmin) / 600 || 'any';
        rango.value = zopt !== null ? zopt : (zmin + zmax) / 2;

        const segmento = (z) => {
            const c = z - zk, pts = [];
            if (zy !== 0) for (const x of [0, X]) { const y = (c - zx * x) / zy; if (y >= -1e-9 && y <= Y + 1e-9) pts.push([x, Math.min(Math.max(y, 0), Y)]); }
            if (zx !== 0) for (const y of [0, Y]) { const x = (c - zy * y) / zx; if (x >= -1e-9 && x <= X + 1e-9) pts.push([Math.min(Math.max(x, 0), X), y]); }
            if (pts.length < 2) return null;
            let mejor = null, dm = -1;
            for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
                const dist = (pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2;
                if (dist > dm) { dm = dist; mejor = [pts[i], pts[j]]; }
            }
            return dm > 0 ? mejor : null;
        };

        const dibujar = (z) => {
            const seg = segmento(z);
            const dentro = (lo === null || z >= lo - eps) && (hi === null || z <= hi + eps);
            const esOptimo = zopt !== null && Math.abs(z - zopt) <= eps;
            if (seg) {
                const [[x0, y0], [x1, y1]] = seg;
                recta.setAttribute('x1', ML + x0 / X * PW); recta.setAttribute('y1', MT + PH - y0 / Y * PH);
                recta.setAttribute('x2', ML + x1 / X * PW); recta.setAttribute('y2', MT + PH - y1 / Y * PH);
            }
            recta.setAttribute('class', `iso-movil estado-${esOptimo ? 'opt' : dentro ? 'ok' : 'fuera'}`);
            recta.setAttribute('opacity', seg ? '1' : '0');
            lectura.textContent = `Z = ${num(z)}`;
            figZ.dataset.zEstado = esOptimo ? 'optimo' : dentro ? 'dentro' : 'fuera';
            if (esOptimo) {
                estado.textContent = '★ ¡Este es el óptimo! Es el último valor de Z que todavía toca la región.';
            } else if (dentro) {
                estado.textContent = '✔ La recta toca la región: hay puntos factibles que dan este Z.';
            } else if (hi !== null && z > hi) {
                estado.textContent = '✘ La recta ya salió de la región: ningún punto factible llega a un Z tan alto.';
            } else {
                estado.textContent = '✘ La recta está fuera de la región: ningún punto factible da un Z tan bajo.';
            }
        };

        rango.addEventListener('input', () => {
            let z = +rango.value;
            if (zopt !== null && Math.abs(z - zopt) <= eps * 1.5) { z = zopt; rango.value = zopt; }   // imán al óptimo
            dibujar(z);
        });
        const botonOptimo = figZ.querySelector('[data-z-optimo]');
        const botonAnimar = figZ.querySelector('[data-z-animar]');
        let animacion = 0;
        const detener = () => {
            if (animacion) cancelAnimationFrame(animacion);
            animacion = 0;
            if (botonAnimar) { botonAnimar.textContent = '▶ Animar'; botonAnimar.setAttribute('aria-pressed', 'false'); }
        };
        if (zopt === null) botonOptimo.hidden = true;
        botonOptimo.addEventListener('click', () => { detener(); rango.value = zopt; dibujar(zopt); });
        rango.addEventListener('pointerdown', detener);
        // La recta parte del lado «peor» de la región y avanza en la dirección en que Z mejora
        if (botonAnimar) botonAnimar.addEventListener('click', () => {
            if (animacion) { detener(); return; }
            const maximizar = d.tipo === 'max';
            const inicio = maximizar ? (lo !== null ? Math.max(zmin, lo - (zmax - zmin) * 0.12) : zmin)
                                     : (hi !== null ? Math.min(zmax, hi + (zmax - zmin) * 0.12) : zmax);
            const fin = zopt !== null ? zopt : (maximizar ? zmax : zmin);
            if (sinMovimiento) { rango.value = fin; dibujar(fin); return; }
            botonAnimar.textContent = '■ Detener';
            botonAnimar.setAttribute('aria-pressed', 'true');
            const t0 = performance.now(), dur = 3200;
            const paso = (t) => {
                const k = Math.min(1, (t - t0) / dur);
                const suave = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
                const z = inicio + (fin - inicio) * suave;
                rango.value = z;
                dibujar(k === 1 ? fin : z);
                if (k < 1) animacion = requestAnimationFrame(paso); else detener();
            };
            animacion = requestAnimationFrame(paso);
        });
        lectura.textContent = 'Z = mueve el control';
        estado.textContent = 'Desliza hacia la derecha o izquierda y mira cuándo la recta sale de la región.';
    }

    // Ondas al pulsar botones
    document.addEventListener('pointerdown', (e) => {
        const b = e.target.closest('.btn-principal, .btn-ia, .btn-sec, .chip');
        if (!b || b.disabled || sinMovimiento) return;
        const r = b.getBoundingClientRect();
        const onda = document.createElement('span');
        onda.className = 'onda';
        onda.style.left = `${e.clientX - r.left}px`;
        onda.style.top = `${e.clientY - r.top}px`;
        b.append(onda);
        setTimeout(() => onda.remove(), 650);
    });

    const botonCopiar = document.querySelector('#btn-copiar');
    if (botonCopiar) botonCopiar.addEventListener('click', async () => {
        const aviso = document.querySelector('#aviso-copiado');
        const texto = botonCopiar.dataset.texto;
        try {
            await navigator.clipboard.writeText(texto);
        } catch (err) {
            const aux = document.createElement('textarea');
            aux.value = texto; document.body.append(aux); aux.select();
            document.execCommand('copy'); aux.remove();
        }
        aviso.textContent = '✔ Copiada: ya puedes pegarla en tu informe';
        aviso.classList.add('visible');
        setTimeout(() => aviso.classList.remove('visible'), 2600);
    });

    const botonImprimir = document.querySelector('#btn-imprimir');
    if (botonImprimir) botonImprimir.addEventListener('click', () => {
        document.querySelectorAll('[data-paso]').forEach((p) => p.classList.add('visible'));
        setTimeout(() => window.print(), 80);
    });


    // ═══ Movimiento al estilo de llanostudio.co ══════════════════════
    // Revelado con desenfoque: sube 34 px, se aclara y se enfoca con una curva expo-out larga.
    const grupos = [
        '.panel-form form > .bloque', '.modelo li', '.semi-grid > *', '.chips-vert > *',
        '.decision-grid > *', '.recursos > .recurso', '.concl-texto > p', '.concl-caja', '.concl-acciones',
        '.nombres-vars > *',
    ];
    grupos.forEach((sel) => document.querySelectorAll(sel).forEach((n, i) => {
        n.dataset.in = '';
        n.style.setProperty('--d', `${Math.min(i, 9) * 0.07}s`);
    }));
    const revelables = document.querySelectorAll('[data-in]');
    const revelado = (n) => {
        n.classList.add('is-in');
        // Al terminar, se libera el elemento para que sus transiciones normales (hover) vuelvan a ser rápidas
        const espera = 1400 + (parseFloat(n.style.getPropertyValue('--d')) || 0) * 1000;
        setTimeout(() => { n.removeAttribute('data-in'); n.classList.remove('is-in'); n.style.removeProperty('--d'); }, espera);
    };
    if (sinMovimiento || !('IntersectionObserver' in window)) {
        revelables.forEach((n) => n.removeAttribute('data-in'));
    } else {
        const verRevelable = new IntersectionObserver((entradas) => entradas.forEach((en) => {
            if (en.isIntersecting) { revelado(en.target); verRevelable.unobserve(en.target); }
        }), { rootMargin: '0px 0px -6% 0px', threshold: 0.1 });
        revelables.forEach((n) => verRevelable.observe(n));
    }

    // Título del hero: palabra por palabra
    document.querySelectorAll('[data-palabras]').forEach((titulo) => {
        let i = 0;
        const envolver = (nodo) => {
            [...nodo.childNodes].forEach((hijo) => {
                if (hijo.nodeType === 3) {
                    const frag = document.createDocumentFragment();
                    hijo.textContent.split(/(\s+)/).forEach((trozo) => {
                        if (!trozo) return;
                        if (/^\s+$/.test(trozo)) { frag.append(' '); return; }
                        const pal = document.createElement('span');
                        pal.className = 'pal';
                        const dentro = document.createElement('span');
                        dentro.textContent = trozo;
                        dentro.style.setProperty('--i', i++);
                        pal.append(dentro);
                        frag.append(pal);
                    });
                    hijo.replaceWith(frag);
                } else if (hijo.nodeType === 1) envolver(hijo);
            });
        };
        envolver(titulo);
        titulo.classList.add('lista');
    });


    // Globo de puntos que gira (solo se anima mientras se ve)
    document.querySelectorAll('.cg-globe').forEach((lienzo) => {
        const ctx = lienzo.getContext('2d');
        if (!ctx) return;
        const N = 900, puntos = [];
        for (let t = 0; t < N; t++) {
            const y = 1 - (t / (N - 1)) * 2, r = Math.sqrt(1 - y * y), a = t * Math.PI * (3 - Math.sqrt(5));
            puntos.push([Math.cos(a) * r, y, Math.sin(a) * r]);
        }
        let ancho = 0, alto = 0, giro = 0, cuadro = 0, visible = false, velocidad = 0.0016;
        let tinta = '#1a1a2e', verde = '#16a34a';
        const leerColores = () => {
            const cs = getComputedStyle(document.documentElement);
            tinta = cs.getPropertyValue('--tinta').trim() || tinta;
            verde = cs.getPropertyValue('--verde').trim() || verde;
        };
        const medir = () => {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            ancho = lienzo.clientWidth; alto = lienzo.clientHeight;
            lienzo.width = ancho * dpr; lienzo.height = alto * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        const dibujar = () => {
            ctx.clearRect(0, 0, ancho, alto);
            const R = Math.min(ancho, alto) * 0.42, cx = ancho / 2, cy = alto / 2;
            const c = Math.cos(giro), s = Math.sin(giro), tc = Math.cos(0.32), ts = Math.sin(0.32);
            for (const [x, y, z] of puntos) {
                const X = x * c + z * s, Z = -x * s + z * c, Y = y * tc - Z * ts;
                const q = (y * ts + Z * tc + 1) / 2;
                ctx.globalAlpha = 0.1 + q * 0.7;
                ctx.fillStyle = q > 0.86 ? verde : tinta;
                const tam = 0.7 + q * 1.3;
                ctx.fillRect(cx + X * R, cy + Y * R, tam, tam);
            }
            ctx.globalAlpha = 1;
        };
        const paso = () => {
            giro += velocidad;
            velocidad += (0.0016 - velocidad) * 0.04;     // vuelve a su ritmo tras acelerar con el mouse
            dibujar();
            cuadro = visible ? requestAnimationFrame(paso) : 0;
        };
        leerColores(); medir(); dibujar();
        window.addEventListener('cambio-tema', () => { setTimeout(() => { leerColores(); dibujar(); }, 60); });
        lienzo.parentElement.addEventListener('pointermove', (e) => {
            const r = lienzo.getBoundingClientRect();
            velocidad = 0.0016 + Math.abs((e.clientX - r.left) / r.width - 0.5) * 0.012;
        });
        if (!sinMovimiento) {
            new IntersectionObserver(([en]) => {
                visible = en.isIntersecting;
                if (visible && !cuadro) cuadro = requestAnimationFrame(paso);
            }).observe(lienzo);
        }
        window.addEventListener('resize', () => { medir(); dibujar(); });
    });

    // «Resolver otro ejercicio» abre la página en blanco (?nuevo=1): se limpia la dirección y se enfoca el enunciado
    if (new URLSearchParams(location.search).has('nuevo')) {
        history.replaceState(null, '', location.pathname);
        setTimeout(() => form.querySelector('#contexto').focus(), 250);
    }

    // Al volver con «atrás» el navegador conserva la página: se quitan los estados de «cargando»
    window.addEventListener('pageshow', (e) => {
        if (!e.persisted) return;
        document.querySelectorAll('.cargando').forEach((b) => b.classList.remove('cargando'));
        document.querySelectorAll('.btn-ia').forEach((b) => { b.disabled = false; });
    });

    // Tras calcular, llevar la vista al resultado (útil en pantallas pequeñas)
    const resumen = document.querySelector('.resumen');
    if (resumen && window.matchMedia('(max-width: 960px)').matches) {
        resumen.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ═══ Enlace para compartir: abre este mismo ejercicio ya resuelto ═══
    const botonEnlace = document.querySelector('#btn-enlace');
    const avisoEnlace = document.querySelector('#aviso-enlace');
    if (avisoEnlace) document.body.append(avisoEnlace);   // fuera de contenedores con overflow o transform
    const avisar = (texto) => {
        if (!avisoEnlace) return;
        avisoEnlace.textContent = texto;
        avisoEnlace.classList.add('visible');
        clearTimeout(avisar.t);
        avisar.t = setTimeout(() => avisoEnlace.classList.remove('visible'), 2600);
    };
    const copiarTexto = async (texto) => {
        try {
            await navigator.clipboard.writeText(texto);
            return true;
        } catch (err) {
            const aux = document.createElement('textarea');
            aux.value = texto; aux.setAttribute('readonly', ''); aux.style.cssText = 'position:fixed;opacity:0';
            document.body.append(aux); aux.select();
            let ok = false;
            try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
            aux.remove();
            return ok;
        }
    };
    if (botonEnlace) botonEnlace.addEventListener('click', async () => {
        const datos = new URLSearchParams();
        for (const [nombre, valor] of new FormData(form)) {
            if (nombre === 'extraccion' || (nombre === 'contexto' && valor.length > 1200)) continue;
            if (valor !== '' || nombre.endsWith('[]')) datos.append(nombre, valor);
        }
        const url = `${location.origin}${location.pathname}?${datos.toString()}`;
        if (navigator.share && matchMedia('(hover: none)').matches) {
            try { await navigator.share({ title: 'Método gráfico · OptiLab', url }); return; } catch (err) { /* cancelado: se copia */ }
        }
        avisar(await copiarTexto(url) ? '✔ Enlace copiado: ábrelo para ver este ejercicio resuelto' : 'No se pudo copiar el enlace');
    });


    // ═══ Explorador de gráficas ══════════════════════════════════════
    // Señala (o toca) cualquier punto: coordenadas, si es factible, qué restricción viola y cuánto vale Z.
    const NS = 'http://www.w3.org/2000/svg';
    const nodoSvg = (tag, attrs = {}) => {
        const n = document.createElementNS(NS, tag);
        Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
        return n;
    };
    const num2 = (v) => {
        const r = Math.round(v * 100) / 100;
        return (Object.is(r, -0) ? 0 : r).toString();
    };
    const exploradores = new Set();

    const explorar = (svg) => {
        let geo;
        try { geo = JSON.parse(svg.dataset.geo); } catch (err) { return; }
        if (!geo || !geo.X || !geo.Y) return;
        const { ml, mt, pw, ph, X, Y } = geo;
        const [zx, zy, zk] = geo.z;
        const conZ = ['region', 'vertices', 'optimo'].includes(geo.etapa) && (zx !== 0 || zy !== 0);

        const capa = nodoSvg('g', { class: 'explorador', 'aria-hidden': 'true' });
        const guiaX = nodoSvg('line', { class: 'exp-guia' });
        const guiaY = nodoSvg('line', { class: 'exp-guia' });
        const punto = nodoSvg('circle', { class: 'exp-punto', r: 6 });
        const globo = nodoSvg('g', { class: 'exp-globo' });
        const fondo = nodoSvg('rect', { class: 'exp-fondo', rx: 9 });
        const texto = nodoSvg('text', { class: 'exp-txt' });
        globo.append(fondo, texto);
        capa.append(guiaX, guiaY, punto, globo);
        svg.append(capa);

        const aPx = (x, y) => [ml + x / X * pw, mt + ph - y / Y * ph];
        const aDatos = (px, py) => [(px - ml) / pw * X, (mt + ph - py) / ph * Y];
        const evaluar = (r, x, y) => r[0] * x + r[1] * y;
        // Distancia en unidades del SVG entre (x, y) y la recta de r (para «sobre la recta» en igualdades)
        const distancia = (r, x, y) => Math.abs(evaluar(r, x, y) - r[3]) / (Math.hypot(r[0] * X / pw, r[1] * Y / ph) || 1);
        const cumple = (r, x, y) => {
            const v = evaluar(r, x, y), tol = 1e-9 * (1 + Math.abs(r[3]));
            if (r[2] === '<=') return v <= r[3] + tol;
            if (r[2] === '>=') return v >= r[3] - tol;
            return distancia(r, x, y) <= 3;
        };
        const simbolo = { '<=': '≤', '>=': '≥', '=': '=' };

        const ocultar = () => capa.classList.remove('activo');

        const mostrar = (e) => {
            const ctm = svg.getScreenCTM();
            if (!ctm) return;
            const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
            if (p.x < ml - 6 || p.x > ml + pw + 6 || p.y < mt - 6 || p.y > mt + ph + 6) { ocultar(); return; }
            let [x, y] = aDatos(Math.min(Math.max(p.x, ml), ml + pw), Math.min(Math.max(p.y, mt), mt + ph));
            x = Math.max(0, x); y = Math.max(0, y);

            // Imán: cerca de un vértice, se muestra el vértice exacto
            const radio = (e.pointerType === 'touch' ? 26 : 14) / (ctm.a || 1);
            let vertice = null;
            for (const v of geo.vertices) {
                const [vx, vy] = aPx(v[0], v[1]);
                const dist = Math.hypot(vx - p.x, vy - p.y);
                if (dist <= radio && (!vertice || dist < vertice.dist)) vertice = { v, dist };
            }
            if (vertice) { x = vertice.v.at(0); y = vertice.v.at(1); }

            const lineas = [];
            lineas.push(vertice ? `Vértice (${vertice.v[2]}, ${vertice.v[3]})` : `X1 = ${num2(x)} · X2 = ${num2(y)}`);
            const violadas = geo.contradiccion ? ['—'] : geo.rectas.filter((r) => !cumple(r, x, y)).map((r) => r[4]);
            let estado = 'ok';
            if (geo.etapa === 'semiplano' && geo.rectas.length) {
                const r = geo.rectas[0];
                const ok = cumple(r, x, y);
                estado = ok ? 'ok' : 'mal';
                lineas.push(`${r[4]}: ${num2(evaluar(r, x, y))} ${ok ? simbolo[r[2]] : (r[2] === '<=' ? '>' : r[2] === '>=' ? '<' : '≠')} ${num2(r[3])} ${ok ? '✔' : '✘'}`);
            } else if (geo.rectas.length || geo.contradiccion) {
                estado = violadas.length ? 'mal' : 'ok';
                if (geo.contradiccion) lineas.push('✘ Ningún punto es factible');
                else lineas.push(violadas.length ? `✘ Viola ${violadas.join(', ')}` : '✔ Cumple todas: factible');
            }
            if (conZ) lineas.push(vertice ? `Z = ${vertice.v[4]}${vertice.v[5] ? ' ★ óptimo' : ''}` : `Z = ${num2(zx * x + zy * y + zk)}`);

            const [px, py] = aPx(x, y);
            guiaX.setAttribute('x1', ml); guiaX.setAttribute('x2', px); guiaX.setAttribute('y1', py); guiaX.setAttribute('y2', py);
            guiaY.setAttribute('x1', px); guiaY.setAttribute('x2', px); guiaY.setAttribute('y1', mt + ph); guiaY.setAttribute('y2', py);
            punto.setAttribute('cx', px); punto.setAttribute('cy', py);
            capa.dataset.estado = vertice ? 'vertice' : estado;

            texto.textContent = '';
            lineas.forEach((t, i) => {
                const tsp = nodoSvg('tspan', { x: 0, dy: i ? '1.3em' : '0', class: i ? '' : 'exp-cabeza' });
                tsp.textContent = t;
                texto.append(tsp);
            });
            capa.classList.add('activo');
            const caja = texto.getBBox();
            const pad = Math.max(8, caja.height * 0.12);
            const ancho = caja.width + pad * 2, alto = caja.height + pad * 2;
            // Globo arriba a la derecha del punto; se voltea si no cabe
            let gx = px + 14, gy = py - 14 - alto;
            if (gx + ancho > ml + pw + 20) gx = px - 14 - ancho;
            if (gy < 2) gy = py + 14;
            fondo.setAttribute('x', caja.x - pad); fondo.setAttribute('y', caja.y - pad);
            fondo.setAttribute('width', ancho); fondo.setAttribute('height', alto);
            globo.setAttribute('transform', `translate(${(gx - caja.x + pad).toFixed(1)},${(gy - caja.y + pad).toFixed(1)})`);
        };

        svg.addEventListener('pointermove', (e) => { if (e.pointerType !== 'touch' || svg.closest('.visor')) mostrar(e); });
        svg.addEventListener('pointerdown', mostrar);
        svg.addEventListener('pointerleave', (e) => { if (e.pointerType !== 'touch') ocultar(); });
        exploradores.add({ svg, ocultar });
    };
    document.querySelectorAll('svg.grafica-svg[data-geo]').forEach(explorar);
    // Con el dedo el globo se queda hasta tocar fuera de la gráfica
    document.addEventListener('pointerdown', (e) => {
        exploradores.forEach(({ svg, ocultar }) => { if (!svg.contains(e.target)) ocultar(); });
    });


    // ═══ Visor a pantalla completa + descarga en PNG ═════════════════
    const PROPIEDADES = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
        'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'opacity', 'font-family', 'font-size',
        'font-weight', 'paint-order', 'display', 'visibility', 'text-anchor'];

    // Copia «autónoma» del SVG: los estilos (variables CSS, tema, clases) quedan escritos en cada nodo.
    // Siempre en tema claro (fondo blanco), que es lo que se pega en un informe o se imprime.
    // Todo ocurre en el mismo cuadro, así que el cambio momentáneo de tema no llega a verse.
    const svgAutonomo = (svg) => {
        const temaPrevio = raiz.dataset.tema;
        raiz.dataset.tema = 'claro';
        try { return svgAutonomoEnTemaActual(svg); } finally { raiz.dataset.tema = temaPrevio; }
    };
    const svgAutonomoEnTemaActual = (svg) => {
        const lienzo = document.createElement('div');
        lienzo.className = 'lienzo-export';
        const vivo = svg.cloneNode(true);
        vivo.querySelectorAll('.explorador').forEach((n) => n.remove());
        lienzo.append(vivo);
        document.body.append(lienzo);
        const copia = vivo.cloneNode(true);
        const origen = [vivo, ...vivo.querySelectorAll('*')];
        const destino = [copia, ...copia.querySelectorAll('*')];
        origen.forEach((n, i) => {
            const cs = getComputedStyle(n);
            const estilo = PROPIEDADES.map((prop) => `${prop}:${cs.getPropertyValue(prop)}`).join(';');
            destino[i].setAttribute('style', estilo);
            destino[i].removeAttribute('class');
        });
        const fondo = getComputedStyle(vivo).backgroundColor;
        lienzo.remove();
        copia.removeAttribute('data-geo');
        copia.setAttribute('xmlns', NS);
        return { copia, fondo };
    };

    const descargarPng = async (svg, nombre) => {
        const { copia, fondo } = svgAutonomo(svg);
        const [, , w, h] = (svg.getAttribute('viewBox') || '0 0 680 470').split(/\s+/).map(Number);
        const escala = 2;
        copia.setAttribute('width', w * escala);
        copia.setAttribute('height', h * escala);
        const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copia)], { type: 'image/svg+xml;charset=utf-8' }));
        try {
            const img = new Image();
            await new Promise((ok, mal) => { img.onload = ok; img.onerror = mal; img.src = url; });
            const canvas = document.createElement('canvas');
            canvas.width = w * escala; canvas.height = h * escala;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = fondo && fondo !== 'rgba(0, 0, 0, 0)' ? fondo : '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);
            const blob = await new Promise((ok) => canvas.toBlob(ok, 'image/png'));
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${nombre}.png`;
            document.body.append(a); a.click(); a.remove();
            setTimeout(() => URL.revokeObjectURL(a.href), 4000);
            return true;
        } catch (err) {
            return false;
        } finally {
            URL.revokeObjectURL(url);
        }
    };

    const nombreArchivo = (figura) => {
        const paso = figura.closest('.paso');
        const tarjeta = figura.closest('.semi-card');
        const base = paso ? paso.id.replace('paso-', '') : 'grafica';
        return `metodo-grafico-${base}${tarjeta ? '-' + tarjeta.dataset.r : ''}`;
    };

    let visor = null;
    const abrirVisor = (figura) => {
        const svg = figura.querySelector('svg.grafica-svg');
        if (!svg) return;
        if (!visor) {
            visor = document.createElement('dialog');
            visor.className = 'visor';
            visor.setAttribute('aria-label', 'Gráfica ampliada');
            visor.innerHTML = '<div class="visor-cab"><b class="visor-titulo"></b><span class="visor-acciones">'
                + '<button type="button" class="chip" data-v-descargar>↓ Descargar PNG</button>'
                + '<button type="button" class="visor-cerrar" data-v-cerrar aria-label="Cerrar">×</button></span></div>'
                + '<div class="visor-cuerpo"></div><p class="visor-ayuda"></p>';
            document.body.append(visor);
            visor.addEventListener('click', (e) => {
                if (e.target === visor || e.target.closest('[data-v-cerrar]')) visor.close();
                const chip = e.target.closest('.ley-chip');
                if (chip) {
                    const activo = chip.getAttribute('aria-pressed') === 'true';
                    visor.querySelectorAll('.ley-chip').forEach((c) => c.setAttribute('aria-pressed', 'false'));
                    chip.setAttribute('aria-pressed', activo ? 'false' : 'true');
                    enfocar(visor, activo ? null : chip.dataset.r);
                }
            });
            visor.addEventListener('close', () => {
                document.documentElement.classList.remove('con-visor');
                visor.querySelector('.visor-cuerpo').innerHTML = '';
                exploradores.forEach((ex) => { if (!ex.svg.isConnected) exploradores.delete(ex); });
                if (visor.origen) visor.origen.focus({ preventScroll: true });
            });
            visor.querySelector('[data-v-descargar]').addEventListener('click', async (e) => {
                const boton = e.currentTarget;
                boton.disabled = true;
                const ok = await descargarPng(visor.querySelector('.visor-cuerpo svg'), visor.dataset.archivo);
                boton.disabled = false;
                if (!ok) boton.textContent = 'No se pudo descargar';
            });
        }
        const paso = figura.closest('.paso');
        const tarjeta = figura.closest('.semi-card');
        const titulo = tarjeta ? `${tarjeta.dataset.r}: ${tarjeta.querySelector('header code').textContent}`
            : (paso ? paso.querySelector('h3').textContent : 'Gráfica');
        visor.querySelector('.visor-titulo').textContent = titulo;
        visor.dataset.archivo = nombreArchivo(figura);
        const cuerpo = visor.querySelector('.visor-cuerpo');
        const copia = svg.cloneNode(true);
        copia.removeAttribute('id');
        copia.querySelectorAll('[id]').forEach((n) => { if (!n.matches('clipPath, pattern')) n.removeAttribute('id'); });
        copia.querySelectorAll('.explorador').forEach((n) => n.remove());
        copia.querySelectorAll('.atenuado, .resaltado').forEach((n) => n.classList.remove('atenuado', 'resaltado'));
        cuerpo.append(copia);
        const leyenda = (tarjeta ? null : figura.querySelector('.leyenda'));
        if (leyenda) {
            const ley = leyenda.cloneNode(true);
            ley.querySelectorAll('.ley-chip').forEach((c) => { c.setAttribute('aria-pressed', 'false'); c.classList.remove('foco', 'apagada'); });
            cuerpo.append(ley);
        }
        const ejes = figura.querySelector('.ejes-nombres');
        if (ejes) cuerpo.append(ejes.cloneNode(true));
        visor.querySelector('.visor-ayuda').textContent = matchMedia('(hover: none)').matches
            ? 'Toca o arrastra sobre la gráfica para ver las coordenadas de cualquier punto.'
            : 'Mueve el mouse sobre la gráfica para ver las coordenadas de cualquier punto. Esc para cerrar.';
        const boton = visor.querySelector('[data-v-descargar]');
        boton.textContent = '↓ Descargar PNG';
        visor.origen = document.activeElement;
        document.documentElement.classList.add('con-visor');
        if (typeof visor.showModal === 'function') visor.showModal(); else visor.setAttribute('open', '');
        explorar(copia);
    };

    // Botones «Ampliar» y «PNG» sobre cada gráfica
    document.querySelectorAll('.paso .figura, .semi-fig').forEach((figura) => {
        if (!figura.querySelector('svg.grafica-svg')) return;
        const herr = document.createElement('div');
        herr.className = 'fig-herr';
        herr.innerHTML = '<button type="button" data-ampliar title="Ver en grande" aria-label="Ampliar la gráfica">'
            + '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 3h5v5M8 17H3v-5M17 3l-6 6M3 17l6-6"/></svg><span>Ampliar</span></button>'
            + '<button type="button" data-descargar title="Descargar como imagen PNG" aria-label="Descargar la gráfica en PNG">'
            + '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M5.5 8.5 10 13l4.5-4.5M4 17h12"/></svg><span>PNG</span></button>';
        figura.classList.add('con-herr');
        figura.prepend(herr);
        herr.querySelector('[data-ampliar]').addEventListener('click', () => abrirVisor(figura));
        herr.querySelector('[data-descargar]').addEventListener('click', async (e) => {
            const boton = e.currentTarget;
            boton.disabled = true;
            const ok = await descargarPng(figura.querySelector('svg.grafica-svg'), nombreArchivo(figura));
            boton.disabled = false;
            if (!ok) avisar('No se pudo descargar la imagen');
        });
    });
});
