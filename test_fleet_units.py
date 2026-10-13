import unittest
from fleet_units import resolve_unit, scope_fleet, route_params

class FleetUnitTests(unittest.TestCase):
 def setUp(self):
  self.vehicles=[{'placa':'ARA0001','unidade':'ARA'},{'placa':'BAA0001','unidade':'BA'}]
  self.opened={v['placa']:{'placa':v['placa']} for v in self.vehicles}
 def test_legacy_routes_and_consolidated_manager(self):
  self.assertEqual(resolve_unit({'view':'vehicles'}),'ARA')
  self.assertEqual(resolve_unit({'view':'panel'}),'ARA')
  self.assertEqual(resolve_unit({'view':'admin'}),'TODAS')
 def test_bahia_fleet_and_counts_exclude_aracruz_trips(self):
  vs,opened=scope_fleet(self.vehicles,self.opened,'BA')
  self.assertEqual([v['placa'] for v in vs],['BAA0001'])
  self.assertEqual(list(opened),['BAA0001'])
 def test_bahia_navigation_preserves_unit(self):
  for view in ('vehicles','out','return','panel','admin'):
   params=route_params(view,'BA',plate='BAA0001')
   self.assertEqual(resolve_unit(params),'BA')
 def test_native_return_infers_bahia_from_plate(self):
  self.assertEqual(resolve_unit({'view':'vehicles','native':'android','plate':'BAA0001','gps_return':'1'},self.vehicles),'BA')
 def test_all_units_only_in_manager(self):
  self.assertEqual(len(scope_fleet(self.vehicles,self.opened,'TODAS')[0]),2)
  self.assertEqual(resolve_unit({'view':'panel','unidade':'TODAS'}),'ARA')
  self.assertEqual(route_params('vehicles','TODAS')['unidade'],'ARA')

if __name__=='__main__':unittest.main()