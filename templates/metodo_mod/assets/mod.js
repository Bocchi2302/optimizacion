'use strict';

const form = document.getElementById('mod-form');
const byId = id => document.getElementById(id);
let pending = null;

function clearResult() {
    byId('result').hidden = true;
    byId('empty-result').hidden = false;
    byId('error').hidden = true;
    byId('status').textContent = '';
}

function cancelPending() {
    if (pending) pending.abort();
    pending = null;
    byId('calculate').disabled = false;
    form.removeAttribute('aria-busy');
}

function signed(value) {
    return value.startsWith('-') ? `(${value})` : value;
}

form.addEventListener('submit', async event => {
    event.preventDefault();
    cancelPending();
    clearResult();
    const controller = new AbortController();
    pending = controller;
    byId('calculate').disabled = true;
    form.setAttribute('aria-busy', 'true');
    byId('status').textContent = 'Calculando…';
    try {
        const response = await fetch(form.dataset.endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({dividendo: byId('dividendo').value.trim(), divisor: byId('divisor').value.trim()}),
            signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (!response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('El servidor no pudo procesar el cálculo. Inténtalo de nuevo.');
        }
        const data = await response.json();
        if (controller.signal.aborted) return;
        if (!response.ok) throw new Error(data.error || 'No se pudo realizar el cálculo.');
        const a = data.dividendo, b = data.divisor, q = data.cociente, r = data.residuo;
        const product = (BigInt(b) * BigInt(q)).toString();
        byId('expression').textContent = `${a} MOD ${signed(b)} =`;
        byId('remainder').textContent = r;
        byId('equation').textContent = `${a} = ${signed(b)} × ${signed(q)} + ${r}`;
        byId('step-quotient').textContent = `Cociente entero: q = ${q}, elegido para que 0 ≤ r < |${b}|.`;
        byId('step-product').textContent = `Multiplica divisor por cociente: ${signed(b)} × ${signed(q)} = ${product}.`;
        byId('step-remainder').textContent = `Resta al dividendo: ${a} − ${signed(product)} = ${r}.`;
        byId('divisibility').textContent = data.divisible ? 'División exacta: el dividendo es divisible por el divisor.' : 'División con residuo: el dividendo no es divisible por el divisor.';
        byId('parity').textContent = `${a} es ${data.par ? 'par' : 'impar'}: ${a} MOD 2 = ${data.par ? '0' : '1'}.`;
        byId('result').hidden = false;
        byId('empty-result').hidden = true;
        byId('status').textContent = `Cálculo terminado. Residuo: ${r}.`;
    } catch (error) {
        if (controller.signal.aborted) return;
        byId('error').textContent = error instanceof TypeError ? 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.' : error.message;
        byId('error').hidden = false;
        byId('status').textContent = '';
    } finally {
        if (pending === controller) cancelPending();
    }
});

form.addEventListener('input', () => { cancelPending(); clearResult(); });
form.addEventListener('reset', event => {
    event.preventDefault();
    cancelPending();
    form.querySelectorAll('input').forEach(input => { input.value = ''; });
    clearResult();
    byId('dividendo').focus();
});
document.querySelectorAll('[data-a][data-b]').forEach(button => {
    button.addEventListener('click', () => {
        byId('dividendo').value = button.dataset.a;
        byId('divisor').value = button.dataset.b;
        form.requestSubmit();
    });
});
