import unittest
from gps_bridge import gps_suggestion
class GPSSuggestionTest(unittest.TestCase):
 def test_suggestion(self):
  self.assertEqual(gps_suggestion({'id':123,'km_inicial':100010},{'gps_id':'123','gps_km':'20.25'}),100030)
 def test_invalid_and_wrong_movement(self):
  m={'id':123,'km_inicial':100010}
  self.assertIsNone(gps_suggestion(m,{'gps_id':'124','gps_km':'20'}))
  for v in ('NaN','inf','-1','abc','100001'):
   self.assertIsNone(gps_suggestion(m,{'gps_id':'123','gps_km':v}))
if __name__=='__main__':unittest.main()
