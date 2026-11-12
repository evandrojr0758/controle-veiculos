import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

APP = Path(__file__).with_name('app.py')

class VehicleEditTests(unittest.TestCase):
 def setUp(self):
  tree = ast.parse(APP.read_text())
  names = {'vehicle_registration_values', 'vehicle_edit_values', 'edit_vehicle'}
  nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
  self.ns = {'re': re}
  exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP), 'exec'), self.ns)
  self.vehicle = {'placa':'ABC1D23','modelo':'MODELO','unidade':'ARA',
                  'km_atual':12345,'atualizado_em':'2026-11-12T12:00:00+00:00'}

 def test_original_plate_is_not_duplicate(self):
  values = self.ns['vehicle_edit_values'](self.vehicle,'abc-1d23',' Novo modelo ','BA',[self.vehicle])
  self.assertEqual(values, {'placa':'ABC1D23','modelo':'NOVO MODELO','unidade':'BA'})

 def test_other_plate_is_duplicate(self):
  with self.assertRaisesRegex(ValueError,'já está cadastrada'):
   self.ns['vehicle_edit_values'](self.vehicle,'XYZ1234','Novo','BA',[self.vehicle,{'placa':'XYZ1234'}])

 def test_edit_does_not_write_odometer_revision_or_photo(self):
  values = self.ns['vehicle_edit_values'](self.vehicle,'ABC1234','Novo','ARA',[self.vehicle])
  db = MagicMock()
  self.ns['DB'] = db
  db.rpc.return_value.execute.return_value = SimpleNamespace(data={**self.vehicle,**values})
  self.ns['edit_vehicle'](self.vehicle,values)
  db.rpc.assert_called_once_with('editar_cadastro_veiculo',{
   'p_placa_original':'ABC1D23','p_placa':'ABC1234','p_modelo':'NOVO',
   'p_unidade':'ARA','p_atualizado_em':self.vehicle['atualizado_em']})
  db.table.assert_not_called()

 def test_unconfirmed_update_never_succeeds(self):
  db = MagicMock()
  self.ns['DB'] = db
  values = {'placa':'ABC1D23','modelo':'NOVO','unidade':'ARA'}
  for result in (None, [], {}, self.vehicle):
   with self.subTest(result=result):
    db.rpc.return_value.execute.return_value = SimpleNamespace(data=result)
    with self.assertRaises(RuntimeError):
     self.ns['edit_vehicle'](self.vehicle,values)

 def test_photo_and_metadata_use_one_atomic_operation(self):
  values = {'placa':'ABC1D23','modelo':'NOVO','unidade':'ARA','foto':'data:image/png;base64,TEST'}
  db = MagicMock()
  self.ns['DB'] = db
  db.rpc.return_value.execute.return_value = SimpleNamespace(data={**self.vehicle,**values})
  self.ns['edit_vehicle'](self.vehicle,values)
  self.assertEqual(db.rpc.call_args.args[0],'editar_cadastro_veiculo_com_foto')
  self.assertEqual(db.rpc.call_args.args[1]['p_foto'],values['foto'])
  db.table.assert_not_called()

 def test_form_edits_vehicle_with_mock_database(self):
  import streamlit as st
  from streamlit.testing.v1 import AppTest
  vehicle = {**self.vehicle,'foto':'original.jpg','km_ultima_revisao':10000,'intervalo_revisao':10000}
  class Query:
   def __init__(self,name):self.name=name
   def select(self,*a,**kw):return self
   def order(self,*a,**kw):return self
   def eq(self,*a,**kw):return self
   def execute(self):return SimpleNamespace(data=[dict(vehicle)] if self.name=='veiculos' else [])
  def rpc(name,params):
   self.assertEqual(name,'editar_cadastro_veiculo')
   def execute():
    vehicle.update(placa=params['p_placa'],modelo=params['p_modelo'],unidade=params['p_unidade'])
    return SimpleNamespace(data=dict(vehicle))
   return SimpleNamespace(execute=execute)
  db=SimpleNamespace(table=lambda name:Query(name),rpc=rpc)
  st.cache_resource.clear()
  with patch.dict('sys.modules',{'supabase':SimpleNamespace(create_client=lambda *a:db)}):
   at=AppTest.from_file(str(APP))
   at.secrets.update(SUPABASE_URL='https://example.supabase.co',SUPABASE_KEY='test-only')
   at.query_params.update(view='admin',tab='veiculos',unidade='TODAS')
   at.run()
   self.assertFalse(at.exception)
   self.assertTrue(any('Editar veículo' in e.label for e in at.expander))
   next(x for x in at.text_input if x.value=='MODELO').set_value('Hilux atualizada')
   next(b for b in at.button if 'SALVAR ALTERAÇÕES' in b.label).click()
   at.run()
   self.assertFalse(at.exception)
   self.assertEqual(vehicle['modelo'],'HILUX ATUALIZADA')
   self.assertEqual(vehicle['km_atual'],12345)
   self.assertEqual(vehicle['foto'],'original.jpg')
   self.assertEqual(vehicle['km_ultima_revisao'],10000)
   self.assertTrue(any('atualizado' in x.value for x in at.success))
  st.cache_resource.clear()

if __name__=='__main__':
 unittest.main()
