"""Conservative screenshot matching. Coordinates are based on the supplied layout."""
from pathlib import Path
import re
import numpy as np
from PIL import Image, ImageFilter
from core import parse_count, RARITIES, finish_from_craft_cost

SIZE = (2048, 1152)
ASSETS = Path(__file__).resolve().parent / 'assets'
CLASS_X = dict(zip(('死亡骑士', '恶魔猎手', '德鲁伊', '猎人', '法师', '圣骑士',
                    '牧师', '潜行者', '萨满祭司', '术士', '战士', '中立'),
                   (315, 389, 463, 536, 609, 682, 755, 828, 901, 974, 1047, 1120)))
SLOTS = [(x, y) for y in (350, 755) for x in (435, 691, 949, 1208)]
COUNT = (914, 715, 1050, 793)
RARITY = (1408, 575, 1602, 608)
NAME = (795, 390, 1162, 462)
BUTTON = (775, 932, 929, 1008)

def normalize(image):
    w, h = image.size
    if w < 1280 or h < 700 or abs(w / h - 16 / 9) > .025:
        raise ValueError('需要至少1280×720、接近16:9的完整游戏窗口；不支持黑边布局')
    return image.convert('RGB').resize(SIZE, Image.Resampling.LANCZOS)

def similar(a, b):
    a = np.asarray(a.convert('RGB').resize((100, 60)), dtype=np.float32)
    b = np.asarray(b.convert('RGB').resize((100, 60)), dtype=np.float32)
    if a.std() < 2 or b.std() < 2:
        return 0.0
    error = float(np.mean(np.abs(a-b)))
    ac, bc = a - a.mean(), b - b.mean()
    corr = float(np.sum(ac*bc) / max(1., np.linalg.norm(ac)*np.linalg.norm(bc)))
    return min(corr, max(0., 1. - error / 128.))

def anchor_match(image, reference, box, threshold=.94):
    # UI anchors tolerate capture scaling/antialiasing, not arbitrary relocation.
    target = reference.crop(box).filter(ImageFilter.GaussianBlur(1.2))
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            shifted = (box[0]+dx, box[1]+dy, box[2]+dx, box[3]+dy)
            sample = image.crop(shifted).filter(ImageFilter.GaussianBlur(1.2))
            if similar(sample, target) >= threshold:
                return True
    return False

def same_variant(a, b):
    # Name + illustration + both frames: same-name special finishes cannot
    # qualify solely by matching their name. Animated art may fail closed.
    crops = (NAME, (843, 185, 1110, 380),
             (1118, 210, 1170, 680), (777, 285, 821, 390))
    return all(similar(a.crop(box), b.crop(box)) >= .95 for box in crops)

class Vision:
    def __init__(self, load_ocr=True):
        self.collection = Image.open(ASSETS / 'collection.png').convert('RGB')
        self.detail = Image.open(ASSETS / 'detail.png').convert('RGB')
        self.warning = Image.open(ASSETS / 'deck-warning.png').convert('RGB')
        self.ocr = None
        if load_ocr:
            from rapidocr import RapidOCR
            self.ocr = RapidOCR()

    def is_collection(self, im):
        return all(anchor_match(im, self.collection, box)
                   for box in ((1235, 1034, 1392, 1081), (1459, 8, 1712, 56)))

    def is_detail(self, im):
        return anchor_match(im, self.detail, (1278, 310, 1728, 353))

    def button_ready(self, im):
        if not self.is_detail(im) or self.warning_frame(im):
            return False
        if not anchor_match(im, self.detail, BUTTON, .9):
            return False
        rgb = np.asarray(im.crop((790, 1041, 826, 1059)), dtype=float).mean(axis=(0, 1))
        return bool(rgb[1] > rgb[0]*1.15 and rgb[1] > rgb[2]*1.1 and rgb[1] > 35)

    def read(self, image, box, single=False):
        if self.ocr is None:
            raise RuntimeError('OCR未初始化')
        crop = image.crop(box).resize(((box[2]-box[0])*2, (box[3]-box[1])*2))
        result = self.ocr(np.asarray(crop)[:, :, ::-1].copy(), use_det=not single, use_cls=False, use_rec=True)
        if result.txts is None or result.scores is None:
            return []
        return [(str(t), float(s)) for t, s in zip(result.txts, result.scores)]

    def count(self, im):
        parts = self.read(im, COUNT)
        if len(parts) != 1:
            return None
        return parse_count(*parts[0])

    def rarity(self, im):
        parts = self.read(im, RARITY, single=True)
        hits = [re.sub(r'\s+', '', t) for t, score in parts if score >= .93]
        hits = [t for t in hits if t in RARITIES]
        return hits[0] if len(hits) == 1 else None

    def name(self, im):
        return ''.join(t for t, s in self.read(im, NAME, single=True) if s >= .8) or '未识别名称'

    def class_matches(self, im, selected):
        if not self.is_collection(im):
            return False
        parts = self.read(im, (674, 104, 965, 156))
        return any(re.sub(r'\s+', '', t) == selected and s >= .9 for t, s in parts)



    def current_class(self, im):
        if not self.is_collection(im):
            return None
        for t, score in self.read(im, (674, 104, 965, 156)):
            t = re.sub(r'\s+', '', t)
            if score >= .90 and t in CLASS_X:
                return t
        return None

    def page_number(self, im):
        if not self.is_collection(im):
            return None
        parts = self.read(im, (755, 963, 872, 998), single=True)
        if len(parts) != 1 or parts[0][1] < .9:
            return None
        text = re.sub(r'\s+', '', parts[0][0])
        m = re.fullmatch(r'第?(\d{1,4})页', text)
        return int(m[1]) if m and int(m[1]) > 0 else None

    def warning_frame(self, im):
        return all(anchor_match(im, self.warning, b, .94) for b in
                   ((920, 433, 1110, 480), (795, 674, 998, 714), (1043, 674, 1245, 714)))

    def deck_warning(self, im):
        if not self.warning_frame(im):
            return False
        parts = self.read(im, (775, 517, 1380, 584))
        text = ''.join(t for t, score in parts if score >= .93)
        text = re.sub(r'[\s，。！？、,.!?]', '', text)
        return ('将该牌分解后' in text and
                '你将没有足够的同名卡牌加入你的套牌' in text)

    def craft_cost(self, im):
        if not self.is_detail(im) or self.warning_frame(im):
            return None
        if not anchor_match(im, self.detail, (1025, 932, 1178, 1008), .90):
            return None
        parts = self.read(im, (1045, 1028, 1140, 1075), single=True)
        if len(parts) != 1 or parts[0][1] < .93:
            return None
        t = re.sub(r'\s+', '', parts[0][0]).replace('−','-').replace('—','-')
        m = re.fullmatch(r'-(\d{2,4})', t)
        return int(m[1]) if m else None

    def auto_finish(self, im, rarity=None):
        # Special finishes have no ordinary crafting price/control. Unknown stays kept.
        if not self.button_ready(im):
            return None
        return finish_from_craft_cost(rarity or self.rarity(im), self.craft_cost(im))
