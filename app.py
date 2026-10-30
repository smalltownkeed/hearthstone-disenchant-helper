"""Two-step automatic selection UI: scan profession, then process selected cards."""
from pathlib import Path
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk,messagebox
from PIL import ImageTk
from core import Approval,MODES,auto_count,StopRun
from desktop import Desktop,dpi_awareness
from vision import Vision,CLASS_X
from workflow import Engine,card_image

ROOT=Path(__file__).resolve().parent

class App:
    def __init__(self,root):
        self.root=root
        root.title('炉石分解助手 · 连续扫描版')
        root.geometry('1220x920');root.minsize(1120,850)
        self.messages=queue.Queue();self.stop=threading.Event()
        self.busy=False;self.cards=[];self.excluded=set();self.binding=None
        self.vision=None;self.photo=None
        self.profession=tk.StringVar(value='死亡骑士')
        self.mode=tk.StringVar(value=MODES[0])
        self.summary=tk.StringVar(value='尚未扫描')
        self.status=tk.StringVar(value='打开游戏收藏页后点击“扫描整个职业”。F8停止。')
        outer=ttk.Frame(root,padding=14);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='炉石收藏分解助手',font=('Microsoft YaHei UI',18,'bold')).pack(anchor='w')
        ttk.Label(outer,text='扫完所有页 → 自动选好 → 一次确认后分解。异画、钻石和无法确认的版本保留。',
                  foreground='#8a4420').pack(anchor='w',pady=(5,12))
        bar=ttk.Frame(outer);bar.pack(fill='x')
        ttk.Label(bar,text='职业').pack(side='left')
        self.class_box=ttk.Combobox(bar,textvariable=self.profession,values=[c for c in CLASS_X if c != '中立'],width=12,state='readonly')
        self.class_box.pack(side='left',padx=(5,15))
        ttk.Label(bar,text='模式').pack(side='left')
        self.mode_box=ttk.Combobox(bar,textvariable=self.mode,values=MODES,width=17,state='readonly')
        self.mode_box.pack(side='left',padx=5)
        self.scan_button=ttk.Button(bar,text='1. 扫描整个职业',command=self.start_scan)
        self.scan_button.pack(side='left',padx=15)
        ttk.Button(bar,text='停止（F8）',command=self.stop.set).pack(side='right')
        ttk.Label(outer,text='多余模式：当前版本传说留1张，其他留2张。模式可在扫描后切换，无需重扫。').pack(anchor='w',pady=8)
        body=ttk.Frame(outer);body.pack(fill='both',expand=True)
        left=ttk.Frame(body);left.pack(side='left',fill='both',padx=(0,12))
        self.tree=ttk.Treeview(left,columns=('page','finish','owned','plan'),show='tree headings',height=18)
        for key,label,width in (('#0','卡牌 / 选择',190),('page','页',38),('finish','版本',45),
                                ('owned','拥有',40),('plan','分解',40)):
            self.tree.heading(key,text=label);self.tree.column(key,width=width,stretch=key=='#0')
        scroll=ttk.Scrollbar(left,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.tree.bind('<<TreeviewSelect>>',self.select_card)
        self.tree.bind('<Double-1>',lambda e:self.toggle_selected())
        right=ttk.Frame(body);right.pack(side='left',fill='both',expand=True)
        self.preview=ttk.Label(right,text='符合规则的卡牌会自动勾选，不需要逐张设置。',anchor='center')
        self.preview.pack(fill='both',expand=True)
        self.info=ttk.Label(right,text='双击左侧卡牌可取消 / 恢复选择',wraplength=690)
        self.info.pack(anchor='w',pady=8)
        self.toggle_button=ttk.Button(right,text='保留这张 / 恢复自动选择',command=self.toggle_selected)
        self.toggle_button.pack(anchor='w')
        ttk.Separator(outer).pack(fill='x',pady=12)
        ttk.Label(outer,textvariable=self.summary,font=('Microsoft YaHei UI',11,'bold')).pack(anchor='w')
        actions=ttk.Frame(outer);actions.pack(fill='x',pady=10)
        self.run_button=ttk.Button(actions,text='2. 开始分解已选卡牌',command=lambda:self.start_execute(False))
        self.run_button.pack(side='left')
        self.verify_button=ttk.Button(actions,text='仅检查（不分解）',command=lambda:self.start_execute(True))
        self.verify_button.pack(side='left',padx=12)
        ttk.Label(actions,text='套牌同名卡不足提示会自动确认；其他未知弹窗暂停。').pack(side='left')
        ttk.Label(outer,textvariable=self.status,wraplength=1170).pack(fill='x')
        self.class_box.bind('<<ComboboxSelected>>',lambda e:self.clear_review())
        self.mode_box.bind('<<ComboboxSelected>>',lambda e:self.render())
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.poll)

    def clear_review(self):
        self.cards=[];self.excluded=set();self.binding=None;self.photo=None
        self.tree.delete(*self.tree.get_children())
        self.preview.configure(image='',text='请选择职业，然后扫描整个职业')
        self.info.configure(text='未选择卡牌')
        self.summary.set('尚未扫描')

    def reviewed(self):
        return [(c,Approval(c.finish,c.count,c.rarity)) for i,c in enumerate(self.cards)
                if i not in self.excluded and auto_count(c,self.mode.get())>0]

    def render(self):
        selected=self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        total=0;chosen=0
        for i,c in enumerate(self.cards):
            n=auto_count(c,self.mode.get()) if i not in self.excluded else 0
            mark='☑' if n else '☐'
            self.tree.insert('', 'end',iid=str(i),text=f'{mark} {c.name}',
                             values=(c.page,c.finish or '保留',c.count or '?',n))
            total+=n;chosen+=bool(n)
        pages=len(set(c.page for c in self.cards))
        self.summary.set(f'扫描 {pages} 页 · {len(self.cards)} 个版本；已自动选择 {chosen} 个版本，共 {total} 张。')
        self.run_button.configure(text=f'2. 开始分解（{total} 张）')
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])

    def select_card(self,event=None):
        selected=self.tree.selection()
        if not selected or self.busy:return
        c=self.cards[int(selected[0])]
        im=card_image(c).crop((727,80,1743,820))
        im.thumbnail((700,450))
        self.photo=ImageTk.PhotoImage(im)
        self.preview.configure(image=self.photo,text='')
        reason=c.reason or ('按所选模式处理' if auto_count(c,self.mode.get()) else '当前模式没有多余副本')
        self.info.configure(text=f'{c.name} · 第{c.page}页 · {c.finish or "无法确认版本"} · 拥有{c.count or "?"}张\n{reason}')

    def toggle_selected(self):
        selected=self.tree.selection()
        if not selected or self.busy:return
        index=int(selected[0]);c=self.cards[index]
        if auto_count(c,self.mode.get())<=0:
            self.status.set('这张卡没有符合规则的副本，或属于受保护 / 无法确认的版本。')
            return
        if index in self.excluded:self.excluded.remove(index)
        else:self.excluded.add(index)
        self.render()

    def set_busy(self,value):
        self.busy=value
        self.class_box.configure(state='disabled' if value else 'readonly')
        self.mode_box.configure(state='disabled' if value else 'readonly')
        for w in (self.scan_button,self.run_button,self.verify_button,self.toggle_button):
            w.configure(state='disabled' if value else 'normal')

    def log(self,text):
        self.messages.put(('status',text))
        with (ROOT/'session.log').open('a',encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ')+text+'\n')

    def launch(self,kind,data=None):
        if self.busy:return
        profession,mode=self.profession.get(),self.mode.get()
        binding=self.binding
        self.stop.clear();self.set_busy(True)
        self.status.set('开始前有8秒切回游戏；助手已最小化。')
        self.root.iconify()
        def worker():
            try:
                if self.vision is None:
                    self.log('加载本地识别组件（无需联网）')
                    self.vision=Vision()
                for second in range(8,0,-1):
                    self.log(f'{second}秒后开始，请切回游戏收藏页；F8停止')
                    if self.stop.wait(1):raise StopRun('已取消')
                d=Desktop(self.stop)
                if kind!='scan' and binding!=(d.hwnd,d.rect):
                    raise StopRun('游戏窗口与扫描时不同，请重新扫描')
                e=Engine(d,self.vision,profession,self.log)
                if kind=='scan':
                    cards=e.scan()
                    self.messages.put(('scanned',(cards,(d.hwnd,d.rect))))
                elif kind=='verify':
                    e.verify_all(data)
                    self.messages.put(('done','所选卡牌核验通过，没有分解。'))
                else:
                    n=e.execute(data,mode)
                    self.messages.put(('consumed',f'处理完成：分解{n}张。'))
            except Exception as exc:
                if not isinstance(exc,(StopRun,ValueError)):self.log(traceback.format_exc())
                self.log('已停止：'+str(exc))
                self.messages.put(('error',str(exc)))
            finally:self.messages.put(('idle',None))
        threading.Thread(target=worker,daemon=True).start()

    def start_scan(self):
        self.clear_review();self.launch('scan')

    def start_execute(self,dry):
        if self.busy:return
        selected=self.reviewed()
        if not selected or self.binding is None:
            messagebox.showinfo('没有待处理卡牌','先扫描整个职业；符合规则的卡牌会自动选中。')
            return
        if not dry:
            total=sum(auto_count(c,self.mode.get()) for c,a in selected)
            if not messagebox.askyesno('确认本次分解',
                f'职业：{self.profession.get()}\n模式：{self.mode.get()}\n共{total}张、{len(selected)}个版本。\n\n'
                '异画、钻石和无法确认版本保留。\n套牌同名卡不足提示将自动确认。\n分解不能撤销。\n\n开始吗？'):
                return
        self.launch('verify' if dry else 'execute',selected)

    def poll(self):
        if self.busy:
            try:
                import ctypes
                if ctypes.windll.user32.GetAsyncKeyState(0x77)&0x8000:self.stop.set()
            except AttributeError:pass
        while True:
            try:kind,data=self.messages.get_nowait()
            except queue.Empty:break
            if kind=='status':self.status.set(data)
            elif kind=='scanned':
                self.cards,self.binding=data;self.excluded=set()
                self.render()
                self.status.set('扫描完成，符合规则的已全部选好；可直接点击“开始分解”。')
                self.root.deiconify();self.root.lift()
                if self.cards:self.tree.selection_set('0')
            elif kind in ('done','consumed','error'):
                if kind in ('consumed','error'):self.clear_review()
                self.status.set(data);self.root.deiconify();self.root.lift();self.root.bell()
            elif kind=='idle':self.set_busy(False);self.select_card()
        self.root.after(100,self.poll)

    def close(self):
        self.stop.set()
        if self.busy:self.status.set('已请求停止，正在结束当前识别。');return
        self.root.destroy()

def main():
    dpi_awareness()
    root=tk.Tk();ttk.Style().theme_use('clam')
    App(root);root.mainloop()

if __name__=='__main__':main()

