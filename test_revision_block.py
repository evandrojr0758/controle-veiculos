import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock


class RevisionBlockTests(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(Path(__file__).with_name('app.py').read_text())
  names={'revision','revision_usage_blocked','confirmar_km_inicial'}
  functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
  for node in functions:node.decorator_list=[]
  self.ns={'REVISION_BLOCK_MESSAGE':'REVISÃO URGENTE'}
  exec(compile(ast.Module(body=functions,type_ignores=[]),'app.py','exec'),self.ns)
  self.vehicle={'km_ultima_revisao':60000,'intervalo_revisao':10000,'km_atual':69000}

 def test_threshold_and_overdue(self):
  for left,blocked in [(1001,False),(1000,True),(999,True),(0,True),(-765,True)]:
   with self.subTest(left=left):
    self.assertEqual(self.ns['revision_usage_blocked']({**self.vehicle,'km_atual':70000-left}),blocked)

 def test_entered_odometer_and_lower_reading(self):
  check=self.ns['revision_usage_blocked']
  self.assertTrue(check({**self.vehicle,'km_atual':68000},69000))
  self.assertTrue(check(self.vehicle,68000))

 def test_completed_revision_releases_vehicle(self):
  self.assertFalse(self.ns['revision_usage_blocked']({**self.vehicle,'km_ultima_revisao':69000}))

 def test_stale_confirmation_checks_database_before_writing(self):
  st=MagicMock()
  st.columns.return_value=(MagicMock(),MagicMock())
  st.columns.return_value[0].button.return_value=True
  db=MagicMock()
  db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value=SimpleNamespace(data=[self.vehicle])
  self.ns.update(st=st,DB=db,km=str)
  self.ns['confirmar_km_inicial']('TEST123','Oficina','João',68000,'João')
  st.error.assert_called_once_with('REVISÃO URGENTE')
  db.table.return_value.insert.assert_not_called()
  db.table.return_value.update.assert_not_called()

 def test_read_failure_does_not_register_trip(self):
  st=MagicMock()
  st.columns.return_value=(MagicMock(),MagicMock())
  st.columns.return_value[0].button.return_value=True
  db=MagicMock()
  db.table.side_effect=RuntimeError('offline')
  self.ns.update(st=st,DB=db,km=str)
  self.ns['confirmar_km_inicial']('TEST123','Oficina','João',68000,'João')
  st.error.assert_called_once()


if __name__=='__main__':unittest.main()
