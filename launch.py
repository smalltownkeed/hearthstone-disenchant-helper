"""Offline launcher for this computer (Windows x64 Python 3.13)."""
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent

def run():
    if os.name != 'nt' or sys.version_info[:2] != (3, 13) or sys.maxsize <= 2**32:
        raise RuntimeError('此离线版需要 Windows 64位 Python 3.13。')
    runtime = ROOT / 'runtime'
    if not (runtime / 'rapidocr' / '__init__.py').is_file():
        raise RuntimeError('缺少runtime文件夹。请解压整个离线包，再运行Start.bat。')
    sys.path.insert(0, str(runtime))
    import PIL
    import numpy
    import rapidocr
    import onnxruntime
    import app
    if '--check' in sys.argv:
        print('OFFLINE IMPORTS OK', sys.version.split()[0], PIL.__version__, numpy.__version__, onnxruntime.__version__)
        return 0
    if '--test' in sys.argv:
        import unittest
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    app.main()
    return 0

if __name__ == '__main__':
    try:
        result = run()
    except Exception as exc:
        (ROOT / 'startup-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        if '--check' in sys.argv or '--test' in sys.argv:
            print(str(exc), file=sys.stderr)
        else:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror('炉石助手启动失败', str(exc) + '\n详细错误已保存到startup-error.log。')
                root.destroy()
            except Exception:
                pass
        result = 1
    sys.exit(result)

