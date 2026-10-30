import unittest
from core import Approval, planned_count, run_card, StopRun

class PolicyTests(unittest.TestCase):
    def test_protected_and_unknown_never_approved(self):
        for finish in ('保留', '异画', '钻石', '', '未知'):
            self.assertEqual(planned_count(Approval(finish, 8, '传说'), '全部分解'), 0)

    def test_all_and_extra(self):
        cases = [('普通', 5, '普通', '全部分解', 5),
                 ('普通', 5, '普通', '只分解多余的', 3),
                 ('金色', 3, '传说', '只分解多余的', 2),
                 ('普通', 1, '史诗', '只分解多余的', 0)]
        for f, n, r, mode, want in cases:
            self.assertEqual(planned_count(Approval(f, n, r), mode), want)

    def test_invalid_inputs_rejected(self):
        for count in (None, 0, -1, 1.5, True, 1000):
            with self.assertRaises(ValueError):
                planned_count(Approval('普通', count, '普通'), '全部分解')
        for rarity, mode in [('未知', '全部分解'), ('普通', '其它')]:
            with self.assertRaises(ValueError):
                planned_count(Approval('普通', 2, rarity), mode)

class FakeIO:
    def __init__(self, counts, mismatch=False, lose_focus=False):
        self.counts = iter(counts)
        self.clicks = 0
        self.mismatch = mismatch
        self.lose_focus = lose_focus
    def check(self):
        if self.lose_focus:
            raise StopRun('focus lost')
    def verify(self, expected):
        self.check()
        if self.mismatch or next(self.counts) != expected:
            raise StopRun('identity/count mismatch')
    def click_disassemble(self):
        self.check()
        self.clicks += 1
    def wait_decreased(self, expected):
        self.check()
        if next(self.counts) != expected:
            raise StopRun('count did not decrease exactly once')
    def wait_final(self):
        self.check()

class ExecutionTests(unittest.TestCase):
    def test_extra_mode_leaves_two(self):
        io = FakeIO([4, 3, 3, 2])
        self.assertEqual(run_card(Approval('普通', 4, '普通'), '只分解多余的', io), 2)
        self.assertEqual(io.clicks, 2)
    def test_final_copy_only_once(self):
        io = FakeIO([1])
        self.assertEqual(run_card(Approval('普通', 1, '普通'), '全部分解', io), 1)
        self.assertEqual(io.clicks, 1)
    def test_mismatch_or_focus_blocks_click(self):
        for io in (FakeIO([2], mismatch=True), FakeIO([2], lose_focus=True)):
            with self.assertRaises(StopRun):
                run_card(Approval('普通', 2, '普通'), '全部分解', io)
            self.assertEqual(io.clicks, 0)
    def test_no_progress_never_retried(self):
        io = FakeIO([3, 3])
        with self.assertRaises(StopRun):
            run_card(Approval('普通', 3, '普通'), '全部分解', io)
        self.assertEqual(io.clicks, 1)
    def test_unapproved_never_clicked(self):
        io = FakeIO([])
        self.assertEqual(run_card(Approval('保留', 2, '普通'), '全部分解', io), 0)
        self.assertEqual(io.clicks, 0)

if __name__ == '__main__':
    unittest.main()

