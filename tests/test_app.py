import tkinter as tk
import unittest
from app import App
from workflow import Card
from vision import Vision

class GuiSelectionTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root)
        self.app.cards=[Card(Vision(False).detail,'测试卡',4,'普通',True,0,finish='普通',page=1)]
        self.app.binding=(123,(0,0,2048,1152))
    def tearDown(self): self.root.destroy()
    def test_scan_results_are_selected_automatically(self):
        self.assertEqual(len(self.app.reviewed()),1)
    def test_one_toggle_keeps_card_no_type_selection(self):
        self.app.render()
        self.app.tree.selection_set('0')
        self.app.toggle_selected()
        self.assertEqual(self.app.reviewed(),[])
    def test_mode_change_recalculates_without_rescanning(self):
        self.app.mode_box.set('全部分解')
        self.app.mode_box.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertEqual(len(self.app.cards),1)
        self.assertIsNotNone(self.app.binding)
        self.assertIn('4',self.app.summary.get())
    def test_interruption_invalidates_selection(self):
        self.app.messages.put(('error','count changed'))
        self.app.poll()
        self.assertEqual(self.app.reviewed(),[])
        self.assertIsNone(self.app.binding)


    def test_neutral_not_offered_without_end_page_detection(self):
        self.assertNotIn('中立',self.app.class_box['values'])
        self.assertEqual(len(self.app.class_box['values']),11)
