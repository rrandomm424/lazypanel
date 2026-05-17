# LazyPanel

Windows 全局快捷键管理器。支持模拟按键、启动程序、打开网址、运行命令和媒体控制。

## 功能

- **全局热键** — 通过 Win32 API 注册系统级快捷键，在任何应用中生效
- **5 种动作类型**：模拟按键、启动程序、打开网址、运行命令、媒体控制
- **两种界面**：原生 tkinter 版本（轻量 9MB）和 Web 版本（pywebview，35MB）
- **暗色主题** — 护眼的深色界面
- **可自定义** — 通过 `config.json` 配置快捷键

## 快速开始

**运行已打包版本：**
```bash
run.bat
```

**从源码运行：**
```bash
pip install pywebview    # Web 版需要
python lazypanel.py      # tkinter 版
python lazypanel_web.py  # Web 版
```

## 配置

编辑 `config.json`，`hotkeys` 数组中的每个条目包含：

```json
{
  "hotkey": "ctrl+shift+a",   // 触发快捷键
  "action": "key",            // key / launch / url / command / media
  "value": "ctrl+v",          // 执行的动作参数
  "enabled": true             // 是否启用
}
```

默认切换热键为 `ctrl+/`，可在 `settings.toggle_hotkey` 中修改。
