import unittest
from pathlib import Path
from PIL import Image, ImageEnhance
from core import parse_count
from vision import Vision, similar, normalize, same_variant

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
class VisionTests(unittest.TestCase):
    def test_ambiguous_counts_rejected(self):
        for text in ('1', 'xO', 'x0', 'x-2', 'x2 x3', '+5', 'x1000', ''):
            self.assertIsNone(parse_count(text, .999))
        self.assertIsNone(parse_count('x3', .7))
        self.assertEqual(parse_count('× 12', .99), 12)
    def test_reference_screens_are_distinct(self):
        v = Vision(load_ocr=False)
        collection = normalize(Image.open(ASSETS / 'collection.png'))
        detail = normalize(Image.open(ASSETS / 'detail.png'))
        self.assertTrue(v.is_collection(collection))
        self.assertFalse(v.is_collection(detail))
        self.assertTrue(v.is_detail(detail))
        self.assertFalse(v.is_detail(collection))
        self.assertTrue(v.button_ready(detail))
    def test_unrelated_image_is_not_variant(self):
        detail = normalize(Image.open(ASSETS / 'detail.png'))
        collection = normalize(Image.open(ASSETS / 'collection.png'))
        self.assertTrue(same_variant(detail, detail.copy()))
        self.assertFalse(same_variant(detail, collection))
        altered = detail.copy()
        altered.paste((240, 215, 10), (1116, 210, 1171, 680))
        self.assertFalse(same_variant(detail, altered))
    def test_wrong_aspect_or_small_capture_rejected(self):
        for size in ((1024, 768), (640, 360)):
            with self.assertRaises(ValueError):
                normalize(Image.new('RGB', size))
    def test_similar_rejects_flat_frames(self):
        self.assertLess(similar(Image.new('RGB',(50,50)), Image.new('RGB',(50,50))), .9)

if __name__ == '__main__':
    unittest.main()

