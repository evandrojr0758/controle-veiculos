import base64
from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from PIL import Image
from vehicle_photos import MAX_UPLOAD_BYTES, PNG_PREFIX, photo_bytes, read_photo, remove_background

def photo(mode='RGB',color='white'):
 output=BytesIO()
 Image.new(mode,(80,60),color).save(output,format='PNG')
 return output.getvalue()

class VehiclePhotoTests(TestCase):
 def test_validates_file_content_and_size(self):
  for raw in (b'',b'not an image',b'x'*(MAX_UPLOAD_BYTES+1)):
   with self.subTest(size=len(raw)),self.assertRaises(ValueError):read_photo(raw)
  output=BytesIO()
  Image.new('RGB',(10,10)).save(output,format='GIF')
  with self.assertRaises(ValueError):read_photo(output.getvalue())

 def test_accepts_normal_photo(self):
  image=read_photo(photo())
  self.assertEqual(image.size,(80,60))
  self.assertEqual(image.mode,'RGB')

 def test_removal_returns_transparent_png_without_metadata(self):
  cutout=Image.new('RGBA',(80,60),(0,0,0,0))
  cutout.paste((255,0,0,255),(20,20,60,40))
  engine=SimpleNamespace(remove=lambda *a,**k:cutout)
  with patch.dict('sys.modules',{'rembg':engine}),patch('vehicle_photos.removal_session',return_value=object()):
   result=remove_background(photo())
  png=photo_bytes(result)
  image=Image.open(BytesIO(png))
  self.assertEqual(image.mode,'RGBA')
  self.assertEqual(image.getchannel('A').getextrema(),(0,255))
  self.assertEqual(image.size,(80,60))
  self.assertFalse(image.getexif())

 def test_engine_failure_does_not_return_original_with_background(self):
  def failure(*a,**k):raise RuntimeError('offline')
  with patch.dict('sys.modules',{'rembg':SimpleNamespace(remove=failure)}),patch('vehicle_photos.removal_session',return_value=object()):
   with self.assertRaisesRegex(ValueError,'foto anterior será mantida'):remove_background(photo())

 def test_rejects_empty_or_opaque_removal(self):
  for color in ((0,0,0,0),(255,0,0,255)):
   cutout=Image.new('RGBA',(80,60),color)
   with patch.dict('sys.modules',{'rembg':SimpleNamespace(remove=lambda *a,**k:cutout)}),patch('vehicle_photos.removal_session',return_value=object()):
    with self.assertRaisesRegex(ValueError,'separar o veículo'):remove_background(photo())

 def test_only_png_data_uris_are_rendered(self):
  valid=PNG_PREFIX+base64.b64encode(photo()).decode()
  self.assertIsNotNone(photo_bytes(valid))
  for value in (None,'foto.jpg','data:image/svg+xml;base64,abc',PNG_PREFIX+'!!!',PNG_PREFIX+base64.b64encode(b'bad png').decode()):
   self.assertIsNone(photo_bytes(value))

if __name__=='__main__':main()
