from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from consumption import report_rows, load_reports, monthly_totals


def fixtures():
    def row(day, odo, qty, value, fuel=True, rate=10):
        return {'data': '2026-10-' + day, 'hora': '12:00', 'cupom': day,
                'produto': 'GASOLINA' if fuel else 'FILTRO', 'combustivel': fuel,
                'km_atual': odo, 'km_rodado_informado': 100,
                'km_l_informado': rate, 'quantidade': qty,
                'preco_unitario': value / qty, 'valor': value}
    return [{'periodo': '2026-10', 'origem': 'Posto de teste', 'veiculos': [
        {'placa': 'ABC-1D23', 'modelo': 'Teste A', 'km_anterior': 1000,
         'registros': [row('01', 1100, 10, 60), row('02', 1200, 1, 50, False)]},
        {'placa': 'DEF-4G56', 'modelo': 'Teste B', 'km_anterior': 2000,
         'registros': [row('01', 2500, 20, 120), row('02', 2300, 10, 60)]},
        {'placa': 'HIJ-7K89', 'modelo': 'Teste C', 'km_anterior': 0,
         'registros': [row('01', 0, 1, 30, False)]}]}]


class Query:
    def __init__(self, table): self.table = table
    def select(self, *args, **kwargs): return self
    def order(self, *args, **kwargs): return self
    def eq(self, *args, **kwargs): return self
    def execute(self):
        return SimpleNamespace(data=[{'conteudo': r} for r in fixtures()] if self.table == 'consumo_relatorios' else [])


def database():
    return SimpleNamespace(table=lambda name: Query(name))


class ConsumptionTests(unittest.TestCase):
    def test_separates_products_and_missing_odometer(self):
        rows = report_rows(fixtures(), [])
        self.assertEqual(sum(r['litros'] for r in rows), 40)
        self.assertEqual(sum(r['valor'] for r in rows), 240)
        self.assertEqual(sum(r['outras_compras'] for r in rows), 80)
        self.assertEqual(sum(r['abastecimentos'] for r in rows), 3)
        self.assertIsNone(rows[2]['km'])
        self.assertEqual(load_reports(database()), fixtures())

    def test_exact_plate_link_and_unit_filter(self):
        fleet = [{'placa': 'ABC1D23', 'modelo': 'TESTE', 'unidade': 'ARA'},
                 {'placa': 'DEF4G57', 'modelo': 'OUTRO', 'unidade': 'BA'}]
        rows = report_rows(fixtures(), fleet, 'ARA')
        self.assertEqual([r['placa'] for r in rows], ['ABC-1D23'])
        self.assertEqual(report_rows(fixtures(), fleet, 'BA'), [])
        all_rows = report_rows(fixtures(), fleet)
        self.assertFalse(all_rows[1]['vinculado'])

    def test_odometer_reset_and_anomalies_suppress_efficiency(self):
        rows = report_rows(fixtures(), [])
        self.assertEqual(rows[1]['km'], 300)
        self.assertTrue(rows[1]['alertas'])
        self.assertIsNone(rows[1]['km_l'])
        self.assertIsNone(rows[1]['custo_km'])

    def test_merges_sources_without_duplicate_vehicles_or_distance(self):
        import copy
        reports = fixtures()
        extra = copy.deepcopy(reports[0])
        extra['origem'] = 'Segundo posto'
        extra['veiculos'] = [extra['veiculos'][0]]
        vehicle = extra['veiculos'][0]
        vehicle['placa'] = 'ABC1D23'
        vehicle['km_anterior'] = None
        vehicle['registros'] = [dict(vehicle['registros'][0], hora='18:00', km_atual=1150)]
        rows = report_rows(reports + [extra, extra, reports[0]], [])
        selected = next(r for r in rows if r['placa'] == 'ABC-1D23')
        self.assertEqual(len(rows), 3)
        self.assertEqual(selected['litros'], 20)
        self.assertEqual(selected['valor'], 120)
        self.assertEqual(selected['abastecimentos'], 2)
        self.assertEqual(selected['km'], 200)
        self.assertEqual(len(selected['registros']), 3)
        self.assertEqual(len({r['origem'] for r in selected['registros']}), 2)
        self.assertFalse(selected['alertas'])

    def test_new_source_without_opening_odometer_uses_available_readings(self):
        reports = fixtures()
        reports[0]['veiculos'][0]['km_anterior'] = None
        selected = report_rows(reports, [])[0]
        self.assertEqual(selected['km'], 100)
        self.assertIsNone(selected['km_l'])
        self.assertTrue(any('Sem odômetro anterior' in message for message in selected['alertas']))

    def test_month_rankings_keep_metrics_and_missing_distance_separate(self):
        rows = [
            {'periodo': '2026-09', 'litros': 50.123, 'valor': 300.74, 'abastecimentos': 2, 'km': 100},
            {'periodo': '2026-10', 'litros': 20, 'valor': 120, 'abastecimentos': 1, 'km': 300},
            {'periodo': '2026-10', 'litros': 10, 'valor': 60, 'abastecimentos': 1, 'km': None},
        ]
        months = monthly_totals(rows)
        self.assertEqual(len(months), 2)
        self.assertEqual(max(months, key=lambda r: r['litros'])['periodo'], '2026-09')
        self.assertEqual(max(months, key=lambda r: r['km'])['periodo'], '2026-10')
        self.assertEqual(months[1]['km'], 300)
        self.assertEqual(months[1]['litros'], 30)
        self.assertEqual(months[1]['valor'], 180)
        self.assertEqual(months[1]['veiculos'], 2)
        self.assertEqual(months[1]['pendentes_km'], 1)
        missing = monthly_totals([dict(rows[2], periodo='2026-11')])
        self.assertIsNone(missing[0]['km'])

    def test_admin_consumption_route(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        st.cache_resource.clear()
        with patch.dict('sys.modules', {'supabase': SimpleNamespace(create_client=lambda *a: database())}):
            app = AppTest.from_file(str(Path(__file__).with_name('app.py')))
            app.secrets['SUPABASE_URL'] = 'https://example.supabase.co'
            app.secrets['SUPABASE_KEY'] = 'test-only'
            app.query_params.update(view='admin', tab='consumo', unidade='TODAS')
            app.run(timeout=30)
            self.assertEqual(len(app.exception), 0, str(app.exception))
            self.assertTrue(any(b.label == '⛽ CONSUMO' for b in app.button))
            self.assertEqual(app.metric[0].value, 'R$ 240,00')
            self.assertTrue(any('Ranking · Mais abastecidos' in m.value for m in app.markdown))
            self.assertTrue(any('Ranking · Mais rodados' in m.value for m in app.markdown))
            self.assertTrue(any('Meses · Mais litros abastecidos' in m.value for m in app.markdown))
            self.assertTrue(any('Meses · Mais quilômetros rodados' in m.value for m in app.markdown))
            self.assertTrue(any("role='img'" in m.value for m in app.markdown))
            app.selectbox[2].set_value('DEF-4G56').run(timeout=30)
            self.assertEqual(len(app.exception), 0, str(app.exception))
            self.assertTrue(any('diminuiu' in w.value for w in app.warning))
            self.assertEqual(len(app.dataframe[1].value), 2)
        st.cache_resource.clear()

    def test_permission_failure_is_handled_without_details(self):
        from streamlit.testing.v1 import AppTest
        code = """
from consumption import render_consumption
class Blocked:
    def table(self, *args):
        raise PermissionError('private internal error')
render_consumption([], 'TODAS', {}, Blocked())
"""
        app = AppTest.from_string(code).run(timeout=30)
        self.assertEqual(len(app.exception), 0, str(app.exception))
        self.assertIn('aguarda', app.info[0].value)
        self.assertNotIn('internal', app.info[0].value)


if __name__ == '__main__': unittest.main()
