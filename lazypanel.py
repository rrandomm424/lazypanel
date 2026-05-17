"""
LazyPanel v3 — 全局快捷键管理器
"""
import sys, os, json, ctypes, subprocess, webbrowser, threading, queue
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# ═══════════════════════════════════════════════════════════════════════════
# Win32 API
# ═══════════════════════════════════════════════════════════════════════════
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_HOTKEY    = 0x0312
MOD_ALT      = 0x0001; MOD_CONTROL = 0x0002
MOD_SHIFT    = 0x0004; MOD_WIN     = 0x0008
MOD_NOREPEAT = 0x4000

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                   wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = wintypes.LPARAM

# ═══════════════════════════════════════════════════════════════════════════
# Key data
# ═══════════════════════════════════════════════════════════════════════════
KEY_VK = {}
for i in range(10):
    KEY_VK[f"小键盘 {i}"] = 0x60 + i
KEY_VK.update({
    "小键盘 /": 0x6F, "小键盘 *": 0x6A, "小键盘 -": 0x6D,
    "小键盘 +": 0x6B, "小键盘 .": 0x6E,
})
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEY_VK[c] = ord(c)
for i in range(10):
    KEY_VK[str(i)] = 0x30 + i
KEY_VK.update({
    "↑": 0x26, "↓": 0x28, "←": 0x25, "→": 0x27,
    "Tab": 0x09, "Esc": 0x1B, "空格": 0x20, "回车": 0x0D,
    "退格": 0x08, "Delete": 0x2E, "Insert": 0x2D,
    "Home": 0x24, "End": 0x23, "PgUp": 0x21, "PgDn": 0x22,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    ",": 0xBC, ".": 0xBE, "/": 0xBF, ";": 0xBA,
    "'": 0xDE, "[": 0xDB, "]": 0xDD, "\\": 0xDC,
    "`": 0xC0, "-": 0xBD, "=": 0xBB,
})

MOD_OPTIONS = [
    ("无", 0), ("Ctrl", MOD_CONTROL), ("Alt", MOD_ALT),
    ("Shift", MOD_SHIFT), ("Win", MOD_WIN),
    ("Ctrl+Shift", MOD_CONTROL|MOD_SHIFT),
    ("Ctrl+Alt", MOD_CONTROL|MOD_ALT),
    ("Alt+Shift", MOD_ALT|MOD_SHIFT),
]
MOD_NAME = {v: n for n, v in MOD_OPTIONS}

KEY_CATEGORIES = [
    ("方向键", ["↑", "↓", "←", "→"]),
    ("小键盘", [f"小键盘 {i}" for i in range(10)] +
               ["小键盘 /", "小键盘 *", "小键盘 -", "小键盘 +", "小键盘 ."]),
    ("字母", [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]),
    ("数字", [str(i) for i in range(10)]),
    ("功能键", [f"F{i}" for i in range(1, 13)]),
    ("特殊键", ["Tab", "Esc", "空格", "回车", "退格", "Delete",
                "Insert", "Home", "End", "PgUp", "PgDn"]),
    ("符号", [",", ".", "/", ";", "'", "[", "]", "\\", "`", "-", "="]),
]

ACTION_OPTIONS = [
    ("模拟按键", "key"), ("启动程序", "launch"),
    ("打开网址", "url"), ("运行命令", "command"),
    ("媒体控制", "media"),
]

MEDIA_OPTIONS = ["volume_up", "volume_down", "volume_mute",
                 "next_track", "prev_track", "play_pause", "stop"]

MEDIA_VK = {
    "volume_up": 0xAF, "volume_down": 0xAE, "volume_mute": 0xAD,
    "next_track": 0xB0, "prev_track": 0xB1,
    "play_pause": 0xB3, "stop": 0xB2,
}

# ═══════════════════════════════════════════════════════════════════════════
# Hotkey parsing
# ═══════════════════════════════════════════════════════════════════════════
def hotkey_to_vk(hk_str: str):
    """Parse stored hotkey string back to (mod, vk)."""
    parts = [p.strip().lower() for p in hk_str.split("+") if p.strip()]
    if not parts: return None
    mod_map = {"ctrl": MOD_CONTROL, "alt": MOD_ALT,
               "shift": MOD_SHIFT, "win": MOD_WIN}
    mod = 0; key = ""
    for p in parts:
        if p in mod_map:
            mod |= mod_map[p]
        else:
            key = p; break
    if not key: return None
    # convert stored key name back to VK — try display names first, then raw
    vk = KEY_VK.get(key)
    if vk is None:
        # try the stored key name as-is
        for k, v in KEY_VK.items():
            if k.lower() == key:
                vk = v; break
    if vk is None and len(key) == 1:
        vk = ord(key.upper())
    if vk is None: return None
    return (mod | MOD_NOREPEAT, vk)

def entry_to_hotkey_str(mod_val: int, key_name: str) -> str:
    """Convert (mod, key) to storage string like 'ctrl+up'."""
    parts = []
    if mod_val & MOD_CONTROL: parts.append("ctrl")
    if mod_val & MOD_ALT:     parts.append("alt")
    if mod_val & MOD_SHIFT:   parts.append("shift")
    if mod_val & MOD_WIN:     parts.append("win")
    parts.append(key_name.lower().replace("小键盘 ", "num "))
    return "+".join(parts)

# ═══════════════════════════════════════════════════════════════════════════
# SendInput
# ═══════════════════════════════════════════════════════════════════════════
VK_SEND = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "esc": 0x1B, "tab": 0x09, "enter": 0x0D, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "home": 0x24, "end": 0x23,
    "pgup": 0x21, "pgdn": 0x22, "pageup": 0x21, "pagedown": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
}
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    VK_SEND[c] = ord(c)
    VK_SEND[c.lower()] = ord(c)
for i in range(10):
    VK_SEND[str(i)] = 0x30 + i
for i in range(1, 13):
    VK_SEND[f"f{i}"] = 0x6F + i

KEYEVENTF_KEYUP = 0x0002; KEYEVENTF_EXTENDEDKEY = 0x0001
INPUT_KEYBOARD = 1

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)]
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_void_p)]
class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]
class _IN_U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]
class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _IN_U)]

_EXT = {0x11,0x10,0x12,0x5B,0x5C,0x2E,0x2D,0x24,0x23,0x21,0x22,0x26,0x28,0x25,0x27,0x2C}

def send_key_combo(s: str):
    parts = [p.strip().lower() for p in s.split("+") if p.strip()]
    if not parts: return
    mods = []; main_vk = None
    for p in parts[:-1]:
        vk = VK_SEND.get(p)
        if vk: mods.append(vk)
    main_vk = VK_SEND.get(parts[-1])
    if main_vk is None and len(parts[-1]) == 1:
        main_vk = ord(parts[-1].upper())
    if not main_vk: return
    events = []
    for mv in mods:
        f = KEYEVENTF_EXTENDEDKEY if mv in _EXT else 0
        events.append(INPUT(INPUT_KEYBOARD, _IN_U(KEYBDINPUT(mv, 0, f, 0, None))))
    mf = KEYEVENTF_EXTENDEDKEY if main_vk in _EXT else 0
    events.append(INPUT(INPUT_KEYBOARD, _IN_U(KEYBDINPUT(main_vk, 0, mf, 0, None))))
    events.append(INPUT(INPUT_KEYBOARD, _IN_U(KEYBDINPUT(main_vk, 0, mf|KEYEVENTF_KEYUP, 0, None))))
    for mv in reversed(mods):
        f = KEYEVENTF_EXTENDEDKEY if mv in _EXT else 0
        events.append(INPUT(INPUT_KEYBOARD, _IN_U(KEYBDINPUT(mv, 0, f|KEYEVENTF_KEYUP, 0, None))))
    n = len(events)
    user32.SendInput(n, ctypes.byref((INPUT*n)(*events)), ctypes.sizeof(INPUT))

def send_media(vk: int):
    f = KEYEVENTF_EXTENDEDKEY
    d = INPUT(INPUT_KEYBOARD, _IN_U(KEYBDINPUT(vk, 0, f, 0, None)))
    u = INPUT(INPUT_KEYBOARD, _IN_U(KEYBDINPUT(vk, 0, f|KEYEVENTF_KEYUP, 0, None)))
    user32.SendInput(1, ctypes.byref(d), ctypes.sizeof(INPUT))
    user32.SendInput(1, ctypes.byref(u), ctypes.sizeof(INPUT))

def execute_action(entry):
    t = entry.get("action",""); v = entry.get("value","")
    if not t or not v: return
    try:
        if t == "key": send_key_combo(v)
        elif t == "launch": os.startfile(v)
        elif t == "url": webbrowser.open(v)
        elif t == "command":
            subprocess.run(v, shell=True, capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        elif t == "media":
            vk = MEDIA_VK.get(v)
            if vk: send_media(vk)
    except Exception as e:
        print(f"  [错误] {t}:{v} — {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 后台引擎 (消息循环线程)
# ═══════════════════════════════════════════════════════════════════════════
WNDPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)

class MSG(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt_x", wintypes.LONG), ("pt_y", wintypes.LONG)]

class HotkeyEngine:
    TOGGLE_ID = 1   # reserved hotkey ID for master toggle

    def __init__(self):
        self._hwnd = None; self._hotkey_map = {}
        self._next_id = self.TOGGLE_ID + 1; self._thread = None
        self._running = False; self._cmd_queue = queue.Queue()
        self._toggle_hotkey = "win+shift+q"
        self.on_toggle = None  # callback(parent) when master toggle is pressed

    def start(self, entries, settings):
        self._toggle_hotkey = settings.get("toggle_hotkey", "win+shift+q")
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(entries,), daemon=True)
        self._thread.start()

    def reload(self, entries, settings=None):
        if settings:
            self._toggle_hotkey = settings.get("toggle_hotkey", "win+shift+q")
        self._cmd_queue.put(("reload", entries))

    def stop(self):
        self._cmd_queue.put(("stop",))
        if self._thread: self._thread.join(timeout=2)

    def _create_window(self):
        hinst = kernel32.GetModuleHandleW(None)
        def wnd_proc(hwnd, msg, wParam, lParam):
            if msg == WM_HOTKEY:
                entry = self._hotkey_map.get(wParam)
                if entry: execute_action(entry)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
        self._wndproc_cb = WNDPROC(wnd_proc)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT), ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON)]
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_cb
        wc.hInstance = hinst
        wc.lpszClassName = "LazyPanelEngine"
        user32.RegisterClassExW(ctypes.byref(wc))
        self._hwnd = user32.CreateWindowExW(0, "LazyPanelEngine", "", 0,
                                              0,0,0,0, None, None, hinst, None)

    def _register_all(self, entries):
        for hid in list(self._hotkey_map.keys()):
            user32.UnregisterHotKey(self._hwnd, hid)
        self._hotkey_map.clear()

        # Always register master toggle hotkey (ID = TOGGLE_ID)
        result = hotkey_to_vk(self._toggle_hotkey)
        if result:
            mod, vk = result
            if user32.RegisterHotKey(self._hwnd, self.TOGGLE_ID, mod, vk):
                self._hotkey_map[self.TOGGLE_ID] = {"_toggle": True}

        for entry in entries:
            if not entry.get("enabled", True): continue
            hk_str = entry.get("hotkey", "")
            if not hk_str: continue
            result = hotkey_to_vk(hk_str)
            if result is None: continue
            mod, vk = result
            hid = self._next_id; self._next_id += 1
            if user32.RegisterHotKey(self._hwnd, hid, mod, vk):
                self._hotkey_map[hid] = entry

    def _run(self, entries):
        self._create_window()
        if not self._hwnd: return
        self._register_all(entries)

        msg = MSG()
        while self._running:
            # Process commands from GUI
            try:
                while True:
                    cmd = self._cmd_queue.get_nowait()
                    if cmd[0] == "reload": self._register_all(cmd[1])
                    elif cmd[0] == "stop": self._running = False
            except queue.Empty: pass

            # Wait for messages (50ms timeout)
            ret = user32.MsgWaitForMultipleObjects(0, None, False, 50, 0x4FF)
            if ret == 0xFFFFFFFF: break
            if ret == 0:  # message arrived
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0012:  # WM_QUIT
                        self._running = False; break
                    if msg.message == WM_HOTKEY:
                        hid = msg.wParam
                        entry = self._hotkey_map.get(hid)
                        if entry:
                            if entry.get("_toggle"):
                                # Master toggle — notify app
                                if self.on_toggle:
                                    self.on_toggle()
                            else:
                                execute_action(entry)
                    else:
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
        # cleanup
        for hid in list(self._hotkey_map.keys()):
            user32.UnregisterHotKey(self._hwnd, hid)
        self._hotkey_map.clear()
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

# ═══════════════════════════════════════════════════════════════════════════
# 配置读写
# ═══════════════════════════════════════════════════════════════════════════
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return _default_entries(), _default_settings()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("hotkeys", [])
        settings = data.get("settings", {})
        settings.setdefault("toggle_hotkey", "win+shift+q")
        if not entries:
            return _default_entries(), settings
        for e in entries:
            e.setdefault("enabled", True)
            e.setdefault("action", "key")
            e.setdefault("value", "")
        return entries, settings
    except Exception:
        return _default_entries(), _default_settings()

def save_config(entries, settings):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"hotkeys": entries, "settings": settings}, f, indent=2, ensure_ascii=False)

def _default_entries():
    return [
        {"hotkey": "ctrl+up",   "action": "key", "value": "ctrl+c", "enabled": True},
        {"hotkey": "ctrl+down", "action": "key", "value": "ctrl+v", "enabled": True},
        {"hotkey": "ctrl+left", "action": "key", "value": "ctrl+a", "enabled": True},
        {"hotkey": "ctrl+right","action": "key", "value": "ctrl+z", "enabled": True},
        {"hotkey": "num .",     "action": "key", "value": "alt+tab","enabled": True},
        {"hotkey": "alt+,",     "action": "key", "value": "tab",    "enabled": True},
    ]

def _default_settings():
    return {"toggle_hotkey": "win+shift+q"}

# ═══════════════════════════════════════════════════════════════════════════
# 热键编辑对话框 — 下拉选择，无需手动输入
# ═══════════════════════════════════════════════════════════════════════════
class HotkeyEditDialog(tk.Toplevel):
    def __init__(self, parent, entry=None, on_save=None):
        super().__init__(parent)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save

        entry = entry or {"hotkey": "ctrl+up", "action": "key", "value": "", "enabled": True}

        # Parse stored hotkey string back to mod + key_name
        hk_str = entry.get("hotkey", "")
        cur_mod = 0; cur_key = ""
        parts = [p.strip().lower() for p in hk_str.split("+") if p.strip()]
        mod_map = {"ctrl": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT, "win": MOD_WIN}
        for p in parts:
            if p in mod_map:
                cur_mod |= mod_map[p]
            else:
                cur_key = p; break
        if not cur_key and parts:
            cur_key = parts[-1] if not parts[-1] in mod_map else ""

        # Find display key name
        cur_key_display = ""
        for disp, vk in KEY_VK.items():
            if disp.lower() == cur_key:
                cur_key_display = disp; break
        if not cur_key_display and len(cur_key) == 1:
            cur_key_display = cur_key.upper()

        self.title("添加热键" if not entry.get("hotkey") else "编辑热键")
        self.configure(bg="#1a1a2e")

        frm = tk.Frame(self, bg="#1a1a2e", padx=12, pady=12)
        frm.pack()

        # ── 触发键选择 ──
        row = 0
        tk.Label(frm, text="修饰键", bg="#1a1a2e", fg="#cdd6f4",
                 font=("Microsoft YaHei", 9)).grid(row=row, column=0, sticky="w", pady=4)
        mod_names = [n for n,_ in MOD_OPTIONS]
        self.mod_var = tk.StringVar(value=MOD_NAME.get(cur_mod, "无"))
        mod_cb = ttk.Combobox(frm, textvariable=self.mod_var, values=mod_names,
                               state="readonly", width=14)
        mod_cb.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        row += 1

        tk.Label(frm, text="按键", bg="#1a1a2e", fg="#cdd6f4",
                 font=("Microsoft YaHei", 9)).grid(row=row, column=0, sticky="w", pady=4)
        # Build flat key list with category separators
        key_values = []
        for cat, keys in KEY_CATEGORIES:
            key_values.append(f"── {cat} ──")
            key_values.extend(keys)
        self.key_var = tk.StringVar(value=cur_key_display or "↑")
        key_cb = ttk.Combobox(frm, textvariable=self.key_var, values=key_values,
                               state="readonly", width=14)
        key_cb.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        # disable selection of category headers
        def _validate_key(*args):
            v = self.key_var.get()
            if v.startswith("──"):
                self.key_var.set("↑")
        self.key_var.trace_add("write", _validate_key)
        row += 1

        # Hotkey preview
        self._preview_var = tk.StringVar()
        tk.Label(frm, text="预览", bg="#1a1a2e", fg="#585b70",
                 font=("Microsoft YaHei", 8)).grid(row=row, column=0, sticky="w")
        tk.Label(frm, textvariable=self._preview_var, bg="#1a1a2e", fg="#f9e2af",
                 font=("Microsoft YaHei", 10, "bold")).grid(row=row, column=1,
                                                             sticky="w", pady=2)
        self._update_preview()
        self.mod_var.trace_add("write", lambda *a: self._update_preview())
        self.key_var.trace_add("write", lambda *a: self._update_preview())
        row += 1

        # ── 分隔 ──
        ttk.Separator(frm, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        # ── 动作 ──
        tk.Label(frm, text="动作类型", bg="#1a1a2e", fg="#cdd6f4",
                 font=("Microsoft YaHei", 9)).grid(row=row, column=0, sticky="w", pady=4)
        act_names = [n for n,_ in ACTION_OPTIONS]
        cur_act = entry.get("action", "key")
        cur_act_name = "模拟按键"
        for n,a in ACTION_OPTIONS:
            if a == cur_act: cur_act_name = n; break
        self.act_var = tk.StringVar(value=cur_act_name)
        act_cb = ttk.Combobox(frm, textvariable=self.act_var, values=act_names,
                               state="readonly", width=14)
        act_cb.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        act_cb.bind("<<ComboboxSelected>>", self._on_act_changed)
        row += 1

        tk.Label(frm, text="动作参数", bg="#1a1a2e", fg="#cdd6f4",
                 font=("Microsoft YaHei", 9)).grid(row=row, column=0, sticky="w", pady=4)
        self.val_frame = tk.Frame(frm, bg="#1a1a2e")
        self.val_frame.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        self.val_entry = ttk.Entry(self.val_frame,
                                    textvariable=tk.StringVar(value=entry.get("value","")),
                                    width=16)
        self.val_cb = ttk.Combobox(self.val_frame,
                                    textvariable=tk.StringVar(
                                        value=entry.get("value", MEDIA_OPTIONS[0])),
                                    values=MEDIA_OPTIONS, state="readonly", width=14)
        self.val_hint = tk.Label(frm, text="", bg="#1a1a2e", fg="#585b70",
                                  font=("Microsoft YaHei", 7))
        self.val_hint.grid(row=row+1, column=1, sticky="w")
        self._on_act_changed()
        row += 2

        # ── 启用 ──
        self.en_var = tk.BooleanVar(value=entry.get("enabled", True))
        ttk.Checkbutton(frm, text="启用此热键", variable=self.en_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=2)
        row += 1

        # ── 按钮 ──
        btn_frame = tk.Frame(frm, bg="#1a1a2e")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(8,0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side="left", padx=4)

        self.geometry(f"+{parent.winfo_rootx()+60}+{parent.winfo_rooty()+40}")

    def _update_preview(self):
        mod_name = self.mod_var.get()
        key_name = self.key_var.get()
        if key_name.startswith("──"):
            self._preview_var.set("—")
            return
        if mod_name == "无":
            self._preview_var.set(key_name)
        else:
            self._preview_var.set(f"{mod_name} + {key_name}")

    def _on_act_changed(self, event=None):
        self.val_entry.pack_forget()
        self.val_cb.pack_forget()
        if self.act_var.get() == "媒体控制":
            self.val_cb.pack(side="left")
            self.val_hint.config(text="")
        else:
            self.val_entry.pack(side="left")
            hints = {
                "模拟按键": "如: ctrl+c, win+d",
                "启动程序": "如: notepad.exe",
                "打开网址": "如: https://github.com",
                "运行命令": "如: shutdown /s /t 0",
            }
            self.val_hint.config(text=hints.get(self.act_var.get(), ""))

    def _save(self):
        mod_name = self.mod_var.get()
        mod_val = 0
        for n,v in MOD_OPTIONS:
            if n == mod_name: mod_val = v; break
        key_name = self.key_var.get()
        if key_name.startswith("──") or not key_name: return

        act_name = self.act_var.get()
        act_id = "key"
        for n,a in ACTION_OPTIONS:
            if n == act_name: act_id = a; break
        val = self.val_cb.get() if act_name == "媒体控制" else self.val_entry.get()

        hk_str = entry_to_hotkey_str(mod_val, key_name)

        result = {
            "hotkey": hk_str,
            "action": act_id,
            "value": val.strip(),
            "enabled": self.en_var.get(),
        }
        if self.on_save: self.on_save(result)
        self.destroy()

# ═══════════════════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════════════════
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LazyPanel")
        self.root.geometry("700x500")
        self.root.minsize(500, 340)
        self.root.configure(bg="#1a1a2e")
        try:
            icon = tk.PhotoImage(file=os.path.join(BASE_DIR, "icon.png"))
            self.root.iconphoto(True, icon)
        except Exception:
            try:
                ico_path = os.path.join(BASE_DIR, "icon.ico")
                if os.path.exists(ico_path):
                    self.root.iconbitmap(ico_path)
            except Exception:
                pass

        # Color scheme
        self.C = {
            "bg": "#1a1a2e", "bar": "#0f0f23", "card": "#16213e",
            "fg": "#cdd6f4", "accent": "#89b4fa", "dim": "#585b70",
            "on": "#a6e3a1", "off": "#f38ba8",
            "warn": "#f9e2af", "btn": "#313244",
        }

        self.entries, self.settings = load_config()
        self.engine = HotkeyEngine()
        self.engine.on_toggle = self._on_master_toggle

        self._build_ui()
        self._refresh()

        self.engine.start(self.entries, self.settings)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        C = self.C

        # ── 标题栏 ──
        bar = tk.Frame(self.root, bg=C["bar"], height=38)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="  LazyPanel", bg=C["bar"], fg=C["accent"],
                 font=("Microsoft YaHei", 11, "bold")).pack(side="left", pady=6)
        tk.Label(bar, text="快捷键管理器  ", bg=C["bar"], fg=C["dim"],
                 font=("Microsoft YaHei", 8)).pack(side="right", pady=6)

        # ── 工具栏 ──
        tb = tk.Frame(self.root, bg=C["card"], height=36)
        tb.pack(fill="x", padx=6, pady=(6,0))
        tb.pack_propagate(False)

        style_btns = [
            ("＋ 添加", self._add),
            ("✎ 编辑", self._edit),
            ("✕ 删除", self._delete),
            ("↻ 开关", self._toggle),
        ]
        for text, cmd in style_btns:
            btn = tk.Button(tb, text=text, command=cmd,
                            bg=C["btn"], fg=C["fg"], bd=0, padx=10, pady=3,
                            font=("Microsoft YaHei", 9), cursor="hand2",
                            activebackground="#45475a", activeforeground=C["fg"])
            btn.pack(side="left", padx=2, pady=5)
            btn.bind("<Enter>", lambda e,b=btn:b.configure(bg="#45475a"))
            btn.bind("<Leave>", lambda e,b=btn:b.configure(bg=C["btn"]))

        tk.Frame(tb, bg=C["card"], width=12).pack(side="left")

        for text, cmd in [("全部启用", self._enable_all), ("全部禁用", self._disable_all)]:
            btn = tk.Button(tb, text=text, command=cmd,
                            bg=C["card"], fg=C["dim"], bd=0, padx=8, pady=3,
                            font=("Microsoft YaHei", 8), cursor="hand2",
                            activebackground="#45475a", activeforeground=C["fg"])
            btn.pack(side="left", padx=2, pady=5)
            btn.bind("<Enter>", lambda e,b=btn:b.configure(fg=C["fg"]))
            btn.bind("<Leave>", lambda e,b=btn:b.configure(fg=C["dim"]))

        # ── 保存按钮 (右侧) ──
        save_btn = tk.Button(tb, text="💾 保存并应用", command=self._save_reload,
                             bg="#89b4fa", fg="#1a1a2e", bd=0, padx=14, pady=3,
                             font=("Microsoft YaHei", 9, "bold"), cursor="hand2",
                             activebackground="#b4d0fb", activeforeground="#1a1a2e")
        save_btn.pack(side="right", padx=6, pady=5)

        settings_btn = tk.Button(tb, text="⚙", command=self._edit_settings,
                                 bg=self.C["card"], fg=self.C["dim"], bd=0,
                                 font=("Microsoft YaHei", 12), cursor="hand2",
                                 activebackground="#45475a", activeforeground=self.C["fg"])
        settings_btn.pack(side="right", padx=2, pady=5)
        settings_btn.bind("<Enter>", lambda e,b=settings_btn:b.configure(fg=self.C["fg"]))
        settings_btn.bind("<Leave>", lambda e,b=settings_btn:b.configure(fg=self.C["dim"]))

        # ── 列表 ──
        list_frame = tk.Frame(self.root, bg=C["bg"])
        list_frame.pack(fill="both", expand=True, padx=6, pady=2)

        cols = ("on", "trigger", "action", "value")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                  selectmode="browse", height=14)
        self.tree.heading("on", text="状态")
        self.tree.heading("trigger", text="触发键")
        self.tree.heading("action", text="动作")
        self.tree.heading("value", text="参数")
        self.tree.column("on", width=50, anchor="center")
        self.tree.column("trigger", width=170)
        self.tree.column("action", width=140)
        self.tree.column("value", width=310)

        # tree style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=C["card"], foreground=C["fg"],
                        fieldbackground=C["card"], borderwidth=0,
                        rowheight=26, font=("Microsoft YaHei", 9))
        style.configure("Treeview.Heading",
                        background=C["bar"], foreground=C["fg"],
                        font=("Microsoft YaHei", 9, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", "#313244")],
                  foreground=[("selected", C["accent"])])

        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self._edit())

        # ── 状态栏 ──
        self.status = tk.Label(self.root, text="", bg=C["bar"], fg=C["dim"],
                                anchor="w", font=("Microsoft YaHei", 8), padx=8, pady=2)
        self.status.pack(fill="x")

    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, e in enumerate(self.entries):
            en = e.get("enabled", True)
            self.tree.insert("", "end", iid=str(i), values=(
                "●" if en else "○",
                self._display_hotkey(e.get("hotkey", "")),
                self._display_action(e.get("action", "")),
                e.get("value", ""),
            ))
        enabled = sum(1 for e in self.entries if e.get("enabled", True))
        thk = self.settings.get("toggle_hotkey", "win+shift+q")
        self.status.config(
            text=f"  {len(self.entries)} 个热键，{enabled} 个已启用  |  "
                 f"全局开关: {thk}  |  双击编辑  |  修改后点击「保存并应用」生效")

    def _display_hotkey(self, s):
        parts = s.split("+")
        out = []
        for p in parts:
            m = {"ctrl":"Ctrl","alt":"Alt","shift":"Shift","win":"Win",
                 "num 0":"0⃣","num 1":"1⃣","num 2":"2⃣","num 3":"3⃣",
                 "num 4":"4⃣","num 5":"5⃣","num 6":"6⃣","num 7":"7⃣",
                 "num 8":"8⃣","num 9":"9⃣","num /":"/","num *":"*",
                 "num -":"-","num +":"+","num .":"."}
            out.append(m.get(p, p.upper()))
        return " + ".join(out)

    def _display_action(self, a):
        for n, aid in ACTION_OPTIONS:
            if aid == a: return n
        return a

    def _idx(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _add(self):
        def cb(result):
            self.entries.append(result)
            self._save_reload()
        HotkeyEditDialog(self.root, on_save=cb)

    def _edit(self):
        i = self._idx()
        if i is None: return
        def cb(result):
            self.entries[i] = result
            self._save_reload()
        HotkeyEditDialog(self.root, entry=self.entries[i], on_save=cb)

    def _delete(self):
        i = self._idx()
        if i is None: return
        e = self.entries[i]
        if messagebox.askyesno("确认删除", f'删除热键 "{self._display_hotkey(e.get("hotkey",""))}"？'):
            self.entries.pop(i)
            self._save_reload()

    def _toggle(self):
        i = self._idx()
        if i is None: return
        self.entries[i]["enabled"] = not self.entries[i].get("enabled", True)
        self._save_reload()

    def _enable_all(self):
        for e in self.entries: e["enabled"] = True
        self._save_reload()

    def _disable_all(self):
        for e in self.entries: e["enabled"] = False
        self._save_reload()

    def _on_master_toggle(self):
        """Handle master toggle hotkey — flip all enabled states."""
        any_enabled = any(e.get("enabled", True) for e in self.entries)
        new_state = not any_enabled
        for e in self.entries:
            e["enabled"] = new_state
        save_config(self.entries, self.settings)
        self.engine.reload(self.entries)
        self.root.after(0, self._refresh)

    def _edit_settings(self):
        """Open a small dialog to configure the master toggle hotkey."""
        dlg = tk.Toplevel(self.root)
        dlg.title("设置")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=self.C["bg"])

        frm = tk.Frame(dlg, bg=self.C["bg"], padx=16, pady=12)
        frm.pack()

        tk.Label(frm, text="全局开关热键", bg=self.C["bg"], fg=self.C["fg"],
                 font=("Microsoft YaHei", 10, "bold")).pack(pady=(0,8))

        tk.Label(frm, text="按下此键可快速启用/禁用全部热键",
                 bg=self.C["bg"], fg=self.C["dim"],
                 font=("Microsoft YaHei", 8)).pack(pady=(0,8))

        row_f = tk.Frame(frm, bg=self.C["bg"])
        row_f.pack()

        cur_thk = self.settings.get("toggle_hotkey", "win+shift+q")
        cur_mod = 0; cur_key = ""
        parts = [p.strip().lower() for p in cur_thk.split("+") if p.strip()]
        mod_map = {"ctrl": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT, "win": MOD_WIN}
        for p in parts:
            if p in mod_map: cur_mod |= mod_map[p]
            else: cur_key = p; break
        if not cur_key and parts: cur_key = parts[-1]
        cur_key_disp = ""
        for disp in KEY_VK:
            if disp.lower() == cur_key: cur_key_disp = disp; break
        if not cur_key_disp and len(cur_key) == 1: cur_key_disp = cur_key.upper()

        mod_var = tk.StringVar(value=MOD_NAME.get(cur_mod, "Win"))
        mod_cb = ttk.Combobox(row_f, textvariable=mod_var,
                               values=[n for n,_ in MOD_OPTIONS],
                               state="readonly", width=14)
        mod_cb.pack(side="left", padx=4)

        tk.Label(row_f, text="+", bg=self.C["bg"], fg=self.C["fg"]).pack(side="left")

        key_vals = []
        for cat, keys in KEY_CATEGORIES:
            key_vals.append(f"── {cat} ──")
            key_vals.extend(keys)
        key_var = tk.StringVar(value=cur_key_disp or "Q")
        key_cb = ttk.Combobox(row_f, textvariable=key_var,
                               values=key_vals, state="readonly", width=14)
        key_cb.pack(side="left", padx=4)

        def _validate(*a):
            if key_var.get().startswith("──"): key_var.set("Q")
        key_var.trace_add("write", _validate)

        def save():
            mn = mod_var.get()
            mv = 0
            for n,v in MOD_OPTIONS:
                if n == mn: mv = v; break
            kn = key_var.get()
            if kn.startswith("──") or not kn: return
            self.settings["toggle_hotkey"] = entry_to_hotkey_str(mv, kn)
            dlg.destroy()
            self._save_reload()

        ttk.Button(frm, text="保存", command=save).pack(pady=(12,0))

        dlg.geometry(f"+{self.root.winfo_rootx()+100}+{self.root.winfo_rooty()+80}")

    def _save_reload(self):
        save_config(self.entries, self.settings)
        self.engine.reload(self.entries)
        self._refresh()

    def _on_close(self):
        self.engine.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

def main():
    App().run()

if __name__ == "__main__":
    main()
