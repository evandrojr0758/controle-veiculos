import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest
import streamlit as st

APP=Path(__file__).with_name('app.py')

class VehicleRegistrationTests(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(APP.read_text())
  functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'vehicle_registration_values','register_vehicle'}]
  import re
  self.ns={'re':re}
  exec(compile(ast.Module(body=functions,type_ignores=[]),'app.py','exec'),self.ns)

 def test_normalizes_both_plate_formats(self):
  for plate,expected in [('abc-1234','ABC1234'),(' abc1d23 ','ABC1D23')]:
   self.assertEqual(self.ns['vehicle_registration_values'](plate,' Fiat Strada ','BA',0),{'placa':expected,'modelo':'FIAT STRADA','unidade':'BA','km_atual':0})

 def test_rejects_invalid_fields_and_duplicate_in_other_unit(self):
  for args in [('BAD','Modelo','ARA',1,()),('ABC1234',' ','ARA',1,()),('ABC1234','Modelo','TODAS',1,()),('ABC1234','Modelo','ARA',None,()),('ABC1234','Modelo','ARA',-1,()),('ABC1234','Modelo','ARA',1,[{'placa':'ABC-1234','unidade':'BA'}])]:
   with self.subTest(args=args),self.assertRaises(ValueError):
    self.ns['vehicle_registration_values'](*args)

 def test_insert_only_and_confirmation(self):
  values=self.ns['vehicle_registration_values']('ABC1234','Modelo','ARA',10)
  db=MagicMock()
  self.ns['DB']=db
  db.table.return_value.insert.return_value.execute.return_value=SimpleNamespace(data=[values])
  self.assertEqual(self.ns['register_vehicle'](values),values)
  db.table.return_value.update.assert_not_called()
  db.table.return_value.upsert.assert_not_called()
  db.table.return_value.insert.return_value.execute.return_value=SimpleNamespace(data=[])
  with self.assertRaises(RuntimeError):self.ns['register_vehicle'](values)

 def test_concurrent_duplicate_explained(self):
  class Duplicate(Exception):code='23505'
  db=MagicMock()
  db.table.return_value.insert.return_value.execute.side_effect=Duplicate()
  self.ns['DB']=db
  with self.assertRaisesRegex(ValueError,'já está cadastrada'):self.ns['register_vehicle']({'placa':'ABC1234'})

 def test_form_can_register_first_vehicle(self):
  class Query:
   def __init__(self,db,table):self.db=db;self.name=table;self.payload=None
   def select(self,*a,**k):return self
   def order(self,*a,**k):return self
   def eq(self,*a,**k):return self
   def insert(self,payload):self.payload=payload;return self
   def execute(self):
    if self.payload is not None:
     self.db.rows.append(dict(self.payload))
     return SimpleNamespace(data=[self.payload])
    return SimpleNamespace(data=list(self.db.rows) if self.name=='veiculos' else [])
  db=SimpleNamespace(rows=[])
  db.table=lambda name:Query(db,name)
  st.cache_resource.clear()
  with patch('supabase.create_client',return_value=db):
   at=AppTest.from_file(str(APP))
   at.secrets['SUPABASE_URL']='https://example.supabase.co'
   at.secrets['SUPABASE_KEY']='test-only'
   at.query_params.update(view='admin',tab='veiculos',unidade='BA')
   at.run()
   self.assertFalse(at.exception)
   self.assertEqual(at.selectbox[1].value,'BA')
   at.text_input[0].set_value('abc1d23')
   at.text_input[1].set_value('Fiat Strada')
   at.number_input[0].set_value(12345)
   next(b for b in at.button if 'CADASTRAR VEÍCULO' in b.label).click()
   at.run()
   self.assertFalse(at.exception)
   self.assertEqual(db.rows,[{'placa':'ABC1D23','modelo':'FIAT STRADA','unidade':'BA','km_atual':12345}])
   self.assertTrue(any('cadastrado' in x.value for x in at.success))
   self.assertTrue(any('ABC1D23' in x.value for x in at.markdown))
  st.cache_resource.clear()

if __name__=='__main__':unittest.main()
