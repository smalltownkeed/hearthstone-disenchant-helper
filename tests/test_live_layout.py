from pathlib import Path
from PIL import Image
import unittest
from vision import Vision, normalize

class LiveLayoutTests(unittest.TestCase):
    def test_real_fullscreen_collection_is_recognized(self):
        p = Path(__file__).resolve().parents[1] / 'assets' / 'live-collection.png'
        im = normalize(Image.open(p))
        self.assertTrue(Vision(load_ocr=False).is_collection(im))


    def test_core_card_detail_can_be_closed_but_never_disassembled(self):
        p = Path(__file__).resolve().parents[1] / 'assets' / 'live-core-detail.png'
        im = normalize(Image.open(p))
        v = Vision(load_ocr=False)
        self.assertTrue(v.is_detail(im))
        self.assertFalse(v.button_ready(im))
