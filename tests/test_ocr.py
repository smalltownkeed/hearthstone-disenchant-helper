from pathlib import Path
import importlib.util
import unittest
from vision import Vision

@unittest.skipUnless(importlib.util.find_spec('rapidocr'), 'OCR组件尚未安装')
class RealOCRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vision = Vision()
    def test_provided_count_and_rarity(self):
        self.assertEqual(self.vision.count(self.vision.detail), 1)
        self.assertEqual(self.vision.rarity(self.vision.detail), '普通')
    def test_provided_class_title(self):
        self.assertTrue(self.vision.class_matches(self.vision.collection, '死亡骑士'))
        self.assertFalse(self.vision.class_matches(self.vision.collection, '法师'))


    def test_normal_card_is_auto_classified_without_user_input(self):
        self.assertEqual(self.vision.auto_finish(self.vision.detail),'普通')
        self.assertEqual(self.vision.page_number(self.vision.collection),1)
        self.assertEqual(self.vision.name(self.vision.detail),'时空冰封勇士')
    def test_uncraftable_core_version_is_never_auto_selected(self):
        from PIL import Image
        p=Path(__file__).resolve().parents[1]/'assets/live-core-detail.png'
        self.assertIsNone(self.vision.auto_finish(Image.open(p).convert('RGB')))

    def test_real_signature_is_kept_through_auto_selection(self):
        from PIL import Image
        from workflow import Card
        from core import auto_count
        im=Image.open(Path(__file__).resolve().parents[1]/'assets/live-signature-detail.png').convert('RGB')
        v=self.vision
        c=Card(im,v.name(im),v.count(im),v.rarity(im),v.button_ready(im),5,v.auto_finish(im),1)
        self.assertIsNone(c.finish)
        self.assertEqual(auto_count(c,'全部分解'),0)
