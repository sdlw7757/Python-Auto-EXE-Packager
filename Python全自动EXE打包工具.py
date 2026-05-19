# -*- coding: utf-8 -*-
import os
import re
import sys
import shutil
import threading
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, scrolledtext, messagebox
import pkgutil

# ---------- 内置/标准库模块列表 ----------
BUILTIN_MODULES = set(sys.builtin_module_names)
STDLIB_MODULES = set([
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
    'dis', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
    'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'fractions', 'ftplib', 'functools',
    'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib', 'gzip', 'hashlib',
    'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp', 'importlib',
    'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword', 'linecache',
    'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
    'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing', 'netrc', 'nis',
    'nntplib', 'nt', 'ntpath', 'nturl2path', 'numbers', 'operator', 'optparse',
    'os', 'ossaudiodev', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes',
    'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint',
    'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue',
    'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
    'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
    'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
    'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
    'struct', 'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog',
    'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'textwrap',
    'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace',
    'traceback', 'tracemalloc', 'tty', 'turtle', 'types', 'typing', 'unicodedata',
    'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref',
    'webbrowser', 'winreg', 'winsound', 'xml', 'xmlrpc', 'zipapp', 'zipfile',
    'zipimport', 'zlib'
])
BUILTIN_OR_STDLIB = BUILTIN_MODULES.union(STDLIB_MODULES)

# ---------- 拖拽支持 ----------
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "tkinterdnd2", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        from tkinterdnd2 import TkinterDnD, DND_FILES
        HAS_DND = True
    except:
        HAS_DND = False
        print("警告：未安装 tkinterdnd2，拖拽功能不可用。请手动执行：pip install tkinterdnd2")

class AutoPackGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python全自动EXE打包工具")
        self.root.geometry("920x750")
        self.root.resizable(False, False)
        self.center_window()
        self.root.configure(bg="#f5f7fa")

        # 变量
        self.target_path = tk.StringVar()
        self.icon_path = tk.StringVar()
        self.use_venv = tk.BooleanVar(value=True)
        self.single_file = tk.BooleanVar(value=True)
        self.hide_console = tk.BooleanVar(value=True)   # 默认隐藏
        self.fix_encode = tk.BooleanVar(value=True)
        self.clean_cache_flag = tk.BooleanVar(value=True)
        self.del_venv_after = tk.BooleanVar(value=True)
        self.uninstall_dep_after = tk.BooleanVar(value=False)
        self.new_install_libs = []
        self.venv_folder = "temp_pack_venv"

        self.create_ui()
        self.setup_drag_drop()

    def center_window(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 920) // 2
        y = (sh - 750) // 2
        self.root.geometry(f"920x750+{x}+{y}")

    def setup_drag_drop(self):
        if not HAS_DND:
            self.log("拖拽功能未启用，请使用按钮选择文件")
            return
        self.target_entry.drop_target_register(DND_FILES)
        self.target_entry.dnd_bind('<<Drop>>', self.on_drop_file)
        self.icon_entry.drop_target_register(DND_FILES)
        self.icon_entry.dnd_bind('<<Drop>>', self.on_drop_icon)

    def on_drop_file(self, event):
        path = event.data.strip('{}').strip()
        if ' ' in path and not os.path.exists(path):
            path = path.split()[0]
        if path.lower().endswith('.py') and os.path.isfile(path):
            self.target_path.set(path)
            self.log(f"已拖拽主文件：{path}")
        else:
            messagebox.showwarning("提示", "仅支持拖拽 .py 主程序文件")

    def on_drop_icon(self, event):
        path = event.data.strip('{}').strip()
        if ' ' in path and not os.path.exists(path):
            path = path.split()[0]
        if path.lower().endswith('.ico') and os.path.isfile(path):
            self.icon_path.set(path)
            self.log(f"已拖拽图标文件：{path}")
        else:
            messagebox.showwarning("提示", "仅支持拖拽 .ico 图标文件")

    def create_ui(self):
        main_frame = tk.Frame(self.root, bg="#f5f7fa")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_frame = tk.Frame(main_frame, bg="#f5f7fa")
        title_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(title_frame, text="Python源码一键EXE打包工具", font=("微软雅黑", 20, "bold"),
                 bg="#f5f7fa", fg="#1e293b").pack()
        tk.Label(title_frame, text="纯净虚拟环境打包｜精简体积｜自动补依赖｜进度可视化",
                 font=("微软雅黑", 11), bg="#f5f7fa", fg="#64748b").pack(pady=(5,0))

        mode_panel = tk.LabelFrame(main_frame, text="打包模式选择", font=("微软雅黑", 12, "bold"),
                                   bg="white", fg="#333", bd=1, relief=tk.SOLID)
        mode_panel.pack(fill=tk.X, pady=(0, 10))
        mode_inner = tk.Frame(mode_panel, bg="white")
        mode_inner.pack(padx=15, pady=12, anchor=tk.W)
        tk.Checkbutton(mode_inner, text="使用纯净虚拟环境打包(推荐)", variable=self.use_venv,
                       bg="white", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W)
        tk.Checkbutton(mode_inner, text="打包完成自动删除虚拟环境文件夹", variable=self.del_venv_after,
                       bg="white", font=("微软雅黑", 10)).grid(row=0, column=1, padx=(40,0), sticky=tk.W)

        file_panel = tk.LabelFrame(main_frame, text="文件配置", font=("微软雅黑", 12, "bold"),
                                   bg="white", fg="#333", bd=1, relief=tk.SOLID)
        file_panel.pack(fill=tk.X, pady=(0, 10))
        row1 = tk.Frame(file_panel, bg="white")
        row1.pack(fill=tk.X, padx=15, pady=(15, 10))
        tk.Label(row1, text="目标Python源码:", bg="white", font=("微软雅黑", 10), width=12, anchor=tk.E).pack(side=tk.LEFT)
        self.target_entry = tk.Entry(row1, textvariable=self.target_path, font=("微软雅黑", 10), relief=tk.SOLID, bd=1)
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,5))
        tk.Button(row1, text="选择文件", command=self.select_py_file, bg="#2563eb",
                  fg="white", font=("微软雅黑", 9), relief=tk.FLAT, padx=8).pack(side=tk.LEFT)

        row2 = tk.Frame(file_panel, bg="white")
        row2.pack(fill=tk.X, padx=15, pady=(0, 15))
        tk.Label(row2, text="程序图标:", bg="white", font=("微软雅黑", 10), width=12, anchor=tk.E).pack(side=tk.LEFT)
        self.icon_entry = tk.Entry(row2, textvariable=self.icon_path, font=("微软雅黑", 10), relief=tk.SOLID, bd=1)
        self.icon_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,5))
        tk.Button(row2, text="选择ICO", command=self.select_icon, bg="#2563eb",
                  fg="white", font=("微软雅黑", 9), relief=tk.FLAT, padx=8).pack(side=tk.LEFT)

        param_panel = tk.LabelFrame(main_frame, text="打包参数设置", font=("微软雅黑", 12, "bold"),
                                    bg="white", fg="#333", bd=1, relief=tk.SOLID)
        param_panel.pack(fill=tk.X, pady=(0, 10))
        param_inner = tk.Frame(param_panel, bg="white")
        param_inner.pack(padx=15, pady=12, anchor=tk.W)
        tk.Checkbutton(param_inner, text="打包为单个EXE文件", variable=self.single_file,
                       bg="white", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, padx=(0,30))
        tk.Checkbutton(param_inner, text="隐藏命令行黑窗口", variable=self.hide_console,
                       bg="white", font=("微软雅黑", 10)).grid(row=0, column=1, sticky=tk.W, padx=(0,30))
        tk.Checkbutton(param_inner, text="自动修复中文乱码", variable=self.fix_encode,
                       bg="white", font=("微软雅黑", 10)).grid(row=0, column=2, sticky=tk.W)
        tk.Checkbutton(param_inner, text="打包后清理缓存文件", variable=self.clean_cache_flag,
                       bg="white", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.W, pady=(8,0))
        tk.Checkbutton(param_inner, text="打包后卸载新增依赖库", variable=self.uninstall_dep_after,
                       bg="white", font=("微软雅黑", 10), fg="#dc2626", selectcolor="white").grid(row=1, column=1, sticky=tk.W, pady=(8,0))

        # ---------- 修改进度条面板，添加百分比显示 ----------
        progress_panel = tk.LabelFrame(main_frame, text="打包进度", font=("微软雅黑", 12, "bold"),
                                       bg="white", fg="#333", bd=1, relief=tk.SOLID)
        progress_panel.pack(fill=tk.X, pady=(0, 10))
        
        # 创建进度条容器
        progress_container = tk.Frame(progress_panel, bg="white")
        progress_container.pack(padx=15, pady=15)
        
        # 进度条
        self.progress = ttk.Progressbar(progress_container, length=800, mode="determinate")
        self.progress.pack(side=tk.LEFT)
        
        # 百分比标签
        self.progress_label = tk.Label(progress_container, text="0%", bg="white", font=("微软雅黑", 10))
        self.progress_label.pack(side=tk.LEFT, padx=(10, 0))

        btn_frame = tk.Frame(main_frame, bg="#f5f7fa")
        btn_frame.pack(pady=(5, 15))
        tk.Button(btn_frame, text="开始全自动打包", command=self.start_pack_thread,
                  bg="#10b981", fg="white", font=("微软雅黑", 12, "bold"),
                  width=18, height=1, relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="复制运行日志", command=self.copy_log,
                  bg="#f59e0b", fg="white", font=("微软雅黑", 12, "bold"),
                  width=18, height=1, relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="清空日志面板", command=self.clear_log,
                  bg="#ef4444", fg="white", font=("微软雅黑", 12, "bold"),
                  width=18, height=1, relief=tk.FLAT, padx=10, pady=5).pack(side=tk.LEFT, padx=10)

        log_panel = tk.LabelFrame(main_frame, text="运行日志", font=("微软雅黑", 12, "bold"),
                                  bg="white", fg="#333", bd=1, relief=tk.SOLID)
        log_panel.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(log_panel, font=("Consolas", 10), wrap=tk.WORD,
                                                  bg="white", fg="#111", relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log("工具已启动\n请选择.py文件后点击开始打包...")

    # ------------------ 辅助函数 ------------------
    def update_progress(self, v):
        """更新进度条和百分比显示"""
        self.progress["value"] = v
        # 更新百分比标签
        self.progress_label.config(text=f"{int(v)}%")
        self.root.update()

    def log(self, t):
        self.log_text.insert(tk.END, f"{t}\n")
        self.log_text.see(tk.END)
        self.root.update()

    def copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get(1.0, tk.END))
        messagebox.showinfo("提示", "日志已复制到剪贴板")

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.update_progress(0)  # 重置进度条和百分比
        self.log("日志已清空")

    def select_py_file(self):
        p = filedialog.askopenfilename(filetypes=[("Python文件", "*.py"), ("所有文件", "*.*")])
        if p:
            self.target_path.set(p)

    def select_icon(self):
        p = filedialog.askopenfilename(filetypes=[("图标文件", "*.ico"), ("所有文件", "*.*")])
        if p:
            self.icon_path.set(p)

    # ------------------ 修正后的扫描依赖 ------------------
    def scan_libs(self, fp):
        libs = set()
        pat = re.compile(r'^(import|from)\s+(\w+)')
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    m = pat.match(line.strip())
                    if m:
                        lib = m.group(2)
                        # 过滤内置/标准库
                        if lib not in BUILTIN_OR_STDLIB:
                            libs.add(lib)
        except Exception as e:
            self.log(f"扫描依赖时出错：{e}")
        return list(libs)

    # ------------------ 打包核心 ------------------
    def create_venv(self):
        if os.path.exists(self.venv_folder):
            shutil.rmtree(self.venv_folder)
        self.log(f"创建虚拟环境 {self.venv_folder}")
        subprocess.run([sys.executable, "-m", "venv", self.venv_folder],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def get_venv_py(self):
        return os.path.join(self.venv_folder, "Scripts", "python.exe")

    def install_libs(self, py, libs):
        self.new_install_libs = []
        if not libs:
            self.log("无第三方依赖需要安装")
            return
        self.log(f"检测到第三方依赖包：{libs}")
        total = len(libs)
        for i, pkg in enumerate(libs):
            self.log(f"正在安装 {pkg} ...")
            subprocess.run([py, "-m", "pip", "install", "-i",
                            "https://pypi.tuna.tsinghua.edu.cn/simple", pkg],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.update_progress(20 + int((i + 1) / total * 25))
            self.new_install_libs.append(pkg)

    def fix_code(self, path):
        with open(path, "r", encoding="utf-8") as f:
            c = f.read()
        if "# -*- coding: utf-8 -*-" not in c:
            c = "# -*- coding: utf-8 -*-\n" + c
            with open(path, "w", encoding="utf-8") as f:
                f.write(c)
            self.log("已添加 UTF-8 编码声明")

    def remove_cache(self):
        for d in ["build", "__pycache__"]:
            if os.path.exists(d):
                shutil.rmtree(d)
        spec = Path(self.target_path.get()).stem + ".spec"
        if os.path.exists(spec):
            os.remove(spec)
        self.log("已清理临时缓存文件")

    def inject_runtime(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        if "__rp(" in code:
            self.log("运行兼容代码已存在，跳过注入")
            return
        head = '''
import sys, os
__pf = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
def __rp(p):
    return os.path.join(__pf, p)
os.chdir(__pf)
'''
        new_code = head + "\n" + code
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)
        self.log("✅ 已自动注入运行兼容代码（打包后可直接运行）")

    def pack_task(self):
        self.clear_log()
        py_file = self.target_path.get().strip()
        icon_file = self.icon_path.get().strip()
        if not os.path.exists(py_file):
            messagebox.showerror("错误", "请选择有效的 .py 文件")
            return

        self.update_progress(5)
        self.log("===== 开始全自动打包（无需手动改代码） =====")
        self.log(f"主文件：{py_file}")

        venv_py = sys.executable
        if self.use_venv.get():
            self.create_venv()
            venv_py = self.get_venv_py()
            self.update_progress(15)
            self.log("正在虚拟环境中安装 PyInstaller ...")
            subprocess.run([venv_py, "-m", "pip", "install", "-i",
                            "https://pypi.tuna.tsinghua.edu.cn/simple", "pyinstaller"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.update_progress(20)

        libs = self.scan_libs(py_file)
        self.install_libs(venv_py, libs)
        self.update_progress(40)

        self.inject_runtime(py_file)
        if self.fix_encode.get():
            self.fix_code(py_file)
        self.update_progress(45)

        cmd = [venv_py, "-m", "PyInstaller"]
        if self.single_file.get():
            cmd.append("-F")
        if self.hide_console.get():
            cmd.append("-w")
            self.log("已添加 -w 参数，生成的 EXE 将无控制台窗口")
        if icon_file and os.path.exists(icon_file):
            cmd.extend(["-i", icon_file])

        folder = os.path.dirname(py_file)
        sep = ";" if sys.platform == "win32" else ":"
        cmd.extend(["--add-data", f"{folder}{sep}."])
        cmd.append(py_file)

        self.log(f"执行命令：{' '.join(cmd)}")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        step = 0
        while True:
            line = p.stdout.readline()
            if not line and p.poll() is not None:
                break
            if line:
                self.log(line.strip())
                step += 1
                if step % 12 == 0:
                    v = 45 + int(step / 70 * 50)
                    if v <= 95:
                        self.update_progress(v)

        self.update_progress(95)

        # 清理阶段
        if self.use_venv.get() and self.uninstall_dep_after.get() and self.new_install_libs:
            self.log("正在卸载本次安装的依赖库（从虚拟环境中）...")
            for lib in self.new_install_libs:
                subprocess.run([venv_py, "-m", "pip", "uninstall", "-y", lib],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log("依赖库卸载完成")
        elif not self.use_venv.get() and self.uninstall_dep_after.get():
            self.log("警告：未使用虚拟环境，忽略‘卸载依赖’选项（避免影响系统Python）")

        if self.use_venv.get() and self.del_venv_after.get() and os.path.exists(self.venv_folder):
            shutil.rmtree(self.venv_folder)
            self.log("已删除临时虚拟环境")

        if self.clean_cache_flag.get():
            self.remove_cache()

        self.update_progress(100)
        dist = os.path.abspath("dist")
        if os.path.exists(dist):
            os.startfile(dist)
            self.log("\n🎉 打包完成！生成的 EXE 位于 dist 文件夹内，直接双击即可运行！")
        else:
            self.log("\n❌ 打包失败，请检查上方日志")

    def start_pack_thread(self):
        threading.Thread(target=self.pack_task, daemon=True).start()


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = AutoPackGUI(root)
    root.mainloop()