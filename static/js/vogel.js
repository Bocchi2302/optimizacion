/* Método de Vogel · OptiLab
   Misma capa de movimiento que el Método Gráfico (cabecera de cristal, progreso de lectura,
   riel de pasos, revelado con desenfoque, título palabra por palabra, cambio de tema circular),
   más la escena del camión que se inclina con el mouse y una red de rutas animada al final. */
document.addEventListener('DOMContentLoaded', () => {
    const raiz = document.documentElement;
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ═══ Modo claro / oscuro (el nuevo tema se abre en círculo desde el botón) ═══
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

    // ═══ Cabecera de cristal, progreso de lectura, riel de pasos y botón arriba ═══
    const barraProgreso = document.querySelector('#progreso-scroll');
    const cabecera = document.querySelector('.barra');
    const zonaPasos = document.querySelector('#pasos');
    const riel = document.querySelector('.riel-progreso');
    const botonArriba = document.querySelector('#btn-arriba');
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
    if (botonArriba) botonArriba.addEventListener('click', () => window.scrollTo({ top: 0, behavior: sinMovimiento ? 'auto' : 'smooth' }));

    // ═══ Pasos que aparecen al entrar en pantalla + índice activo ═══
    const pasos = [...document.querySelectorAll('[data-paso]')];
    const enlaces = new Map([...document.querySelectorAll('[data-nav]')].map((a) => [a.dataset.nav, a]));
    if ('IntersectionObserver' in window && !sinMovimiento) {
        const revelar = new IntersectionObserver((entradas) => entradas.forEach((en) => {
            if (en.isIntersecting) { en.target.classList.add('visible'); revelar.unobserve(en.target); }
        }), { threshold: 0.04 });
        pasos.forEach((p) => revelar.observe(p));
    } else {
        pasos.forEach((p) => p.classList.add('visible'));
    }
    const indice = document.querySelector('.indice');
    let navegando = 0;   // mientras dura un salto del índice, el resaltado no se mueve solo

    // Marca el enlace activo y lo centra DENTRO de la barra del índice. No se usa scrollIntoView:
    // también desplaza la página y cancelaba el salto en curso (se quedaba en la iteración 4).
    const marcarActivo = (id) => {
        const a = enlaces.get(id);
        if (!a || a.classList.contains('activo')) return;
        enlaces.forEach((otro) => otro.classList.remove('activo'));
        a.classList.add('activo');
        if (indice && indice.scrollWidth > indice.clientWidth) {
            indice.scrollTo({ left: a.offsetLeft - (indice.clientWidth - a.offsetWidth) / 2, behavior: 'auto' });
        }
    };
    if ('IntersectionObserver' in window) {
        const activo = new IntersectionObserver((entradas) => entradas.forEach((en) => {
            if (en.isIntersecting && !navegando) marcarActivo(en.target.id);
        }), { rootMargin: '-30% 0px -60% 0px' });
        pasos.forEach((p) => activo.observe(p));
    }

    // Salto a una sección: abre la iteración, calcula la posición bajo la cabecera y el índice fijos
    // y se desplaza una sola vez, sin que nada más interrumpa el movimiento.
    const irA = (id) => {
        const destino = document.getElementById(id);
        if (!destino) return;
        if (destino.tagName === 'DETAILS') destino.open = true;
        destino.classList.add('visible');
        // El índice se fija a la altura de su `top` (CSS); se usa esa medida, no su posición actual
        const fijoEn = indice ? parseFloat(getComputedStyle(indice).top) || 0 : (cabecera ? cabecera.offsetHeight : 0);
        const tapa = fijoEn + (indice ? indice.offsetHeight : 0) + 12;
        // Posición por layout (offsetTop): ignora el desplazamiento de 24 px de la animación de entrada,
        // que getBoundingClientRect sí incluye en las tarjetas que aún no se han mostrado
        let y = -tapa;
        for (let n = destino; n; n = n.offsetParent) y += n.offsetTop;
        marcarActivo(id);
        clearTimeout(navegando);
        navegando = setTimeout(() => { navegando = 0; }, sinMovimiento ? 50 : 1200);
        window.scrollTo({ top: Math.max(0, y), behavior: sinMovimiento ? 'auto' : 'smooth' });
        history.replaceState(null, '', `#${id}`);
    };
    document.querySelectorAll('.indice a, .subpaso a[href^="#"]').forEach((a) => a.addEventListener('click', (e) => {
        e.preventDefault();
        irA(a.getAttribute('href').slice(1));
    }));
    // Si la persona toma el control (rueda, toque, teclado), el resaltado vuelve a seguir la lectura
    ['wheel', 'touchstart', 'keydown'].forEach((ev) => window.addEventListener(ev, () => {
        if (navegando) { clearTimeout(navegando); navegando = 0; }
    }, { passive: true }));

    // Expandir / contraer iteraciones
    document.querySelectorAll('[data-todo]').forEach((boton) => boton.addEventListener('click', () => {
        const abrir = boton.dataset.todo === 'abrir';
        document.querySelectorAll('details.iteracion').forEach((d) => { d.open = abrir; });
    }));

    const botonImprimir = document.querySelector('#btn-imprimir');
    if (botonImprimir) botonImprimir.addEventListener('click', () => {
        document.querySelectorAll('details.iteracion').forEach((d) => { d.open = true; });
        pasos.forEach((p) => p.classList.add('visible'));
        setTimeout(() => window.print(), 80);
    });

    // ═══ Revelado con desenfoque (sube 34 px, se aclara y se enfoca) ═══
    ['.panel-form > .bloque', '.panel-form > .btn-principal', '.bloque-analisis'].forEach((sel) =>
        document.querySelectorAll(sel).forEach((n, i) => {
            n.dataset.in = '';
            n.style.setProperty('--d', `${Math.min(i, 9) * 0.07}s`);
        }));
    const revelables = document.querySelectorAll('[data-in]');
    const revelado = (n) => {
        n.classList.add('is-in');
        const espera = 1400 + (parseFloat(n.style.getPropertyValue('--d')) || 0) * 1000;
        setTimeout(() => { n.removeAttribute('data-in'); n.classList.remove('is-in'); n.style.removeProperty('--d'); }, espera);
    };
    if (sinMovimiento || !('IntersectionObserver' in window)) {
        revelables.forEach((n) => n.removeAttribute('data-in'));
    } else {
        const ver = new IntersectionObserver((entradas) => entradas.forEach((en) => {
            if (en.isIntersecting) { revelado(en.target); ver.unobserve(en.target); }
        }), { rootMargin: '0px 0px -6% 0px', threshold: 0.1 });
        revelables.forEach((n) => ver.observe(n));
    }

    // ═══ Título del hero: palabra por palabra ═══
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

    // ═══ La escena del camión se inclina siguiendo el mouse ═══
    const escena = document.querySelector('#escena');
    if (escena && !sinMovimiento && window.matchMedia('(hover: hover)').matches) {
        escena.addEventListener('pointermove', (e) => {
            const r = escena.getBoundingClientRect();
            const px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
            escena.style.setProperty('--ry', `${(px * 8).toFixed(2)}deg`);
            escena.style.setProperty('--rx', `${(-py * 6).toFixed(2)}deg`);
        });
        escena.addEventListener('pointerleave', () => {
            escena.style.setProperty('--ry', '0deg');
            escena.style.setProperty('--rx', '0deg');
        });
    }

    // ═══ Ondas al pulsar botones ═══
    document.addEventListener('pointerdown', (e) => {
        const b = e.target.closest('.btn-principal, .btn, .btn-cg');
        if (!b || b.disabled || sinMovimiento) return;
        const r = b.getBoundingClientRect();
        const onda = document.createElement('span');
        onda.className = 'onda';
        onda.style.left = `${e.clientX - r.left}px`;
        onda.style.top = `${e.clientY - r.top}px`;
        b.append(onda);
        setTimeout(() => onda.remove(), 650);
    });

    // ═══ Cierre: red de transporte con camiones en las rutas de la solución ═══
    document.querySelectorAll('.cg-red').forEach((lienzo) => {
        const ctx = lienzo.getContext('2d');
        let red = null;
        try { red = JSON.parse(lienzo.dataset.red || 'null'); } catch (err) { red = null; }
        if (!ctx || !red) return;
        const m = red.origenes.length, n = red.destinos.length;
        const maxCant = Math.max(1, ...red.rutas.map((r) => r.cantidad));
        // Varios camiones por ruta según la cantidad enviada, desfasados para que no viajen juntos
        const camiones = [];
        red.rutas.forEach((r, k) => {
            const cuantos = r.ficticia ? 0 : 1 + Math.round((r.cantidad / maxCant) * 2);
            for (let c = 0; c < cuantos; c++) camiones.push({ ruta: r, t: (c / cuantos + k * 0.13) % 1, v: 0.0022 + (k % 3) * 0.0004 });
        });
        let ancho = 0, alto = 0, cuadro = 0, visible = false, rapidez = 1;
        let colores = {};
        const leerColores = () => {
            const cs = getComputedStyle(raiz);
            const v = (nombre, def) => cs.getPropertyValue(nombre).trim() || def;
            colores = { tinta: v('--tinta', '#1f2430'), acento: v('--acento', '#004387'), dorado: v('--dorado', '#ffcc00'), tarjeta: v('--tarjeta', '#fff'), tinta3: v('--tinta-3', '#667085') };
        };
        const medir = () => {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            ancho = lienzo.clientWidth; alto = lienzo.clientHeight;
            lienzo.width = ancho * dpr; lienzo.height = alto * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        const nodo = (lado, k, total) => {
            const margenY = alto * 0.16;
            const y = total === 1 ? alto / 2 : margenY + (k * (alto - 2 * margenY)) / (total - 1);
            return { x: lado === 'o' ? Math.max(70, ancho * 0.1) : ancho - Math.max(70, ancho * 0.1), y };
        };
        const curva = (r, t) => {
            const a = nodo('o', r.i, m), b = nodo('d', r.j, n);
            const dx = (b.x - a.x) * 0.45, u = 1 - t;
            const x = u * u * u * a.x + 3 * u * u * t * (a.x + dx) + 3 * u * t * t * (b.x - dx) + t * t * t * b.x;
            const y = u * u * u * a.y + 3 * u * u * t * a.y + 3 * u * t * t * b.y + t * t * t * b.y;
            const ddx = 3 * u * u * dx + 6 * u * t * (b.x - dx - a.x - dx) + 3 * t * t * dx;
            const ddy = 6 * u * t * (b.y - a.y);
            return { x, y, ang: Math.atan2(ddy, ddx), a, b, dx };
        };
        const trazo = (a, b, dx) => {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.bezierCurveTo(a.x + dx, a.y, b.x - dx, b.y, b.x, b.y);
            ctx.stroke();
        };
        const camion = (x, y, ang) => {
            ctx.save();
            ctx.translate(x, y); ctx.rotate(ang);
            ctx.fillStyle = colores.dorado; ctx.fillRect(-10, -5, 13, 10);
            ctx.fillStyle = colores.acento; ctx.fillRect(3, -4.5, 7, 9);
            ctx.restore();
        };
        const dibujar = () => {
            ctx.clearRect(0, 0, ancho, alto);
            // Todas las rutas posibles, tenues
            ctx.strokeStyle = colores.tinta; ctx.globalAlpha = 0.07; ctx.lineWidth = 1;
            for (let i = 0; i < m; i++) for (let j = 0; j < n; j++) {
                const a = nodo('o', i, m), b = nodo('d', j, n);
                trazo(a, b, (b.x - a.x) * 0.45);
            }
            // Rutas de la solución: más gruesas cuanto más se envía
            red.rutas.forEach((r) => {
                const { a, b, dx } = curva(r, 0);
                ctx.globalAlpha = r.ficticia ? 0.18 : 0.42;
                ctx.strokeStyle = colores.acento;
                ctx.lineWidth = 1.5 + (r.cantidad / maxCant) * 4;
                ctx.setLineDash(r.ficticia ? [4, 6] : []);
                trazo(a, b, dx);
            });
            ctx.setLineDash([]); ctx.globalAlpha = 1;
            camiones.forEach((c) => { const p = curva(c.ruta, c.t); camion(p.x, p.y, p.ang); });
            // Nodos con su nombre
            ctx.font = '600 12px Inter, system-ui, sans-serif'; ctx.textBaseline = 'middle';
            [['o', m, red.origenes], ['d', n, red.destinos]].forEach(([lado, total, nombres]) => {
                nombres.forEach((nombre, k) => {
                    const p = nodo(lado, k, total);
                    ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, Math.PI * 2);
                    ctx.fillStyle = lado === 'o' ? colores.acento : colores.dorado; ctx.fill();
                    ctx.lineWidth = 3; ctx.strokeStyle = colores.tarjeta; ctx.stroke();
                    if (ancho > 520) {
                        ctx.fillStyle = colores.tinta3;
                        ctx.textAlign = lado === 'o' ? 'right' : 'left';
                        const texto = nombre.length > 16 ? `${nombre.slice(0, 15)}…` : nombre;
                        ctx.fillText(texto, p.x + (lado === 'o' ? -14 : 14), p.y);
                    }
                });
            });
        };
        const paso = () => {
            camiones.forEach((c) => { c.t = (c.t + c.v * rapidez) % 1; });
            rapidez += (1 - rapidez) * 0.04;
            dibujar();
            cuadro = visible ? requestAnimationFrame(paso) : 0;
        };
        leerColores(); medir(); dibujar();
        window.addEventListener('cambio-tema', () => setTimeout(() => { leerColores(); dibujar(); }, 60));
        window.addEventListener('resize', () => { medir(); dibujar(); });
        lienzo.parentElement.addEventListener('pointermove', (e) => {
            const r = lienzo.getBoundingClientRect();
            rapidez = 1 + Math.abs((e.clientX - r.left) / r.width - 0.5) * 5;
        });
        if (!sinMovimiento && 'IntersectionObserver' in window) {
            new IntersectionObserver(([en]) => {
                visible = en.isIntersecting;
                if (visible && !cuadro) cuadro = requestAnimationFrame(paso);
            }).observe(lienzo);
        }
    });

    // «Resolver otro ejercicio» abre la página en blanco (?nuevo=1): se limpia la dirección y se enfoca el contexto
    if (new URLSearchParams(location.search).has('nuevo')) {
        history.replaceState(null, '', location.pathname);
        setTimeout(() => document.querySelector('#contexto')?.focus(), 250);
    }
    // Al resolver, la página baja hasta el resultado una sola vez, y no lo hace si la persona
    // ya empezó a desplazarse (antes los dos movimientos peleaban y la página «brincaba»)
    const resultados = document.querySelector('#resultados');
    if (resultados && !location.hash) {
        // Cualquier movimiento previo (rueda, toque, teclado o un scroll que ya iba en curso al cargar)
        // cancela la bajada automática: la persona ya tomó el control.
        let tocado = window.scrollY > 2;
        const soltar = () => { tocado = true; };
        ['wheel', 'touchstart', 'keydown', 'pointerdown', 'scroll'].forEach((ev) => window.addEventListener(ev, soltar, { once: true, passive: true }));
        setTimeout(() => {
            if (tocado || window.scrollY > 2) return;
            const tapa = cabecera ? cabecera.offsetHeight + 8 : 8;
            window.scrollTo({ top: window.scrollY + resultados.getBoundingClientRect().top - tapa, behavior: sinMovimiento ? 'auto' : 'smooth' });
        }, 250);
    } else if (location.hash) {
        setTimeout(() => irA(location.hash.slice(1)), 100);
    }

    // ── Tabla de entrada ───────────────────────────────────────────────
    const tabla = document.querySelector('#tabla-entrada');
    const form = document.querySelector('#form-vogel');
    if (!tabla || !form) return;

    const limite = Number(tabla.dataset.max) || 10;
    const campoFilas = document.querySelector('#num-origenes');
    const campoColumnas = document.querySelector('#num-destinos');
    const encabezados = document.querySelector('#encabezados');
    const cuerpo = document.querySelector('#origenes');
    const demandas = document.querySelector('#demandas');
    const balanceVivo = document.querySelector('#balance-vivo');

    const valor = (nombre) => {
        const campo = form.querySelector(`[name="${nombre}"]`);
        return campo ? campo.value : '';
    };

    const leerEstado = () => {
        const m = Number(campoFilas.value);
        const n = Number(campoColumnas.value);
        return {
            m, n,
            origenes: Array.from({ length: m }, (_, i) => valor(`nombre_origen_${i}`)),
            destinos: Array.from({ length: n }, (_, j) => valor(`nombre_destino_${j}`)),
            costos: Array.from({ length: m }, (_, i) => Array.from({ length: n }, (_, j) => valor(`costo_${i}_${j}`))),
            oferta: Array.from({ length: m }, (_, i) => valor(`oferta_${i}`)),
            demanda: Array.from({ length: n }, (_, j) => valor(`demanda_${j}`)),
        };
    };

    const crear = (etiqueta, atributos = {}, hijos = []) => {
        const el = document.createElement(etiqueta);
        Object.entries(atributos).forEach(([k, v]) => {
            if (k === 'className') el.className = v;
            else if (k === 'value') el.value = v;
            else el.setAttribute(k, v);
        });
        hijos.forEach((h) => el.append(h));
        return el;
    };

    const campoNumero = (nombre, etiqueta, val) => crear('input', {
        type: 'text', inputmode: 'decimal', className: 'num-in', required: '',
        name: nombre, 'aria-label': etiqueta, value: val ?? '',
    });

    const campoNombre = (nombre, defecto, etiqueta, val) => crear('input', {
        type: 'text', className: 'nombre', maxlength: '40', name: nombre,
        placeholder: defecto, 'aria-label': etiqueta, value: val ?? '',
    });

    const dibujar = (e) => {
        campoFilas.value = e.m;
        campoColumnas.value = e.n;

        encabezados.replaceChildren(
            crear('th', { className: 'esquina' }, ['Origen \\ Destino']),
            ...Array.from({ length: e.n }, (_, j) => crear('th', {}, [
                campoNombre(`nombre_destino_${j}`, `Destino ${j + 1}`, `Nombre del destino ${j + 1}`, e.destinos[j]),
            ])),
            crear('th', { className: 'col-od' }, ['Oferta']),
        );

        cuerpo.replaceChildren(...Array.from({ length: e.m }, (_, i) => crear('tr', {}, [
            crear('th', {}, [campoNombre(`nombre_origen_${i}`, `Origen ${i + 1}`, `Nombre del origen ${i + 1}`, e.origenes[i])]),
            ...Array.from({ length: e.n }, (_, j) => crear('td', {}, [
                campoNumero(`costo_${i}_${j}`, `Costo origen ${i + 1} destino ${j + 1}`, e.costos[i]?.[j]),
            ])),
            crear('td', { className: 'od' }, [campoNumero(`oferta_${i}`, `Oferta origen ${i + 1}`, e.oferta[i])]),
        ])));

        demandas.replaceChildren(
            crear('th', {}, ['Demanda']),
            ...Array.from({ length: e.n }, (_, j) => crear('td', { className: 'od' }, [
                campoNumero(`demanda_${j}`, `Demanda destino ${j + 1}`, e.demanda[j]),
            ])),
            crear('td', { className: 'vacio' }),
        );
        actualizarBotones();
        actualizarBalance();
    };

    const botones = {
        agregarOrigen: document.querySelector('#agregar-origen'),
        quitarOrigen: document.querySelector('#quitar-origen'),
        agregarDestino: document.querySelector('#agregar-destino'),
        quitarDestino: document.querySelector('#quitar-destino'),
    };

    const actualizarBotones = () => {
        const m = Number(campoFilas.value);
        const n = Number(campoColumnas.value);
        botones.agregarOrigen.disabled = m >= limite;
        botones.quitarOrigen.disabled = m <= 1;
        botones.agregarDestino.disabled = n >= limite;
        botones.quitarDestino.disabled = n <= 1;
    };

    const cambiar = (dm, dn) => {
        const e = leerEstado();
        const m = Math.min(limite, Math.max(1, e.m + dm));
        const n = Math.min(limite, Math.max(1, e.n + dn));
        if (m === e.m && n === e.n) return;
        dibujar({ ...e, m, n });
        const foco = dm > 0 ? cuerpo.lastElementChild?.querySelector('.num-in')
            : dn > 0 ? cuerpo.querySelector(`[name="costo_0_${n - 1}"]`) : null;
        if (foco) foco.focus();
    };

    botones.agregarOrigen.addEventListener('click', () => cambiar(1, 0));
    botones.quitarOrigen.addEventListener('click', () => cambiar(-1, 0));
    botones.agregarDestino.addEventListener('click', () => cambiar(0, 1));
    botones.quitarDestino.addEventListener('click', () => cambiar(0, -1));

    // ── Ejemplo y limpiar ──────────────────────────────────────────────
    const fijar = (nombre, val) => {
        const campo = form.querySelector(`[name="${nombre}"]`);
        if (campo) campo.value = val;
    };

    document.querySelector('#cargar-ejemplo')?.addEventListener('click', () => {
        const ej = window.VOGEL_EJEMPLO;
        if (!ej) return;
        dibujar({
            m: ej.oferta.length, n: ej.demanda.length,
            origenes: ej.origenes, destinos: ej.destinos,
            costos: ej.costos.map((f) => f.map(String)),
            oferta: ej.oferta.map(String), demanda: ej.demanda.map(String),
        });
        fijar('contexto', ej.contexto);
        fijar('unidad_envio', ej.unidadEnvio);
        fijar('unidad_valor', ej.unidadValor);
        fijar('tipo_valor', 'auto');
    });

    document.querySelector('#limpiar')?.addEventListener('click', () => {
        dibujar({ m: 2, n: 2, origenes: [], destinos: [], costos: [], oferta: [], demanda: [] });
        fijar('contexto', '');
        fijar('unidad_envio', '');
        fijar('unidad_valor', '');
        fijar('tipo_valor', 'auto');
        form.querySelector('#contexto')?.focus();
    });

    // ── Balance en vivo (paso 1 adelantado mientras se escribe) ────────
    const numero = (t) => {
        const v = Number(String(t).trim().replace(',', '.'));
        return String(t).trim() !== '' && Number.isFinite(v) ? v : null;
    };
    const redondear = (v) => Math.round(v * 10000) / 10000;

    function actualizarBalance() {
        if (!balanceVivo) return;
        const e = leerEstado();
        const ofertas = e.oferta.map(numero);
        const demandasN = e.demanda.map(numero);
        if (ofertas.some((v) => v === null) || demandasN.some((v) => v === null)) {
            balanceVivo.textContent = '';
            balanceVivo.className = 'balance-vivo';
            return;
        }
        const to = redondear(ofertas.reduce((a, b) => a + b, 0));
        const td = redondear(demandasN.reduce((a, b) => a + b, 0));
        if (to === td) {
            balanceVivo.textContent = `Oferta total ${to} = demanda total ${td}: el problema está balanceado.`;
            balanceVivo.className = 'balance-vivo ok';
        } else {
            const falta = to < td;
            balanceVivo.textContent = `Oferta total ${to} y demanda total ${td}: se agregará un ${falta ? 'origen' : 'destino'} ficticio con ${redondear(Math.abs(to - td))} para balancear.`;
            balanceVivo.className = 'balance-vivo aviso';
        }
    }

    tabla.addEventListener('input', actualizarBalance);
    actualizarBotones();
    actualizarBalance();
});
