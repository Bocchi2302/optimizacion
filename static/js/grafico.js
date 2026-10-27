document.addEventListener('DOMContentLoaded', () => {
    const botonAgregar = document.querySelector('#btn-agregar-restriccion');
    const contenedor = document.querySelector('#restricciones-container');

    if (!botonAgregar || !contenedor) {
        return;
    }

    botonAgregar.addEventListener('click', () => {
        const fila = document.createElement('div');
        fila.className = 'restriccion-row';
        fila.innerHTML = `
            <input type="number" name="r_x[]" step="any" required placeholder="X1"> X1 +
            <input type="number" name="r_y[]" step="any" required placeholder="X2"> X2
            <select name="r_op[]">
                <option value="&lt;=">≤</option>
                <option value="&gt;=">≥</option>
            </select>
            <input type="number" name="r_c[]" step="any" required placeholder="C">
        `;
        contenedor.appendChild(fila);
    });
});
