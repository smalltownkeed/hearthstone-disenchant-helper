import unittest
from core import finish_from_craft_cost, auto_count
from workflow import Card

class AutoSelectionTests(unittest.TestCase):
    def test_cost_identifies_normal_and_golden_only(self):
        self.assertEqual(finish_from_craft_cost('普通',40),'普通')
        self.assertEqual(finish_from_craft_cost('普通',400),'金色')
        self.assertEqual(finish_from_craft_cost('传说',1600),'普通')
        self.assertEqual(finish_from_craft_cost('传说',3200),'金色')
        for rarity,cost in [('普通',None),('普通',0),('未知',400),('普通',1600)]:
            self.assertIsNone(finish_from_craft_cost(rarity,cost))
    def test_known_cards_auto_selected_without_manual_approval(self):
        c=Card(None,'测试',4,'普通',True,0,finish='普通',page=1)
        self.assertEqual(auto_count(c,'只分解多余的'),2)
        self.assertEqual(auto_count(c,'全部分解'),4)
    def test_special_uncertain_and_disabled_never_auto_select(self):
        for finish in ('异画','钻石',None):
            c=Card(None,'测试',4,'普通',True,0,finish=finish,page=1)
            self.assertEqual(auto_count(c,'全部分解'),0)
        c=Card(None,'核心',4,'普通',False,0,finish='普通',page=1)
        self.assertEqual(auto_count(c,'全部分解'),0)

