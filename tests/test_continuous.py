import unittest
from core import StopRun
from workflow import Engine

class PageVision:
    def current_class(self,frame): return frame[1]
    def page_number(self,frame): return frame[0]
    def is_collection(self,frame): return True
    def class_matches(self,frame,selected): return frame[1]==selected

class Pages:
    def __init__(self,start=3,blocked=False):
        self.page=start
        self.blocked=blocked
    def capture(self): return (self.page,'死亡骑士' if self.page<=3 else '恶魔猎手')
    def check(self): pass
    def sleep(self,t): pass
    def scroll(self,amount):
        if not self.blocked:
            self.page=max(1,min(4,self.page+(-1 if amount>0 else 1)))

class ScanEngine(Engine):
    def select_class(self): return self.collection()
    def scan_page(self,page):
        self.visited.append(page)
        return [page]
    def __init__(self,d):
        super().__init__(d,PageVision(),'死亡骑士')
        self.visited=[]

class ContinuousTests(unittest.TestCase):
    def test_starts_at_first_page_and_stops_at_class_boundary(self):
        e=ScanEngine(Pages())
        self.assertEqual(e.scan(),[1,2,3])
        self.assertEqual(e.visited,[1,2,3])
        self.assertEqual(e.d.page,3)
    def test_unresponsive_paging_does_not_claim_complete(self):
        e=ScanEngine(Pages(blocked=True))
        with self.assertRaises(StopRun): e.scan()
    def test_goto_requires_exact_page(self):
        e=ScanEngine(Pages(start=1))
        e.goto_page(3)
        self.assertEqual(e.d.page,3)


    def test_forward_unresponsive_from_first_page_is_not_complete(self):
        e=ScanEngine(Pages(start=1,blocked=True))
        with self.assertRaises(StopRun):e.scan()
    def test_forward_unresponsive_mid_scan_is_not_complete(self):
        class Midway(Pages):
            def scroll(self,amount):
                if amount<0 and self.page==2:return
                super().scroll(amount)
        e=ScanEngine(Midway(start=1))
        with self.assertRaises(StopRun):e.scan()
        self.assertEqual(e.visited,[1,2])
