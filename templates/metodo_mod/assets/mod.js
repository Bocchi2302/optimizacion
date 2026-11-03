document.addEventListener("DOMContentLoaded", () => {
    const limiteMax = 10;
    const numOrigenes = document.getElementById("num-origenes");
    const numDestinos = document.getElementById("num-destinos");
    const cuerpoOrigenes = document.getElementById("cuerpo-origenes");
    const filaEncabezados = document.getElementById("fila-encabezados");
    const filaDemandas = document.getElementById("fila-demandas");
    const btnAgregarOrigen = document.getElementById("btn-agregar-origen");
    const btnQuitarOrigen = document.getElementById("btn-quitar-origen");
    const btnAgregarDestino = document.getElementById("btn-agregar-destino");
    const btnQuitarDestino = document.getElementById("btn-quitar-destino");
    const btnEjemploMax = document.getElementById("btn-ejemplo-max");
    const btnEjemploMin = document.getElementById("btn-ejemplo-min");
    const selectTipoOpt = document.getElementById("tipo_opt");
    const textareaContexto = document.getElementById("contexto-ejercicio");
    const celdaTotalBalance = document.getElementById("celda-total-balance");

    function actualizarTotales() {
        if (!celdaTotalBalance) return;
        let totalOferta = 0;
        let totalDemanda = 0;

        document.querySelectorAll(".input-oferta").forEach(input => {
            const val = parseFloat(input.value);
            if (!isNaN(val)) totalOferta += val;
        });

        document.querySelectorAll(".input-demanda").forEach(input => {
            const val = parseFloat(input.value);
            if (!isNaN(val)) totalDemanda += val;
        });

        if (totalOferta === 0 && totalDemanda === 0) {
            celdaTotalBalance.textContent = "Total";
            celdaTotalBalance.style.color = "#475569";
        } else if (totalOferta === totalDemanda) {
            celdaTotalBalance.innerHTML = `<span style="color:#166534;">Balanceado: ${totalOferta}</span>`;
        } else {
            celdaTotalBalance.innerHTML = `<span style="color:#b45309;" title="Se balanceará automáticamente con ficticio">Of: ${totalOferta} | Dem: ${totalDemanda}</span>`;
        }
    }

    document.getElementById("tabla-transporte")?.addEventListener("input", actualizarTotales);
    actualizarTotales();

    // ── Agregar Origen ──
    btnAgregarOrigen?.addEventListener("click", () => {
        let filas = parseInt(numOrigenes.value, 10);
        const columnas = parseInt(numDestinos.value, 10);
        if (filas >= limiteMax) return;

        const nuevaFila = document.createElement("tr");
        nuevaFila.setAttribute("data-fila", filas);

        let html = `
            <th class="celda-nombre-origen">
                <input type="text" name="nombre_origen_${filas}" value="Origen ${filas + 1}" class="input-nombre-fila" title="Editar nombre de origen">
            </th>
        `;

        for (let j = 0; j < columnas; j++) {
            html += `
                <td>
                    <input type="number" step="any" min="0" required name="costo_${filas}_${j}" placeholder="Costo" class="input-costo">
                </td>
            `;
        }

        html += `
            <td class="celda-oferta">
                <input type="number" step="any" min="0" required name="oferta_${filas}" placeholder="Oferta" class="input-oferta">
            </td>
        `;

        nuevaFila.innerHTML = html;
        cuerpoOrigenes.appendChild(nuevaFila);
        numOrigenes.value = filas + 1;
        actualizarTotales();
    });

    // ── Quitar Origen ──
    btnQuitarOrigen?.addEventListener("click", () => {
        let filas = parseInt(numOrigenes.value, 10);
        if (filas <= 1) return;

        cuerpoOrigenes.removeChild(cuerpoOrigenes.lastElementChild);
        numOrigenes.value = filas - 1;
        actualizarTotales();
    });

    // ── Agregar Destino ──
    btnAgregarDestino?.addEventListener("click", () => {
        const filas = parseInt(numOrigenes.value, 10);
        let columnas = parseInt(numDestinos.value, 10);
        if (columnas >= limiteMax) return;

        // 1. Agregar encabezado
        const nuevoTh = document.createElement("th");
        nuevoTh.className = "col-destino";
        nuevoTh.setAttribute("data-col", columnas);
        nuevoTh.innerHTML = `<input type="text" name="nombre_destino_${columnas}" value="Destino ${columnas + 1}" class="input-nombre-col" title="Editar nombre de destino">`;
        filaEncabezados.insertBefore(nuevoTh, filaEncabezados.lastElementChild);

        // 2. Agregar celdas en cada fila del cuerpo
        Array.from(cuerpoOrigenes.rows).forEach((fila, i) => {
            const nuevaCelda = document.createElement("td");
            nuevaCelda.innerHTML = `<input type="number" step="any" min="0" required name="costo_${i}_${columnas}" placeholder="Costo" class="input-costo">`;
            fila.insertBefore(nuevaCelda, fila.lastElementChild);
        });

        // 3. Agregar celda en pie de tabla (Demanda)
        const nuevaDemanda = document.createElement("td");
        nuevaDemanda.setAttribute("data-col", columnas);
        nuevaDemanda.innerHTML = `<input type="number" step="any" min="0" required name="demanda_${columnas}" placeholder="Demanda" class="input-demanda">`;
        filaDemandas.insertBefore(nuevaDemanda, filaDemandas.lastElementChild);

        numDestinos.value = columnas + 1;
        actualizarTotales();
    });

    // ── Quitar Destino ──
    btnQuitarDestino?.addEventListener("click", () => {
        let columnas = parseInt(numDestinos.value, 10);
        if (columnas <= 1) return;

        // Quitar encabezado
        const encabezadosDestino = filaEncabezados.querySelectorAll(".col-destino");
        if (encabezadosDestino.length > 0) {
            encabezadosDestino[encabezadosDestino.length - 1].remove();
        }

        // Quitar celdas en cada fila
        Array.from(cuerpoOrigenes.rows).forEach(fila => {
            const celdas = fila.querySelectorAll("td:not(.celda-oferta)");
            if (celdas.length > 0) {
                celdas[celdas.length - 1].remove();
            }
        });

        // Quitar celda de demanda
        const celdasDemanda = filaDemandas.querySelectorAll("td[data-col]");
        if (celdasDemanda.length > 0) {
            celdasDemanda[celdasDemanda.length - 1].remove();
        }

        numDestinos.value = columnas - 1;
        actualizarTotales();
    });

    // ── Función para reconstruir tabla con dimensiones específicas ──
    function configurarDimensiones(m, n) {
        while (parseInt(numOrigenes.value, 10) > m) {
            btnQuitarOrigen.click();
        }
        while (parseInt(numOrigenes.value, 10) < m) {
            btnAgregarOrigen.click();
        }
        while (parseInt(numDestinos.value, 10) > n) {
            btnQuitarDestino.click();
        }
        while (parseInt(numDestinos.value, 10) < n) {
            btnAgregarDestino.click();
        }
    }

    // ── Cargar Ejemplo Maximización ──
    btnEjemploMax?.addEventListener("click", () => {
        configurarDimensiones(3, 3);
        selectTipoOpt.value = "max";
        textareaContexto.value = "Una empresa comercializadora de suministros tecnológicos despacha productos desde 3 plantas regionales hacia 3 centros mayoristas. La dirección busca maximizar el margen de utilidad neta total considerando las ganancias unitarias por ruta y asegurando que los costes de mejora certifiquen la optimalidad.";

        const origenes = ["Planta Norte", "Planta Centro", "Planta Sur"];
        const destinos = ["Mayorista A", "Mayorista B", "Mayorista C"];
        const costos = [
            [10, 12, 15],
            [14, 10, 16],
            [12, 15, 11]
        ];
        const oferta = [30, 40, 30];
        const demanda = [25, 35, 40];

        origenes.forEach((nombre, i) => {
            const input = document.querySelector(`input[name="nombre_origen_${i}"]`);
            if (input) input.value = nombre;
            const inputOf = document.querySelector(`input[name="oferta_${i}"]`);
            if (inputOf) inputOf.value = oferta[i];
        });

        destinos.forEach((nombre, j) => {
            const input = document.querySelector(`input[name="nombre_destino_${j}"]`);
            if (input) input.value = nombre;
            const inputDem = document.querySelector(`input[name="demanda_${j}"]`);
            if (inputDem) inputDem.value = demanda[j];
        });

        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                const inputC = document.querySelector(`input[name="costo_${i}_${j}"]`);
                if (inputC) inputC.value = costos[i][j];
            }
        }

        actualizarTotales();
    });

    // ── Cargar Ejemplo Minimización ──
    btnEjemploMin?.addEventListener("click", () => {
        configurarDimensiones(3, 4);
        selectTipoOpt.value = "min";
        textareaContexto.value = "Una cadena de distribución de alimentos requiere abastecer 4 supermercados urbanos desde 3 almacenes logísticos al menor costo de transporte posible, evaluando las rutas no básicas mediante sus respectivos costes de mejora.";

        const origenes = ["Almacén 1", "Almacén 2", "Almacén 3"];
        const destinos = ["Supermercado A", "Supermercado B", "Supermercado C", "Supermercado D"];
        const costos = [
            [2, 3, 5, 1],
            [7, 3, 4, 6],
            [4, 1, 7, 2]
        ];
        const oferta = [30, 40, 20];
        const demanda = [20, 25, 25, 20];

        origenes.forEach((nombre, i) => {
            const input = document.querySelector(`input[name="nombre_origen_${i}"]`);
            if (input) input.value = nombre;
            const inputOf = document.querySelector(`input[name="oferta_${i}"]`);
            if (inputOf) inputOf.value = oferta[i];
        });

        destinos.forEach((nombre, j) => {
            const input = document.querySelector(`input[name="nombre_destino_${j}"]`);
            if (input) input.value = nombre;
            const inputDem = document.querySelector(`input[name="demanda_${j}"]`);
            if (inputDem) inputDem.value = demanda[j];
        });

        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 4; j++) {
                const inputC = document.querySelector(`input[name="costo_${i}_${j}"]`);
                if (inputC) inputC.value = costos[i][j];
            }
        }

        actualizarTotales();
    });
});
