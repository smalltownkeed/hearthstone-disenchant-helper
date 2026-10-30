import importlib.util
from pathlib import Path
import unittest
from PIL import Image
from vision import Vision

@unittest.skipUnless(importlib.util.find_spec('rapidocr'),'OCR未安装')
class WarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.v=Vision()
    def test_exact_deck_warning_recognized(self):
        im=Image.open(Path(__file__).resolve().parents[1]/'assets/deck-warning.png').convert('RGB')
        self.assertTrue(self.v.deck_warning(im))
    def test_normal_detail_and_collection_are_not_confirmed(self):
        self.assertFalse(self.v.deck_warning(self.v.detail))
        self.assertFalse(self.v.deck_warning(self.v.collection))
    def test_only_given_warning_text_allowed(self):
        im=Image.open(Path(__file__).resolve().parents[1]/'assets/deck-warning.png').convert('RGB')
        im.paste((45,45,45),(775,520,1380,580))
        self.assertFalse(self.v.deck_warning(im))


    def make_io(self,frames):
        from types import SimpleNamespace
        from workflow import Card,CardIO
        class Desktop:
            def __init__(self): self.frames=list(frames);self.clicks=[]
            def capture(self): return self.frames.pop(0)
            def sleep(self,s): pass
            def check(self): pass
            def click(self,x,y): self.clicks.append((x,y))
        reference=Image.open(Path(__file__).resolve().parents[1]/'assets/deck-warning.png').convert('RGB')
        d=Desktop()
        e=SimpleNamespace(d=d,v=self.v,log=lambda s:None)
        io=CardIO(e,Card(reference,'发挥优势',1,'普通',True,0,'普通',7))
        io.expected=1
        return io,d
    def test_confirm_specific_warning_once(self):
        io,d=self.make_io([self.v.warning,self.v.detail])
        io.settle()
        self.assertEqual(d.clicks,[(892,694)])
    def test_persistent_warning_never_retried(self):
        from core import StopRun
        io,d=self.make_io([self.v.warning,self.v.warning])
        with self.assertRaises(StopRun):io.settle()
        self.assertEqual(d.clicks,[(892,694)])
    def test_unknown_warning_never_confirmed(self):
        unknown=self.v.warning.copy();unknown.paste((45,45,45),(775,520,1380,580))
        io,d=self.make_io([unknown])
        io.settle()
        self.assertEqual(d.clicks,[])
