"""Continuous, bounded collection scan and guarded batch processing."""
from dataclasses import dataclass
from pathlib import Path
import time
from PIL import Image
from core import Approval, StopRun, run_card, auto_count
from vision import CLASS_X, SLOTS, same_variant, similar

@dataclass
class Card:
    image: object
    name: str
    count: int | None
    rarity: str | None
    available: bool
    slot: int
    finish: str | None = None
    page: int = 0
    reason: str = ''

def card_image(card):
    if isinstance(card.image, (str, Path)):
        with Image.open(card.image) as im:
            return im.convert('RGB')
    return card.image

class Engine:
    def __init__(self, desktop, vision, profession, log=lambda text: None):
        self.d, self.v, self.profession, self.log = desktop, vision, profession, log
        self.scan_dir = None

    def collection(self):
        im=self.d.capture()
        if not self.v.class_matches(im,self.profession):
            raise StopRun('收藏页或所选职业无法确认')
        return im

    def state(self):
        im=self.d.capture()
        if not self.v.is_collection(im):
            raise StopRun('当前不是收藏页，已停止')
        profession=self.v.current_class(im)
        page=self.v.page_number(im)
        if profession is None or page is None:
            raise StopRun('无法读出职业或页码，已停止')
        return im,profession,page

    def select_class(self):
        if not self.v.is_collection(self.d.capture()):
            raise StopRun('请先关闭详情或弹窗，回到收藏页')
        self.d.click(CLASS_X[self.profession],42)
        self.d.sleep(.8)
        return self.collection()

    def step_page(self, delta):
        before=self.state()
        self.log(f'翻页检查：当前{before[2]}页，方向{delta:+d}')
        self.d.scroll(120 if delta<0 else -120)
        after=self.state()
        self.log(f'翻页结果：{after[2]}页')
        if after[2]==before[2]:
            # One bounded retry for a dropped wheel event, never a click retry.
            self.d.sleep(.3)
            self.d.scroll(120 if delta<0 else -120)
            after=self.state()
            if after[2]==before[2]:
                return None
        if after[2]!=before[2]+delta:
            raise StopRun('翻页没有恰好移动一页，已停止以免漏扫')
        return after

    def rewind_class(self):
        for _ in range(200):
            _,profession,page=self.state()
            if profession!=self.profession:
                raise StopRun('回到首页时职业发生变化')
            if page==1:
                return page
            previous=self.step_page(-1)
            if previous is None:
                raise StopRun('无法确认职业首页；游戏没有响应翻页')
            if previous[1]!=self.profession:
                restored=self.step_page(1)
                if restored is None or restored[1]!=self.profession:
                    raise StopRun('无法返回所选职业首页')
                return restored[2]
        raise StopRun('查找首页超过200页，已停止')

    def goto_page(self,target):
        for _ in range(200):
            _,profession,page=self.state()
            if profession!=self.profession:
                raise StopRun('执行时职业发生变化，请重新扫描')
            if page==target:
                return
            if self.step_page(1 if target>page else -1) is None:
                raise StopRun('无法到达已扫描的页码，请重新扫描')
        raise StopRun('定位页码超限')

    def close_detail(self):
        if not self.v.is_detail(self.d.capture()):
            raise StopRun('详情画面异常，不关闭未知弹窗')
        self.d.click(1870,700)
        self.d.sleep(.35)
        self.collection()

    def open_slot(self,index):
        self.collection()
        self.d.click(*SLOTS[index],right=True)
        self.d.sleep(.55)
        im=self.d.capture()
        if self.v.is_detail(im) and not self.v.warning_frame(im):
            return im
        if self.v.class_matches(im,self.profession):
            return None
        raise StopRun('打开卡牌后出现未知画面')

    def scan_page(self,page):
        cards=[]
        for index in range(8):
            self.log(f'扫描第{page}页 · {index+1}/8（只扫描，不分解）')
            im=self.open_slot(index)
            if im is None:
                continue
            count=self.v.count(im)
            rarity=self.v.rarity(im)
            name=self.v.name(im)
            available=self.v.button_ready(im)
            finish=self.v.auto_finish(im,rarity) if available else None
            reason='' if finish else '保留：不可分解、特殊版本或无法确认'
            if available and finish:
                self.d.sleep(.15)
                again=self.d.capture()
                if not same_variant(im,again) or self.v.count(again)!=count:
                    available=False
                    reason='保留：画面不稳定'
            if self.scan_dir is None:
                self.scan_dir=Path(__file__).resolve().parent/'scans'/str(time.time_ns())
                self.scan_dir.mkdir(parents=True,exist_ok=True)
            path=self.scan_dir/f'{page:04d}-{index}.png'
            im.save(path)
            cards.append(Card(path,name,count,rarity,available,index,finish,page,reason))
            self.close_detail()
        return cards

    def scan(self):
        self.select_class()
        first=self.rewind_class()
        self.log(f'从第{first}页开始扫描整个{self.profession}')
        cards=[]
        seen=set()
        for _ in range(200):
            _,profession,page=self.state()
            if profession!=self.profession or page in seen:
                raise StopRun('职业边界或重复页异常')
            seen.add(page)
            cards.extend(self.scan_page(page))
            next_state=self.step_page(1)
            if next_state is None:
                raise StopRun('无法确认下一页或职业边界，扫描已停止；不会把未翻页误认为完成')
            if next_state[1]!=self.profession:
                restored=self.step_page(-1)
                if restored is None or restored[1]!=self.profession:
                    raise StopRun('扫描结束后无法返回原职业')
                self.log(f'{self.profession}扫描完成，共{len(seen)}页、{len(cards)}个版本')
                return cards
        raise StopRun('扫描超过200页，已停止')

    def locate(self,card):
        self.goto_page(card.page)
        expected=card_image(card)
        for index in [card.slot]+[i for i in range(8) if i!=card.slot]:
            im=self.open_slot(index)
            if im is None:
                continue
            if same_variant(expected,im):
                return
            self.close_detail()
        raise StopRun(f'找不到相同版本：{card.name}，请重新扫描')

    def verify_all(self,reviewed):
        for card,approval in sorted(reviewed,key=lambda x:(x[0].page,x[0].slot),reverse=True):
            self.locate(card)
            CardIO(self,card).verify(approval.count)
            self.close_detail()

    def execute(self,reviewed,mode):
        total=0
        ordered=sorted(reviewed,key=lambda x:(x[0].page,x[0].slot),reverse=True)
        self.collection()
        for item,(card,approval) in enumerate(ordered):
            self.locate(card)
            total+=run_card(approval,mode,CardIO(self,card))
            im=self.d.capture()
            if self.v.is_detail(im):
                self.close_detail()
            elif item<len(ordered)-1:
                self.collection()
            self.log(f'{card.name}已处理；累计分解{total}张')
        return total

class CardIO:
    def __init__(self,engine,card):
        self.e,self.card=engine,card
        self.expected=None
        self.reference=card_image(card)

    def check(self):
        self.e.d.check()

    def snapshot(self,count):
        im=self.e.d.capture()
        if (not self.e.v.is_detail(im) or not same_variant(self.reference,im)
            or not self.e.v.button_ready(im) or self.e.v.rarity(im)!=self.card.rarity
            or self.e.v.count(im)!=count
            or self.e.v.auto_finish(im,self.card.rarity)!=self.card.finish):
            raise StopRun(f'{self.card.name}的版本、数量或可处理状态发生变化')
        return im

    def verify(self,expected):
        self.snapshot(expected)
        self.e.d.sleep(.15)
        self.snapshot(expected)
        self.expected=expected

    def click_disassemble(self):
        self.snapshot(self.expected)
        self.e.d.click(850,972)
        self.e.log(f'点击分解：{self.card.name}（此前{self.expected}张）')

    def settle(self):
        self.e.d.sleep(.65)
        im=self.e.d.capture()
        if self.e.v.deck_warning(im):
            visible=(843,185,1110,380)
            if (similar(self.reference.crop(visible),im.crop(visible))<.95
                or self.e.v.count(im)!=self.expected):
                raise StopRun('套牌提示背后的卡牌或数量无法确认')
            self.check()
            self.e.d.click(892,694)
            self.e.log('已自动确认：套牌同名卡数量不足提示')
            self.e.d.sleep(1.5)
            if self.e.v.warning_frame(self.e.d.capture()):
                raise StopRun('确认后提示没有消失，不重复点击')
        else:
            self.e.d.sleep(1.2)

    def wait_decreased(self,expected):
        self.settle()
        self.snapshot(expected)
        self.e.d.sleep(.2)
        self.snapshot(expected)

    def wait_final(self):
        self.settle()
        im=self.e.d.capture()
        if self.e.v.is_collection(im):
            return
        if (self.e.v.is_detail(im) and not self.e.v.warning_frame(im)
            and same_variant(self.reference,im) and not self.e.v.button_ready(im)):
            return
        raise StopRun('最后一张已点击，结果无法确认；不会重复分解')

