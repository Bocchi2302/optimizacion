import copy
import json
import unittest
from fractions import Fraction as F

from pathlib import Path

try:
    from demo_dos_fases import create_app  # carpeta independiente
except ImportError:  # proyecto real: se usa su app.py con el Blueprint ya registrado
    from app import app as _app

    def create_app():
        return _app
from blueprints.dos_fases_solver import EXAMPLES, ModelError, number, solve

PROYECTO = Path(__file__).resolve().parents[1]


def model(c, constraints, sense="max"):
    return {"sense": sense, "objective": c, "constraints": [
        {"coefficients": a, "operator": op, "rhs": b} for a,op,b in constraints]}


class SolverTests(unittest.TestCase):
    def test_example_and_seven_tables(self):
        r=solve(EXAMPLES['profesora'])
        self.assertEqual((r['solution'],r['objective_value']),(['2','8'],'74'))
        self.assertEqual(len(r['events']),7)
        self.assertEqual(r['events'][1]['tableau'][0],['3','2','-1','0','0','0','20'])
        self.assertEqual(r['events'][3]['basis'],['x1','x2','S3'])
        self.assertEqual(r['events'][4]['tableau'][0],['-5','-8','0','0','0'])
        self.assertEqual(r['events'][5]['tableau'][0],['0','0','-11','0','52'])
        self.assertEqual(r['events'][6]['tableau'][0],['0','0','0','11/2','74'])
        self.assertEqual(r['values']['S2'],'2')

    def test_minimization(self):
        r=solve(EXAMPLES['minimo'])
        self.assertEqual((r['solution'],r['objective_value']),(['3','1'],'9'))
        self.assertTrue(all(F(v)<=0 for v in r['events'][-1]['tableau'][0][:-1]))

    def test_infeasible_stops_before_phase2(self):
        r=solve(EXAMPLES['infactible'])
        self.assertEqual((r['status'],r['phase1_value']),('infeasible','2'))
        self.assertFalse(any(e['phase']==2 for e in r['events']))

    def test_unbounded_with_ray(self):
        r=solve(EXAMPLES['no_acotado'])
        self.assertEqual(r['status'],'unbounded')
        self.assertGreater(F(r['ray_gain']),0)
        for ch in r['verification']:self.assertTrue(ch['satisfied'])
        x=[F(a)+100*F(b) for a,b in zip(r['solution'],r['ray'])]
        self.assertGreaterEqual(x[0]-x[1],1)

    def test_minimum_unbounded(self):
        r=solve(model([-1],[([1],'>=',1)],'min'))
        self.assertEqual(r['status'],'unbounded')
        self.assertLess(F(r['ray_gain']),0)

    def test_negative_rhs_normalization(self):
        r=solve(model([1],[([-1],'>=',-2)]))
        self.assertEqual((r['objective_value'],r['solution']),('2',['2']))
        self.assertTrue(r['standardization'][0]['flipped'])

    def test_negative_rhs_equality(self):
        r=solve(model([2],[([-1],'=',-3)]))
        self.assertEqual(r['objective_value'],'6')

    def test_zero_ratio_is_eligible(self):
        r=solve(model([1,1],[([1,0],'<=',0),([0,1],'<=',1)]))
        self.assertEqual(r['solution'],['0','1'])
        self.assertTrue(any(e['pivot'] and e['pivot']['degenerate'] for e in r['events']))

    def test_redundant_equality(self):
        r=solve(model([1],[([1],'=',2),([2],'=',4)]))
        self.assertEqual((r['status'],r['objective_value']),('optimal','2'))
        self.assertTrue(any('redundante' in x for x in r['notes']))
        self.assertFalse(any(v.startswith('A') for v in r['final_basis']))

    def test_cleanup_negative_pivot(self):
        r=solve(model([1],[([-1],'=',0)]))
        self.assertEqual((r['status'],r['objective_value']),('optimal','0'))
        self.assertTrue(any(e['pivot'] and e['pivot']['element']=='-1' for e in r['events']))

    def test_zero_equals_zero(self):
        r=solve(model([0],[([0],'=',0)]))
        self.assertEqual(r['status'],'optimal')
        self.assertEqual(r['final_basis'],[])

    def test_zero_equals_one(self):
        self.assertEqual(solve(model([0],[([0],'=',1)]))['status'],'infeasible')

    def test_no_artificials(self):
        r=solve(model([3,2],[([1,1],'<=',4),([1,0],'<=',2)]))
        self.assertEqual(r['objective_value'],'10')
        self.assertEqual(r['phase1_value'],'0')
        self.assertTrue(r['notes'])

    def test_fractional_result_exact(self):
        r=solve(model(['1/3'],[([3],'<=',1)]))
        self.assertEqual((r['solution'],r['objective_value']),(['1/3'],'1/9'))

    def test_decimal_comma(self):
        self.assertEqual(number('0,25'),F(1,4))

    def test_alternate_optimum(self):
        r=solve(model([1,1],[([1,1],'<=',4)]))
        self.assertTrue(r['alternate_directions'])

    def test_no_phase2_pivots_needed(self):
        r=solve(model([2],[([1],'=',3)]))
        self.assertFalse(any(e['kind']=='pivot' and e['phase']==2 for e in r['events']))

    def test_bland_resolves_classic_cycle(self):
        r=solve(model([10,-57,-9,-24],[(['0.5','-5.5','-2.5',9],'<=',0),
            (['0.5','-1.5','-0.5',1],'<=',0),([1,0,0,0],'<=',1)]))
        self.assertEqual((r['status'],r['objective_value']),('optimal','1'))
        self.assertTrue(any('Bland' in note for note in r['notes']))

    def test_iteration_limit_is_not_optimal(self):
        r=solve(EXAMPLES['profesora'],max_iterations=0)
        self.assertEqual(r['status'],'iteration_limit')

    def test_input_unchanged_and_results_repeatable(self):
        p=copy.deepcopy(EXAMPLES['profesora']);before=copy.deepcopy(p)
        self.assertEqual(solve(p),solve(p));self.assertEqual(p,before)

    def test_validation(self):
        for value in [None,True,'NaN','Infinity','1/0','__import__("os")','1e99']:
            with self.subTest(value=value),self.assertRaises(ModelError): number(value)
        for p in [{},[],{'objective':[1],'constraints':[]},model([1],[([1,2],'<=',3)]),
                  model([1],[([1],'<>',3)]),dict(EXAMPLES['profesora'],sense='other')]:
            with self.subTest(payload=p),self.assertRaises(ModelError): solve(p)

    def test_basis_identity_and_feasibility_after_each_pivot(self):
        for p in EXAMPLES.values():
            r=solve(p)
            for e in r['events']:
                if e['kind']!='pivot':continue
                t=e['tableau']
                for i,v in enumerate(e['basis'],1):
                    j=e['columns'].index(v)
                    self.assertEqual([F(row[j]) for row in t],[F(k==i) for k in range(len(t))])
                    self.assertGreaterEqual(F(t[i][-1]),0)

    def test_every_logged_component_is_exact(self):
        r=solve(EXAMPLES['profesora'])
        for e in r['events']:
            for op in e['operations']:
                self.assertEqual(len(op['components']),len(e['columns'])+1)
        # En el primer pivote, la nueva fila se usa al reducir r: -3*(1/2)+2=1/2.
        op=r['events'][2]['operations'][-1]
        self.assertEqual(op['components'][1]['calculation'],'(-3)·(1/2) + (2) = 1/2')


class WebTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app(); self.app.testing=True; self.client=self.app.test_client()

    def test_page_and_assets(self):
        self.assertEqual(self.client.get('/').status_code,200)
        for path in ['/metodo_dos_fases/','/static/css/dos_fases.css','/static/js/dos_fases.js',
                     '/static/fonts/dos_fases/atkinson-hyperlegible-latin-400-normal.woff2','/static/fonts/dos_fases/fraunces-latin-600-normal.woff2',
                     '/static/fonts/dos_fases/jetbrains-mono-latin-500-normal.woff2','/static/fonts/dos_fases/caveat-latin-700-normal.woff2']:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code,200,path)

    def test_architecture_files_follow_project_convention(self):
        for rel in ['blueprints/dos_fases_bp.py','blueprints/dos_fases_solver.py','templates/metodo_dos_fases/index.html',
                    'static/css/dos_fases.css','static/js/dos_fases.js']:
            self.assertTrue((PROYECTO/rel).is_file(),rel)
        from blueprints.dos_fases_bp import dos_fases_bp
        self.assertEqual(dos_fases_bp.name,'dos_fases_bp')
        endpoints={r.endpoint for r in self.app.url_map.iter_rules()}
        self.assertTrue({'dos_fases_bp.vista_principal','dos_fases_bp.calcular','dos_fases_bp.descargar_informe'}<=endpoints)

    def test_page_uses_url_for_for_static_and_menu(self):
        html=self.client.get('/metodo_dos_fases/').data.decode()
        for expected in ['href="/static/css/dos_fases.css"','src="/static/js/dos_fases.js"','data-api-url="/metodo_dos_fases/api/resolver"','data-report-url="/metodo_dos_fases/informe"','href="/"']:
            self.assertIn(expected,html)
        self.assertNotIn('<style',html)

    def test_css_is_scoped_to_this_module(self):
        import re
        css=(PROYECTO/'static/css/dos_fases.css').read_text(encoding='utf-8')
        css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
        loose=[]
        for block in re.findall(r'(?:^|\})\s*([^{}@]+)\{',css):
            for sel in block.split(','):
                sel=sel.strip()
                if sel and 'df-' not in sel and sel not in (':root',) and not re.match(r'^(from|to|\d)',sel):
                    loose.append(sel)
        self.assertEqual(loose,[],'selectores sin prefijo df- que podrían afectar a otros módulos')

    def test_api(self):
        r=self.client.post('/metodo_dos_fases/api/resolver',json=EXAMPLES['profesora'])
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['objective_value'],'74');self.assertIn('Tabla 7',r.json['html'])

    def test_bad_request(self):
        for payload in [None,[],{}, {'objective':[1],'constraints':[]}]:
            self.assertEqual(self.client.post('/metodo_dos_fases/api/resolver',json=payload).status_code,400)

    def test_context_escaped_in_report(self):
        p=copy.deepcopy(EXAMPLES['profesora']);p['context']='<script>alert(1)</script>'
        p['variables'][0]['name']='<img src=x onerror=alert(1)>'
        r=self.client.post('/metodo_dos_fases/informe',json=p)
        self.assertNotIn(b'<script>',r.data);self.assertIn(b'&lt;script&gt;',r.data)
        self.assertNotIn(b'<img src=x',r.data)

    def test_report_is_self_contained(self):
        r=self.client.post('/metodo_dos_fases/informe',json=EXAMPLES['profesora'])
        self.assertEqual(r.status_code,200)
        self.assertIn('attachment',r.headers['Content-Disposition'])
        self.assertNotIn(b'<link',r.data);self.assertNotIn(b'<script',r.data)
        self.assertIn(b'<style>',r.data)

    def test_custom_prefix_and_home(self):
        from flask import Flask
        from blueprints.dos_fases_bp import dos_fases_bp
        app=Flask('host',root_path=str(PROYECTO));app.add_url_rule('/',endpoint='index',view_func=lambda:'menu')
        app.register_blueprint(dos_fases_bp,url_prefix='/otro')
        c=app.test_client();r=c.get('/otro/')
        self.assertEqual(r.status_code,200);self.assertIn('Menú del proyecto'.encode(),r.data)
        self.assertIn(b'/otro/api/resolver',r.data)


class NewFeatureTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(); self.app.testing = True; self.client = self.app.test_client()

    def test_error_identifies_field(self):
        p = copy.deepcopy(EXAMPLES['profesora']); p['constraints'][0]['rhs'] = '1/0'
        r = self.client.post('/metodo_dos_fases/api/resolver', json=p)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json['field'], 'b-0')
        self.assertIn('R1 · K', r.json['error'])
        p = copy.deepcopy(EXAMPLES['profesora']); p['objective'][1] = 'abc'
        self.assertEqual(self.client.post('/metodo_dos_fases/api/resolver', json=p).json['field'], 'c-1')

    def test_interpretation_uses_names_and_units(self):
        r = solve(EXAMPLES['profesora'])
        text = '\n'.join(r['interpretation'])
        self.assertIn('Producto B (x2): 8 unidades', text)
        self.assertIn('Contribución total (valor máximo): 74 unidades monetarias', text)
        self.assertIn('Producción mínima: se supera el mínimo en 2 unidades (excedente)', text)
        self.assertEqual([(s['name'], s['kind'], s['value']) for s in r['slacks']], [('S2', 'excedente', '2'), ('S3', 'holgura', '0')])

    def test_infeasible_and_unbounded_interpretation(self):
        inf = solve(EXAMPLES['infactible'])
        self.assertIn('Pedido mínimo', inf['interpretation'][0])
        unb = solve(EXAMPLES['no_acotado'])
        self.assertIn('Producto A (x1)', unb['interpretation'][0])
        self.assertEqual(unb['unbounded_column_index'], 1)

    def test_standardization_explains_each_conversion(self):
        r = solve(model([1], [([-1], '>=', -2)]))
        self.assertIn('K negativo', r['standardization'][0]['explanation'])
        r = solve(EXAMPLES['profesora'])
        self.assertIn('artificial A1', r['standardization'][0]['explanation'])
        self.assertIn('excedente S2', r['standardization'][1]['explanation'])
        self.assertIn('holgura S3', r['standardization'][2]['explanation'])

    def test_pivot_metadata_links_previous_table(self):
        r = solve(EXAMPLES['profesora'])
        pivots = [e['pivot'] for e in r['events'] if e['kind'] == 'pivot']
        self.assertEqual([(p['previous_table'], p['table']) for p in pivots], [(2, 3), (3, 4), (6, 7)])
        self.assertEqual({o['kind'] for o in r['events'][2]['operations']}, {'normalize', 'reduce'})

    def test_report_highlights_pivot_on_previous_table_with_decision(self):
        html = self.client.post('/metodo_dos_fases/api/resolver', json=EXAMPLES['profesora']).json['html']
        self.assertEqual(html.count('class="df-decision"'), 3)
        import re
        self.assertEqual(len(re.findall(r'<td class="[^"]*\bdf-pivot(?=[\s"])', html)), 3)  # una celda pivote por decisión, en la tabla previa
        self.assertIn('Tabla 2 · pivote encerrado en azul', html)
        self.assertIn('Tabla 7</caption>', html)
        self.assertIn('−11', html)  # signo menos tipográfico
        self.assertIn('Normalización de la fila pivote', html)
        self.assertIn('Entra el coeficiente más negativo de Z', html)

    def test_unbounded_report_highlights_entering_column(self):
        html = self.client.post('/metodo_dos_fases/api/resolver', json=EXAMPLES['no_acotado']).json['html']
        self.assertIn('columna que entra en azul', html)
        self.assertIn('CERTIFICADO DE NO ACOTACIÓN', html)

    def test_standalone_report_embeds_fonts_and_has_no_external_urls(self):
        data = self.client.post('/metodo_dos_fases/informe', json=EXAMPLES['profesora']).data
        self.assertIn(b'font/woff2;base64', data)
        data = data.replace(b'http://www.w3.org/2000/svg', b'')  # espacio de nombres XML de un icono incrustado; no es una petición
        for marker in (b'http://', b'https://', b'<link', b'<script', b'@import', b'url(../'):
            self.assertNotIn(marker, data)

    def test_index_has_no_external_resources_and_no_cdn(self):
        html = self.client.get('/metodo_dos_fases/').data.decode()
        self.assertNotIn('https://', html); self.assertNotIn('http://', html)
        css = self.client.get('/static/css/dos_fases.css').data.decode()
        self.assertNotIn('http', css.replace('http://www.w3.org', ''))
        self.assertEqual(self.client.get('/static/fonts/dos_fases/atkinson-hyperlegible-latin-400-normal.woff2').status_code, 200)

    def test_standalone_report_has_every_operation_open(self):
        data = self.client.post('/metodo_dos_fases/informe', json=EXAMPLES['profesora']).data.decode()
        self.assertEqual(data.count('<details class="df-operations" open>'), 5)  # tablas 2, 3, 4, 6 y 7
        fragment = self.client.post('/metodo_dos_fases/api/resolver', json=EXAMPLES['profesora']).json['html']
        self.assertNotIn('df-operations" open', fragment)

    def test_constraint_unit_is_optional(self):
        p = copy.deepcopy(EXAMPLES['profesora'])
        for c in p['constraints']: c.pop('unit')
        self.assertEqual(solve(p)['status'], 'optimal')


if __name__=='__main__': unittest.main()


class ExplicacionTests(unittest.TestCase):
    """Bitácora, recorrido y conclusión: explican los resultados sin cambiarlos."""

    def test_bitacora_del_ejemplo_de_clase(self):
        r = solve(EXAMPLES['profesora'])
        textos = {e['number']: ' '.join(n['text'] for n in e['narrative']) for e in r['events']}
        self.assertIn('r − A1 − A2 = 0', textos[1])
        self.assertIn('R1: 12 ÷ 2 = 6; R2: 8 ÷ 1 = 8. R3 no participa', textos[2])
        self.assertIn('sale A1 (R1) y el pivote es 2', textos[2])
        self.assertIn('El punto (6, 0) todavía no es factible: las artificiales suman 2', textos[3])
        self.assertIn('Termina la Fase 1', textos[4])
        self.assertIn('Z − 5·x1 − 8·x2 = 0', textos[5])
        self.assertIn('Z = 52', textos[6])
        self.assertIn('S2 (-11)', textos[6])
        self.assertIn('Z máximo = 74', textos[7])
        for e in r['events']:
            self.assertEqual(e['narrative'][0]['title'], '¿Qué se hizo?')
            self.assertTrue(any(n['kind'] == 'lectura' for n in e['narrative']))

    def test_recorrido_y_resumen(self):
        r = solve(EXAMPLES['profesora'])
        self.assertEqual([(t['point'], t['tables'], t['feasible']) for t in r['trajectory']],
                         [(['0', '0'], [1, 2], False), (['6', '0'], [3], False), (['4', '4'], [4, 5, 6], True), (['2', '8'], [7], True)])
        self.assertEqual([s['values'] for s in r['story']], [['20', '2', '0'], ['52', '74']])
        self.assertIn('Sin pivotes', solve(EXAMPLES['minimo'])['story'][1]['text'])

    def test_puntos_del_recorrido_son_las_soluciones_basicas(self):
        r = solve(EXAMPLES['minimo'])
        for e in r['events']:
            T = e['tableau']
            values = {b: T[i + 1][-1] for i, b in enumerate(e['basis'])}
            self.assertEqual(e['point'], [values.get('x1', '0'), values.get('x2', '0')])


class ConclusionTests(unittest.TestCase):
    """Conclusión final: se redacta con los nombres, unidades y valores verificados."""

    def test_optimo_usa_contexto_valores_y_condiciones_que_limitan(self):
        c = solve(EXAMPLES['profesora'])['conclusion']
        self.assertEqual(c['tone'], 'optimal')
        self.assertEqual(c['title'], 'Máximo de Contribución total: 74 unidades monetarias')
        self.assertIn('Producto A = 2 unidades y Producto B = 8 unidades', c['lead'])
        self.assertIn('Z = 74 unidades monetarias (Contribución total)', c['lead'])
        self.assertIn('Producción mínima: se supera el mínimo en 2 unidades', ' '.join(c['points']))
        self.assertIn('Recurso utilizado exactamente y Límite del producto B', c['closing'][0])
        self.assertEqual([(f['symbol'], f['value']) for f in c['figures']], [('x1', '2'), ('x2', '8'), ('Z', '74')])

    def test_minimizacion_variable_en_cero_y_fracciones(self):
        c = solve(model([1, 1], [([1, 0], '>=', '1/2')], sense='min'))['conclusion']
        self.assertIn('x1 = 1/2', c['lead'])
        self.assertIn('x2 queda en 0', c['lead'])
        self.assertIn('mínimo posible', c['lead'])
        self.assertTrue(any('fraccionarios' in t for t in c['closing']))

    def test_infactible_y_no_acotado(self):
        inf = solve(EXAMPLES['infactible'])['conclusion']
        self.assertEqual(inf['tone'], 'infeasible')
        self.assertIn('r = 2', inf['lead'])
        self.assertIn('Pedido mínimo (R1): quedan 2 unidades sin cubrir.', inf['points'])
        noa = solve(EXAMPLES['no_acotado'])['conclusion']
        self.assertEqual(noa['tone'], 'unbounded')
        self.assertIn('no tiene un valor máximo', noa['lead'])
        self.assertIn('Z sube 2 unidades monetarias por cada paso', noa['lead'])
        self.assertNotIn('óptimo', noa['lead'])


class InterfazV2Tests(unittest.TestCase):
    """Interfaz v2 «ruta al óptimo»: mapa, bitácora, recorrido guiado y textos según el estado."""
    def setUp(self):
        self.app = create_app(); self.app.testing = True; self.client = self.app.test_client()

    def informe(self, nombre):
        return self.client.post('/metodo_dos_fases/api/resolver', json=EXAMPLES[nombre]).json['html']

    def test_pagina_tiene_editor_ruta_pestanas_y_recorrido_guiado(self):
        html = self.client.get('/metodo_dos_fases/').data.decode()
        for marca in ('id="df-editor"', 'id="df-route"', 'data-step="fase1"', 'data-step="fase2"', 'id="df-tabs"',
                      'data-tab="guiado"', 'id="df-guided"', 'role="dialog"', 'id="df-preview"', 'id="df-plan-list"',
                      'id="df-context-summary"', 'id="df-examples"'):
            self.assertIn(marca, html)

    def test_informe_optimo_tiene_bitacora_diapositivas_y_conclusion_al_final(self):
        html = self.informe('profesora')
        self.assertEqual(html.count('data-df-slide="tabla"'), 7)  # una diapositiva por tabla
        self.assertIn('data-df-slide="comprobar"', html)
        for titulo in ('¿Qué se hizo?', '¿Qué muestra la tabla?', '¿Quién entra?', '¿Quién sale?'):
            self.assertIn(titulo, html)
        resumen = html[:html.index('id="df-panel-desarrollo"')]
        self.assertLess(resumen.index('id="df-verificacion"'), resumen.index('id="df-conclusion"'))  # la conclusión cierra el resumen
        self.assertIn('Máximo de Contribución total: 74 unidades monetarias', resumen)
        self.assertIn('Planteamiento:', resumen)
        desarrollo = html[html.index('id="df-panel-desarrollo"'):]
        self.assertIn('df-conclusion', desarrollo[desarrollo.index('id="df-resumen"'):])  # y también el desarrollo completo

    def test_sin_graficas(self):
        html = self.informe('profesora') + self.informe('no_acotado')
        pagina = self.client.get('/metodo_dos_fases/').data.decode()
        css = (PROYECTO / 'static/css/dos_fases.css').read_text(encoding='utf-8')
        js = (PROYECTO / 'static/js/dos_fases.js').read_text(encoding='utf-8')
        for texto in (html, pagina, css, js):
            self.assertNotIn('df-map', texto)
        self.assertNotIn('geometry', solve(EXAMPLES['profesora']))

    def test_encabezado_sin_frase_de_relleno(self):
        pagina = self.client.get('/metodo_dos_fases/').data.decode()
        self.assertNotIn('Cada tabla trae su explicación', pagina)
        self.assertNotIn('sirve para estudiar y para exponer', pagina)

    def test_informe_descargable_termina_con_la_conclusion(self):
        data = self.client.post('/metodo_dos_fases/informe', json=EXAMPLES['profesora']).data.decode()
        self.assertEqual(data.count('id="df-conclusion"'), 1)
        self.assertGreater(data.index('id="df-conclusion"'), data.index('id="df-resumen"'))

    def test_no_acotado_no_promete_un_optimo(self):
        html = self.informe('no_acotado')
        self.assertNotIn('hasta el óptimo', html)
        self.assertIn('Fase 2 · Z mejora sin tope', html)
        self.assertNotIn('ya era la mejor', html)
        self.assertIn('CERTIFICADO DE NO ACOTACIÓN', html)
        self.assertIn('Ganancia no tiene máximo', html)

    def test_infactible_explica_que_no_hay_fase_2(self):
        html = self.informe('infactible')
        self.assertIn('Fase 2 · no se ejecuta', html)
        self.assertIn('El modelo no tiene solución factible', html)
        self.assertIn('df-conc-infeasible', html)

    def test_css_no_restablece_botones_con_especificidad_mayor_que_la_del_modulo(self):
        css = (PROYECTO / 'static/css/dos_fases.css').read_text(encoding='utf-8')
        self.assertIn(':where(.df-app button', css)
        self.assertNotIn('\n.df-app button,', css)
