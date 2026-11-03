"""Prueba opcional de extremo a extremo en un navegador real (Playwright).

No forma parte de las pruebas unitarias ni es necesaria para usar el módulo.
Uso:  python tests/e2e_dos_fases_navegador.py [ancho]        (el servidor demo se inicia solo)
Variables: PW_CHROMIUM=ruta/al/chromium  (opcional, si Playwright no encuentra su navegador)
"""
import json
import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server  # noqa: E402
try:
    from demo_dos_fases import create_app  # carpeta independiente
except ImportError:  # proyecto real: se usa su app.py con el Blueprint ya registrado
    from app import app as _app

    def create_app():
        return _app
from playwright.sync_api import sync_playwright  # noqa: E402

WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
srv = make_server("127.0.0.1", 5077, create_app())
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:5077/metodo_dos_fases/"
checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("OK   " if cond else "FALLA"), name)


with sync_playwright() as p:
    kw = {"executable_path": os.environ["PW_CHROMIUM"]} if os.environ.get("PW_CHROMIUM") else {}
    browser = p.chromium.launch(args=["--no-sandbox"], **kw)
    ctx = browser.new_context(viewport={"width": WIDTH, "height": 900}, accept_downloads=True)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL); pg.wait_for_load_state("networkidle")
    pg.keyboard.press("Tab")
    check("el primer Tab llega al enlace «Ir al planteamiento»", pg.evaluate("document.activeElement.className") == "df-skip")
    check("vista previa inicial: Max Z = 5x1 + 8x2", pg.inner_text("#df-preview").replace("\n", "").startswith("Max Z = 5x1 + 8x2"))
    pg.fill("#df-c-0", "7")
    check("la vista previa se actualiza al escribir", "7x1" in pg.inner_text("#df-preview").replace("\n", ""))
    pg.fill("#df-c-0", "5")
    OPT = ".df-report.df-st-optimal"
    pg.click("#df-solve"); pg.wait_for_selector(OPT)
    check("Resolver: Z máximo = 74", pg.inner_text(".df-cifra strong").strip() == "74")
    check("ejemplo sin cambios: el encabezado nombra el ejemplo", "EJEMPLO DE LA PROFESORA" in pg.inner_text("#df-results-eyebrow"))
    check("pestañas visibles y Resumen activo", pg.is_visible("#df-tabs") and pg.get_attribute("#df-tab-resumen", "aria-selected") == "true")
    check("ruta: las cinco estaciones completadas", pg.evaluate("[...document.querySelectorAll('#df-route li')].every(l => l.dataset.state === 'done')"))
    check("conclusión destacada al final del resumen, con nombres y valores", pg.locator("#df-panel-resumen > .df-conclusion:last-child").count() == 1 and "Producto A = 2 unidades" in pg.inner_text("#df-conclusion") and pg.locator(".df-map").count() == 0)
    pg.click("#df-tab-desarrollo")
    check("Desarrollo completo: siete tablas numeradas", pg.locator("#df-panel-desarrollo article.df-step:visible").count() == 7)
    check("pivote encerrado (3 celdas pivote)", pg.locator("td.df-pivot").count() == 3)
    check("cada tabla trae su bitácora", pg.locator("#df-panel-desarrollo .df-bitacora").count() == 7)
    check("operaciones plegadas al inicio", pg.locator("details.df-operations[open]").count() == 0)
    pg.click("#df-expand")
    check("«Abrir todas las operaciones» abre todas", pg.locator("details.df-operations:not([open])").count() == 0)
    pg.click("#df-tab-guiado"); pg.wait_for_selector("#df-guided:not([hidden])")
    total = int(pg.inner_text("#df-g-count").split()[-1])
    check("recorrido guiado: plantear + estandarizar + 7 tablas + comprobar + conclusión = 11 pasos", total == 11)
    check("el foco entra en el diálogo", pg.evaluate("document.activeElement.id") == "df-g-body")
    pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowRight")
    check("flecha derecha avanza (paso 3: tabla 1)", pg.inner_text("#df-g-count") == f"3 de {total}" and "Fase 1" in pg.inner_text("#df-g-phase"))
    check("la diapositiva de tabla muestra la tabla y la bitácora (sin gráficas)", pg.locator("#df-g-body .df-tableau").count() == 1 and pg.locator("#df-g-body .df-bitacora").count() == 1 and pg.locator("#df-g-body svg.df-map").count() == 0)
    check("la estación actual de la ruta se marca", pg.get_attribute("#df-route li[data-step=fase1]", "data-state") == "current")
    pg.keyboard.press("End")
    check("Fin lleva a la conclusión", pg.inner_text("#df-g-count") == f"{total} de {total}" and "conclusión" in pg.inner_text(".df-g-eyebrow").lower() and "74" in pg.inner_text(".df-g-title"))
    pg.keyboard.press("Escape")
    check("Esc cierra el recorrido y devuelve el foco", pg.is_hidden("#df-guided") and pg.evaluate("document.activeElement.id") == "df-tab-guiado")
    with pg.expect_download() as d:
        pg.click("#df-report-download")
    path = d.value.path(); html = Path(path).read_text(encoding="utf-8")
    check("informe descargado: autónomo y con Tabla 7", "Tabla 7" in html and "<script" not in html and "http" not in html.replace("http://www.w3.org", ""))
    with pg.expect_download() as d:
        pg.click("#df-download-model")
    model = json.loads(Path(d.value.path()).read_text(encoding="utf-8"))
    check("JSON descargado conserva nombres y unidades", model["variables"][1]["name"] == "Producto B" and model["constraints"][1]["unit"] == "unidades")
    pg.fill("#df-c-0", "6")
    check("editar sin recalcular marca el resultado como anterior", pg.is_visible("#df-stale") and "df-stale-result" in pg.get_attribute("#df-result", "class"))
    pg.click("#df-solve"); pg.wait_for_selector(OPT)
    pg.wait_for_function("document.querySelector('.df-cifra strong') && document.querySelector('.df-cifra strong').textContent.trim() !== '74'")
    check("al recalcular desaparece el aviso", not pg.is_visible("#df-stale"))
    check("modelo propio: el encabezado dice «TU MODELO»", "TU MODELO" in pg.inner_text("#df-results-eyebrow"))
    pg.select_option("#df-count", "3")
    check("3 variables: se conservan los datos y aparece x3", pg.input_value("#df-c-0") == "6" and pg.locator("#df-c-2").count() == 1)
    pg.click("#df-add-constraint")
    check("agregar restricción (4)", pg.locator(".df-constraint").count() == 4)
    pg.click("[aria-label='Eliminar restricción R4']")
    check("eliminar restricción (3)", pg.locator(".df-constraint").count() == 3)
    pg.fill("#df-b-0", "1/0"); pg.click("#df-solve"); pg.wait_for_timeout(300)
    check("1/0: campo marcado, aria-invalid y alerta visible", pg.get_attribute("#df-b-0", "aria-invalid") == "true" and pg.is_visible("#df-error"))
    check("tras el error el resultado previo queda atenuado", "df-stale-result" in pg.get_attribute("#df-result", "class"))
    pg.fill("#df-b-0", "12")
    check("corregir el campo limpia su error", pg.get_attribute("#df-b-0", "aria-invalid") is None)
    for ex, st, ruta in (("infactible", "infeasible", "fail"), ("no_acotado", "unbounded", "warn"), ("minimo", "optimal", "done")):
        pg.select_option("#df-example", ex); pg.click("#df-load-example"); pg.click("#df-solve"); pg.wait_for_selector(f".df-report.df-st-{st}")
        estacion = "fase1" if st == "infeasible" else "fase2"
        check(f"ejemplo {ex}: estado correcto y ruta «{ruta}»", pg.get_attribute(f"#df-route li[data-step={estacion}]", "data-state") == ruta)
    pg.select_option("#df-example", "profesora"); pg.click("#df-load-example")
    model["objective"][0] = "9"
    pg.set_input_files("#df-import", {"name": "m.json", "mimeType": "application/json", "buffer": json.dumps(model).encode()})
    pg.wait_for_timeout(400)
    check("importar JSON carga el modelo (x1 = 9)", pg.input_value("#df-c-0") == "9")
    pg.set_input_files("#df-import", {"name": "x.json", "mimeType": "application/json", "buffer": b'{"a":1}'})
    pg.wait_for_timeout(400)
    check("JSON inválido muestra error", pg.is_visible("#df-error"))
    over = pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    check(f"sin desplazamiento horizontal de página a {WIDTH}px", not over)
    check("sin errores de consola ni excepciones", not errors)
    if errors: print(errors)
    browser.close()
srv.shutdown()
failed = [n for n, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} comprobaciones correctas")
sys.exit(1 if failed else 0)
