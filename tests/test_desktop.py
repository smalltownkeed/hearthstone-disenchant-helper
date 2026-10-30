import time
import unittest
from desktop import Desktop

class InputTimingTests(unittest.TestCase):
    def test_right_click_is_held_across_game_frames(self):
        class InputRecorder:
            def __init__(self): self.events=[]
            def SetCursorPos(self, x, y): pass
            def mouse_event(self, flag, a, b, c, d):
                self.events.append((flag,time.monotonic()))
        d=Desktop.__new__(Desktop)
        d.u=InputRecorder()
        d.rect=(0,0,2048,1152)
        d.check=lambda: None
        d.click(400,300,right=True)
        self.assertEqual([e[0] for e in d.u.events], [8,16])
        self.assertGreaterEqual(d.u.events[1][1]-d.u.events[0][1], .05)


    def test_focus_lost_during_settle_blocks_mouse_down(self):
        from core import StopRun
        class InputRecorder:
            def __init__(self): self.events=[]
            def SetCursorPos(self,x,y): pass
            def mouse_event(self,*args): self.events.append(args)
        d=Desktop.__new__(Desktop)
        d.u=InputRecorder(); d.rect=(0,0,2048,1152)
        lost=[False]
        def check():
            if lost[0]: raise StopRun('focus lost')
        d.check=check
        d.sleep=lambda seconds: lost.__setitem__(0,True)
        with self.assertRaises(StopRun): d.click(400,300)
        self.assertEqual(d.u.events,[])

    def test_wheel_mapping_matches_observed_game_direction(self):
        class Recorder:
            def __init__(self):self.events=[]
            def SetCursorPos(self,*args):pass
            def mouse_event(self,*args):self.events.append(args)
        d=Desktop.__new__(Desktop);d.u=Recorder();d.rect=(0,0,2048,1152)
        d.check=lambda:None;d.sleep=lambda s:None
        d.scroll(-120)
        d.scroll(120)
        self.assertEqual([e[3] for e in d.u.events],[120,(-120)&0xffffffff])
