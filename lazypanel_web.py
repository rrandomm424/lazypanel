"""
LazyPanel Web — pywebview version with HTML/CSS UI
=====================================================
Requires: pip install pywebview
Reuses the engine and config from lazypanel.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lazypanel import (
    HotkeyEngine, load_config, save_config,
    hotkey_to_vk, execute_action, send_key_combo,
    KEY_VK, MOD_OPTIONS, MOD_NAME, MOD_CONTROL, MOD_ALT, MOD_SHIFT, MOD_WIN,
    KEY_CATEGORIES, ACTION_OPTIONS, MEDIA_OPTIONS, MEDIA_VK,
    entry_to_hotkey_str
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LazyPanel</title>
<style>
:root {
  --bg: #1e1e2e; --surface: #181825; --overlay: #313244;
  --text: #cdd6f4; --sub: #a6adc8; --muted: #585b70;
  --accent: #89b4fa; --green: #a6e3a1; --red: #f38ba8;
  --yellow: #f9e2af; --border: #45475a;
  --radius: 8px; --font: 'Segoe UI','Microsoft YaHei',sans-serif;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background: var(--bg); color: var(--text);
  font-family: var(--font); font-size: 13px;
  overflow: hidden; height: 100vh;
  user-select: none; -webkit-user-select: none;
}
#app { display:flex; flex-direction:column; height:100vh; }

/* header */
.header {
  background: var(--surface); padding: 8px 16px;
  display:flex; align-items:center; gap:12px;
  border-bottom:1px solid var(--border);
  -webkit-app-region: drag;
}
.header .logo { font-size:16px; font-weight:700; color: var(--accent); }
.header .sub { color: var(--muted); font-size:11px; }

/* toolbar */
.toolbar {
  display:flex; gap:6px; padding:8px 12px;
  background: var(--surface); border-bottom:1px solid var(--border);
  flex-wrap:wrap;
}
.btn {
  padding:5px 14px; border-radius:6px; border:none; cursor:pointer;
  font-size:12px; font-family:var(--font); font-weight:500;
  transition: all .15s; white-space:nowrap;
}
.btn:active { transform:scale(.96); }
.btn-primary { background: var(--accent); color: #1e1e2e; }
.btn-primary:hover { filter: brightness(1.15); }
.btn-surface { background: var(--overlay); color: var(--text); }
.btn-surface:hover { background: #45475a; }
.btn-danger { background: transparent; color: var(--red); }
.btn-danger:hover { background: rgba(243,139,168,.15); }
.btn-sm { padding:3px 10px; font-size:11px; }
.spacer { flex:1; }

/* list */
.list-container { flex:1; overflow-y:auto; padding:8px 12px; }
.list-container::-webkit-scrollbar { width:6px; }
.list-container::-webkit-scrollbar-track { background:transparent; }
.list-container::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

.list-header {
  display:grid; grid-template-columns:44px 1fr 100px 1fr 72px;
  gap:4px; padding:6px 8px; font-size:11px; color:var(--muted);
  font-weight:600; position:sticky; top:0; background:var(--bg);
  border-bottom:1px solid var(--border); z-index:1;
}
.hotkey-row {
  display:grid; grid-template-columns:44px 1fr 100px 1fr 72px;
  gap:4px; padding:8px; align-items:center;
  border-radius:6px; transition:background .1s;
  border:1px solid transparent; margin-bottom:2px; cursor:default;
}
.hotkey-row:hover { background: var(--overlay); }
.hotkey-row.disabled { opacity:.45; }
.status-dot { text-align:center; font-size:14px; cursor:pointer; }
.status-dot.on { color: var(--green); }
.status-dot.off { color: var(--red); }
.hotkey-tag {
  display:inline-flex; gap:3px; align-items:center;
  font-weight:600; font-size:12px; flex-wrap:wrap;
}
.key-badge {
  background: var(--overlay); color: var(--text);
  padding:2px 8px; border-radius:4px; font-size:12px;
  border:1px solid var(--border);
}
.key-plus { color: var(--muted); font-size:10px; }
.action-type { color: var(--sub); font-size:12px; }
.action-value {
  color: var(--yellow); font-family:'Cascadia Code','Consolas',monospace;
  font-size:11px; word-break:break-all;
}
.row-actions { display:flex; gap:4px; justify-content:flex-end; }

/* footer */
.footer {
  background: var(--surface); padding:6px 16px;
  border-top:1px solid var(--border); font-size:11px; color:var(--muted);
  display:flex; gap:16px;
}
.footer .toggle-key { color: var(--accent); font-weight:600; }

/* modal overlay */
.modal-overlay {
  display:none; position:fixed; inset:0; background:rgba(0,0,0,.6);
  z-index:100; justify-content:center; align-items:center;
  animation:fadeIn .15s ease;
}
.modal-overlay.active { display:flex; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
@keyframes slideUp { from{transform:translateY(20px);opacity:0} to{transform:translateY(0);opacity:1} }
.modal {
  background: var(--surface); border-radius:12px; padding:20px 24px;
  min-width:380px; max-width:440px;
  border:1px solid var(--border);
  box-shadow:0 8px 32px rgba(0,0,0,.5);
  animation:slideUp .2s ease;
}
.modal h3 { margin-bottom:16px; color:var(--accent); font-size:15px; }
.form-row { display:flex; align-items:center; gap:8px; margin-bottom:10px; }
.form-row label { width:70px; flex-shrink:0; color:var(--sub); font-size:12px; }
select, input[type="text"] {
  background: var(--overlay); color: var(--text);
  border:1px solid var(--border); border-radius:6px;
  padding:6px 10px; font-size:12px; font-family:var(--font);
  outline:none; flex:1;
}
select:focus, input:focus { border-color: var(--accent); }
.preview {
  color: var(--yellow); font-size:14px; font-weight:700;
  padding:6px 0; text-align:center;
}
.modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:16px; }
.hint { color: var(--muted); font-size:10px; margin-top:2px; min-height:16px; }
.empty-state {
  text-align:center; padding:60px 40px; color:var(--muted); font-size:14px;
}
.empty-state .big-icon { font-size:48px; display:block; margin-bottom:16px; color:var(--border); }

/* toast */
.toast {
  position:fixed; bottom:60px; left:50%; transform:translateX(-50%);
  background:var(--green); color:#1e1e2e; padding:8px 20px;
  border-radius:8px; font-size:12px; font-weight:600;
  z-index:200; animation:fadeIn .2s ease;
  pointer-events:none; opacity:0; transition:opacity .3s;
}
.toast.show { opacity:1; }
</style>
</head>
<body>
<div id="app">
  <div class="header">
    <span class="logo">LazyPanel</span>
    <span class="sub">快捷键管理器</span>
  </div>
  <div class="toolbar">
    <button class="btn btn-primary" onclick="showAddDialog()">＋ 添加</button>
    <button class="btn btn-surface" onclick="toggleAll()">↻ 开关</button>
    <button class="btn btn-surface" onclick="enableAll()">全部启用</button>
    <button class="btn btn-surface" onclick="disableAll()">全部禁用</button>
    <span class="spacer"></span>
    <button class="btn btn-surface" onclick="showSettingsDialog()" title="全局设置">⚙</button>
    <button class="btn btn-primary" onclick="saveState()">💾 保存</button>
  </div>
  <div class="list-container">
    <div class="list-header">
      <span style="text-align:center">状态</span>
      <span>触发键</span>
      <span>动作</span>
      <span>参数</span>
      <span style="text-align:right">操作</span>
    </div>
    <div id="hotkey-list"></div>
  </div>
  <div class="footer">
    <span id="footer-count"></span>
    <span>全局开关: <span class="toggle-key" id="footer-toggle"></span></span>
  </div>
</div>

<div class="toast" id="toast"></div>

<!-- 编辑/添加热键弹窗 -->
<div class="modal-overlay" id="edit-modal" onclick="closeModalOutside(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <h3 id="modal-title">添加热键</h3>
    <div class="form-row">
      <label>修饰键</label>
      <select id="mod-select"></select>
      <span style="color:var(--muted)">+</span>
      <select id="key-select"></select>
    </div>
    <div class="preview" id="hk-preview"></div>
    <div class="form-row">
      <label>动作</label>
      <select id="act-select"></select>
    </div>
    <div class="form-row" id="val-row">
      <label>参数</label>
      <input type="text" id="val-input" placeholder="ctrl+c">
    </div>
    <div class="form-row" id="media-row" style="display:none">
      <label>媒体</label>
      <select id="media-select"></select>
    </div>
    <div class="hint" id="val-hint"></div>
    <div class="form-row">
      <label></label>
      <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
        <input type="checkbox" id="enabled-check" checked>
        <span>启用此热键</span>
      </label>
    </div>
    <div class="modal-actions">
      <button class="btn btn-surface" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" onclick="saveEntry()" id="modal-save-btn">保存</button>
    </div>
  </div>
</div>

<!-- 设置弹窗 -->
<div class="modal-overlay" id="settings-modal" onclick="closeSettingsModalOutside(event)">
  <div class="modal" onclick="event.stopPropagation()" style="min-width:320px">
    <h3>全局设置</h3>
    <div class="form-row">
      <label>全局开关</label>
      <select id="settings-mod-select"></select>
      <span style="color:var(--muted)">+</span>
      <select id="settings-key-select"></select>
    </div>
    <div class="preview" id="settings-hk-preview"></div>
    <div class="hint" style="text-align:center">按此键快速启用/禁用全部热键</div>
    <div class="modal-actions">
      <button class="btn btn-surface" onclick="closeSettingsModal()">取消</button>
      <button class="btn btn-primary" onclick="saveSettings()">保存</button>
    </div>
  </div>
</div>

<script>
// ===================================================================
// State
// ===================================================================
let entries = [];
let settings = {};
let editingIndex = -1;

// ===================================================================
// API calls to Python
// ===================================================================
function loadState() {
  try {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_state) {
      console.error('API not ready');
      return;
    }
    var promise = window.pywebview.api.get_state();
    if (promise && promise.then) {
      promise.then(function(data) {
        entries = data.entries;
        settings = data.settings;
        render();
      }).catch(function(e) { console.error(e); });
    } else {
      entries = promise.entries;
      settings = promise.settings;
      render();
    }
  } catch(e) { console.error('loadState error:', e); }
}

function saveState() {
  try {
    if (!window.pywebview.api.save_state) return;
    var promise = window.pywebview.api.save_state(
      JSON.stringify(entries), JSON.stringify(settings)
    );
    if (promise && promise.then) {
      promise.then(function() {
        showToast('已保存并应用');
        loadState();
      }).catch(function(e) { showToast('保存失败', true); });
    } else {
      showToast('已保存并应用');
      loadState();
    }
  } catch(e) { showToast('保存失败', true); }
}

// ===================================================================
// Toast
// ===================================================================
function showToast(msg, isError) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.style.background = isError ? 'var(--red)' : 'var(--green)';
  el.classList.add('show');
  setTimeout(function() { el.classList.remove('show'); }, 2000);
}

// ===================================================================
// Render
// ===================================================================
var MOD_NAMES = {0:'无',2:'Ctrl',1:'Alt',4:'Shift',8:'Win',6:'Ctrl+Shift',3:'Ctrl+Alt',5:'Alt+Shift'};
var MOD_VALUES = {0:0,'无':0,'Ctrl':2,'Alt':1,'Shift':4,'Win':8};

function render() {
  var list = document.getElementById('hotkey-list');
  var html = '';
  if (entries.length === 0) {
    html = '<div class="empty-state">'
      + '<span class="big-icon">⌨</span>'
      + '还没有热键<br><br>'
      + '点击「＋ 添加」开始创建'
      + '</div>';
  } else {
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      var en = e.enabled !== false;
      var rowClass = en ? '' : 'disabled';
      html += '<div class="hotkey-row ' + rowClass + '">'
        + '<div class="status-dot ' + (en?'on':'off') + '" onclick="toggleEntry(' + i + ')" title="点击切换">' + (en?'●':'○') + '</div>'
        + '<div><span class="hotkey-tag">' + formatHotkey(e.hotkey) + '</span></div>'
        + '<div class="action-type">' + formatAction(e.action) + '</div>'
        + '<div class="action-value">' + escHtml(e.value||'') + '</div>'
        + '<div class="row-actions">'
        + '<button class="btn btn-surface btn-sm" onclick="editEntry(' + i + ')">编辑</button>'
        + '<button class="btn btn-danger btn-sm" onclick="deleteEntry(' + i + ')">删除</button>'
        + '</div></div>';
    }
  }
  list.innerHTML = html;

  var enabled = 0;
  for (var i = 0; i < entries.length; i++) {
    if (entries[i].enabled !== false) enabled++;
  }
  document.getElementById('footer-count').textContent = entries.length + ' 个热键，' + enabled + ' 个已启用';
  document.getElementById('footer-toggle').textContent = settings.toggle_hotkey || '未设置';
}

function formatHotkey(hk) {
  if (!hk) return '';
  var parts = hk.split('+');
  var out = [];
  for (var i = 0; i < parts.length; i++) {
    var p = parts[i];
    var m = {'ctrl':'Ctrl','alt':'Alt','shift':'Shift','win':'Win',
      'num 0':'0','num 1':'1','num 2':'2','num 3':'3','num 4':'4',
      'num 5':'5','num 6':'6','num 7':'7','num 8':'8','num 9':'9',
      'num /':'/','num *':'*','num -':'-','num +':'+','num .':'.'};
    var label = m[p] || p.toUpperCase();
    out.push('<span class="key-badge">' + escHtml(label) + '</span>');
  }
  return out.join('<span class="key-plus">+</span>');
}

function formatAction(a) {
  var map = {key:'模拟按键',launch:'启动程序',url:'打开网址',command:'运行命令',media:'媒体控制'};
  return map[a] || a;
}

function escHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ===================================================================
// List actions
// ===================================================================
function toggleEntry(i) {
  entries[i].enabled = !(entries[i].enabled !== false);
  render();
}

function toggleAll() {
  var anyOn = false;
  for (var i = 0; i < entries.length; i++) {
    if (entries[i].enabled !== false) { anyOn = true; break; }
  }
  for (var i = 0; i < entries.length; i++) {
    entries[i].enabled = !anyOn;
  }
  render();
}

function enableAll() {
  for (var i = 0; i < entries.length; i++) entries[i].enabled = true;
  render();
}

function disableAll() {
  for (var i = 0; i < entries.length; i++) entries[i].enabled = false;
  render();
}

// ===================================================================
// Modal — edit / add
// ===================================================================
function showAddDialog() {
  editingIndex = -1;
  document.getElementById('modal-title').textContent = '添加热键';
  document.getElementById('modal-save-btn').textContent = '添加';
  populateForm({hotkey:'ctrl+up', action:'key', value:'', enabled:true});
  document.getElementById('edit-modal').classList.add('active');
  setTimeout(function() { document.getElementById('key-select').focus(); }, 200);
}

function editEntry(i) {
  editingIndex = i;
  document.getElementById('modal-title').textContent = '编辑热键';
  document.getElementById('modal-save-btn').textContent = '保存';
  populateForm(entries[i]);
  document.getElementById('edit-modal').classList.add('active');
  setTimeout(function() { document.getElementById('key-select').focus(); }, 200);
}

function closeModal() {
  document.getElementById('edit-modal').classList.remove('active');
}

function closeModalOutside(e) {
  if (e.target === e.currentTarget) closeModal();
}

function deleteEntry(i) {
  if (confirm('确认删除此热键？')) {
    entries.splice(i, 1);
    render();
    showToast('已删除');
  }
}

function populateForm(e) {
  var hk = e.hotkey || '';
  var parts = hk.split('+').map(function(p) { return p.trim().toLowerCase(); });
  var modKeys = {'ctrl':2,'alt':1,'shift':4,'win':8};
  var mod = 0, key = '';
  for (var i = 0; i < parts.length; i++) {
    var p = parts[i];
    if (modKeys[p] !== undefined) mod |= modKeys[p];
    else { key = p; break; }
  }
  if (!key && parts.length) key = parts[parts.length - 1];

  var act = e.action || 'key';

  document.getElementById('mod-select').value = mod;
  document.getElementById('act-select').value = act;
  document.getElementById('val-input').value = e.value || '';
  document.getElementById('enabled-check').checked = e.enabled !== false;
  updateKeySelect('key-select', key);
  updatePreview();
  onActChange();
}

function updateKeySelect(selectId, matchKey) {
  var sel = document.getElementById(selectId);
  sel.innerHTML = '';
  var cats = KEY_CATEGORIES;
  for (var ci = 0; ci < cats.length; ci++) {
    var cat = cats[ci];
    var og = document.createElement('optgroup');
    og.label = cat[0];
    var keys = cat[1];
    for (var ki = 0; ki < keys.length; ki++) {
      var k = keys[ki];
      var opt = document.createElement('option');
      opt.value = k;
      opt.textContent = k;
      if (k.toLowerCase() === matchKey) opt.selected = true;
      og.appendChild(opt);
    }
    sel.appendChild(og);
  }
  if (!sel.value && sel.options.length) sel.options[0].selected = true;
}

function updatePreview() {
  var mod = parseInt(document.getElementById('mod-select').value);
  var key = document.getElementById('key-select').value;
  var modName = MOD_NAMES[mod] || '';
  var display = modName && modName !== '无'
    ? modName + ' + ' + key
    : key;
  document.getElementById('hk-preview').textContent = display;
}

function onActChange() {
  var act = document.getElementById('act-select').value;
  document.getElementById('val-row').style.display = act === 'media' ? 'none' : 'flex';
  document.getElementById('media-row').style.display = act === 'media' ? 'flex' : 'none';
  var hints = {
    'key':'如: ctrl+c, win+d',
    'launch':'如: notepad.exe 或完整路径',
    'url':'如: https://github.com',
    'command':'如: shutdown /s /t 0',
    'media':'选择媒体控制指令',
  };
  document.getElementById('val-hint').textContent = hints[act] || '';
}

function saveEntry() {
  var mod = parseInt(document.getElementById('mod-select').value);
  var key = document.getElementById('key-select').value;
  var act = document.getElementById('act-select').value;
  var val = act === 'media'
    ? document.getElementById('media-select').value
    : document.getElementById('val-input').value;
  var enabled = document.getElementById('enabled-check').checked;

  if (!key) return;

  var keyLower = key.toLowerCase().replace(/小键盘 /g, 'num ');
  var modParts = [];
  if (mod & 2) modParts.push('ctrl');
  if (mod & 1) modParts.push('alt');
  if (mod & 4) modParts.push('shift');
  if (mod & 8) modParts.push('win');
  modParts.push(keyLower);
  var hk = modParts.join('+');

  var entry = { hotkey: hk, action: act, value: val, enabled: enabled };

  if (editingIndex >= 0) {
    entries[editingIndex] = entry;
  } else {
    entries.push(entry);
  }
  closeModal();
  render();
}

// ===================================================================
// Modal — settings
// ===================================================================
function showSettingsDialog() {
  var hk = settings.toggle_hotkey || 'win+shift+q';
  var parts = hk.split('+').map(function(p) { return p.trim().toLowerCase(); });
  var modKeys = {'ctrl':2,'alt':1,'shift':4,'win':8};
  var mod = 0, key = '';
  for (var i = 0; i < parts.length; i++) {
    var p = parts[i];
    if (modKeys[p] !== undefined) mod |= modKeys[p];
    else { key = p; break; }
  }
  if (!key && parts.length) key = parts[parts.length - 1];

  document.getElementById('settings-mod-select').value = mod;
  updateKeySelect('settings-key-select', key);
  updateSettingsPreview();
  document.getElementById('settings-modal').classList.add('active');
}

function closeSettingsModal() {
  document.getElementById('settings-modal').classList.remove('active');
}

function closeSettingsModalOutside(e) {
  if (e.target === e.currentTarget) closeSettingsModal();
}

function updateSettingsPreview() {
  var mod = parseInt(document.getElementById('settings-mod-select').value);
  var key = document.getElementById('settings-key-select').value;
  var modName = MOD_NAMES[mod] || '';
  var display = modName && modName !== '无'
    ? modName + ' + ' + key
    : key;
  document.getElementById('settings-hk-preview').textContent = display;
}

function saveSettings() {
  var mod = parseInt(document.getElementById('settings-mod-select').value);
  var key = document.getElementById('settings-key-select').value;
  if (!key) return;

  var keyLower = key.toLowerCase().replace(/小键盘 /g, 'num ');
  var modParts = [];
  if (mod & 2) modParts.push('ctrl');
  if (mod & 1) modParts.push('alt');
  if (mod & 4) modParts.push('shift');
  if (mod & 8) modParts.push('win');
  modParts.push(keyLower);

  settings.toggle_hotkey = modParts.join('+');
  closeSettingsModal();
  render();
  showToast('设置已更新，点击「保存」生效');
}

// ===================================================================
// Keyboard shortcuts
// ===================================================================
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    if (document.getElementById('settings-modal').classList.contains('active')) {
      closeSettingsModal();
    } else if (document.getElementById('edit-modal').classList.contains('active')) {
      closeModal();
    }
  }
  if (e.key === 'Enter') {
    if (document.getElementById('edit-modal').classList.contains('active')) {
      saveEntry();
    } else if (document.getElementById('settings-modal').classList.contains('active')) {
      saveSettings();
    }
  }
});

// ===================================================================
// Static data for key categories
// ===================================================================
var KEY_CATEGORIES = [
  ["方向键",["↑","↓","←","→"]],
  ["小键盘",["小键盘 0","小键盘 1","小键盘 2","小键盘 3","小键盘 4","小键盘 5","小键盘 6","小键盘 7","小键盘 8","小键盘 9","小键盘 /","小键盘 *","小键盘 -","小键盘 +","小键盘 ."]],
  ["字母",["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"]],
  ["数字",["0","1","2","3","4","5","6","7","8","9"]],
  ["功能键",["F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12"]],
  ["特殊键",["Tab","Esc","空格","回车","退格","Delete","Insert","Home","End","PgUp","PgDn"]],
  ["符号",[",",".","/",";","'","[","]","\\","`","-","="]],
];

function initSelects() {
  var modOpts = [
    [0,'无'],[2,'Ctrl'],[1,'Alt'],[4,'Shift'],[8,'Win'],
    [6,'Ctrl+Shift'],[3,'Ctrl+Alt'],[5,'Alt+Shift']
  ];
  var modSel = document.getElementById('mod-select');
  for (var i = 0; i < modOpts.length; i++) {
    var o = document.createElement('option');
    o.value = modOpts[i][0];
    o.textContent = modOpts[i][1];
    modSel.appendChild(o);
  }

  // settings的修饰键下拉用相同数据
  var settingsModSel = document.getElementById('settings-mod-select');
  for (var i = 0; i < modOpts.length; i++) {
    var o = document.createElement('option');
    o.value = modOpts[i][0];
    o.textContent = modOpts[i][1];
    settingsModSel.appendChild(o);
  }

  var actOpts = [
    ['key','模拟按键'],['launch','启动程序'],['url','打开网址'],
    ['command','运行命令'],['media','媒体控制']
  ];
  var actSel = document.getElementById('act-select');
  for (var i = 0; i < actOpts.length; i++) {
    var o = document.createElement('option');
    o.value = actOpts[i][0];
    o.textContent = actOpts[i][1];
    actSel.appendChild(o);
  }

  var mediaVals = ['volume_up','volume_down','volume_mute','next_track','prev_track','play_pause','stop'];
  var medSel = document.getElementById('media-select');
  for (var i = 0; i < mediaVals.length; i++) {
    var o = document.createElement('option');
    o.value = mediaVals[i];
    o.textContent = mediaVals[i];
    medSel.appendChild(o);
  }

  // Listeners
  document.getElementById('mod-select').addEventListener('change', updatePreview);
  document.getElementById('key-select').addEventListener('change', updatePreview);
  document.getElementById('act-select').addEventListener('change', onActChange);
  document.getElementById('settings-mod-select').addEventListener('change', updateSettingsPreview);
  document.getElementById('settings-key-select').addEventListener('change', updateSettingsPreview);
}

// ===================================================================
// Startup
// ===================================================================
initSelects();

function startWhenReady() {
  var platform = (window.pywebview && window.pywebview.platform) || '';
  if (platform === 'mshtml') {
    document.getElementById('hotkey-list').innerHTML =
      '<div class="empty-state" style="color:#f38ba8">'
      + '<span class="big-icon" style="color:var(--red)">⚠</span>'
      + '浏览器引擎不支持<br><br>'
      + '当前使用 MSHTML (IE) 引擎，不支持现代界面。<br><br>'
      + '请安装 <b>Edge WebView2 Runtime</b> 后重试：<br>'
      + '<a href="https://go.microsoft.com/fwlink/p/?LinkId=2124703" style="color:#89b4fa">下载 WebView2</a>'
      + '</div>';
    var btns = document.querySelectorAll('.btn');
    for (var i = 0; i < btns.length; i++) btns[i].disabled = true;
    return;
  }

  if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_state === 'function') {
    loadState();
  } else {
    window.addEventListener('pywebviewready', function() {
      setTimeout(loadState, 100);
    }, {once: true});
  }
}
startWhenReady();
</script>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════════════════════
# pywebview API — bridges JS ↔ Python
# ═══════════════════════════════════════════════════════════════════════════
class LazyApi:
    def __init__(self):
        self.entries, self.settings = load_config()
        self.engine = HotkeyEngine()
        self.engine.on_toggle = self._on_master_toggle
        self.engine.start(self.entries, self.settings)

    def get_state(self):
        return {
            "entries": self.entries,
            "settings": self.settings,
        }

    def save_state(self, entries_json, settings_json):
        try:
            self.entries = json.loads(entries_json)
            self.settings = json.loads(settings_json)
        except Exception as e:
            return {"error": str(e)}
        save_config(self.entries, self.settings)
        self.engine.reload(self.entries, self.settings)

    def _on_master_toggle(self):
        any_enabled = any(e.get("enabled", True) for e in self.entries)
        new_state = not any_enabled
        for e in self.entries:
            e["enabled"] = new_state
        save_config(self.entries, self.settings)
        self.engine.reload(self.entries)
        try:
            self._window.evaluate_js("loadState()")
        except Exception:
            pass

    def set_window(self, window):
        self._window = window

    def stop(self):
        self.engine.stop()


def main():
    import webview
    api = LazyApi()
    icon_path = os.path.join(BASE_DIR, "icon.ico")
    window = webview.create_window(
        "LazyPanel", html=HTML, js_api=api,
        width=760, height=520, min_size=(520, 360),
        resizable=True, icon=icon_path if os.path.exists(icon_path) else None,
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
