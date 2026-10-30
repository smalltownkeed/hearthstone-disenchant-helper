"""Rules and one-click-at-a-time execution; no desktop dependencies."""
from dataclasses import dataclass
import re

MODES = ('只分解多余的', '全部分解')
RARITIES = ('普通', '稀有', '史诗', '传说')

class StopRun(RuntimeError):
    pass

@dataclass(frozen=True)
class Approval:
    finish: str
    count: int | None
    rarity: str | None

def planned_count(approval: Approval, mode: str) -> int:
    if mode not in MODES:
        raise ValueError('未知模式')
    if approval.finish not in ('普通', '金色'):
        return 0
    n = approval.count
    if type(n) is not int or not 1 <= n <= 999:
        raise ValueError('数量未知或无效；请重新扫描')
    if approval.rarity not in RARITIES:
        raise ValueError('稀有度未知；不能执行')
    keep = 0 if mode == '全部分解' else (1 if approval.rarity == '传说' else 2)
    return max(0, n - keep)

def parse_count(text: str, confidence: float) -> int | None:
    if confidence < .93:
        return None
    text = re.sub(r'\s+', '', text)
    match = re.fullmatch(r'[xX×](\d{1,3})', text)
    if not match:
        return None
    value = int(match[1])
    return value if 1 <= value <= 999 else None

def run_card(approval: Approval, mode: str, io) -> int:
    total = planned_count(approval, mode)
    for index in range(total):
        remaining = approval.count - index
        io.check()
        io.verify(remaining)
        io.check()
        io.click_disassemble()
        if remaining == 1:
            # Never retry the last-copy click, even when acknowledgement is absent.
            io.wait_final()
        else:
            io.wait_decreased(remaining - 1)
    return total


CRAFT_COSTS = {'普通': (40, 400), '稀有': (100, 800), '史诗': (400, 1600), '传说': (1600, 3200)}

def finish_from_craft_cost(rarity, cost):
    if type(cost) is not int or rarity not in CRAFT_COSTS:
        return None
    normal, golden = CRAFT_COSTS[rarity]
    return '普通' if cost == normal else ('金色' if cost == golden else None)

def auto_count(card, mode):
    if not card.available or card.finish not in ('普通', '金色'):
        return 0
    try:
        return planned_count(Approval(card.finish, card.count, card.rarity), mode)
    except ValueError:
        return 0
