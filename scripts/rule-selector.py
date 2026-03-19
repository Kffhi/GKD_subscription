#!/usr/bin/env python3
"""
GKD 订阅规则可视化勾选工具
运行: python scripts/rule-selector.py
访问: http://localhost:8765
"""

import os
import re
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import webbrowser
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(BASE_DIR, 'src', 'apps')
OUTPUT_FILE = os.path.join(BASE_DIR, 'selected_apps.json')

CATEGORY_PREFIXES = [
    ('开屏广告', '#ef4444'),
    ('全屏广告', '#f97316'),
    ('分段广告', '#eab308'),
    ('局部广告', '#84cc16'),
    ('更新提示', '#06b6d4'),
    ('评价提示', '#8b5cf6'),
    ('通知提示', '#ec4899'),
    ('权限提示', '#6366f1'),
    ('青少年模式', '#14b8a6'),
    ('功能类', '#64748b'),
    ('其他', '#94a3b8'),
]

CATEGORY_COLORS = {k: v for k, v in CATEGORY_PREFIXES}
CATEGORY_ORDER = [k for k, _ in CATEGORY_PREFIXES]


def parse_app_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pkg_id = os.path.basename(filepath).replace('.ts', '')

    # 提取顶层 id 和 name
    id_match = re.search(r"id:\s*['\"]([^'\"]+)['\"]", content)
    app_id = id_match.group(1) if id_match else pkg_id

    # 提取 defineGkdApp 内的第一个 name
    name_match = re.search(r"defineGkdApp\s*\(\s*\{[^}]*?name:\s*['\"]([^'\"]+)['\"]", content, re.DOTALL)
    app_name = name_match.group(1) if name_match else pkg_id

    # 提取所有 groups 里的 name 字段
    groups_match = re.search(r'groups\s*:\s*\[(.+)', content, re.DOTALL)
    categories = set()
    group_count = 0
    if groups_match:
        groups_text = groups_match.group(1)
        group_names = re.findall(r"name:\s*['\"]([^'\"]+)['\"]", groups_text)
        group_count = len(group_names)
        for gname in group_names:
            matched = False
            for prefix, _ in CATEGORY_PREFIXES:
                if gname.startswith(prefix):
                    categories.add(prefix)
                    matched = True
                    break
            if not matched:
                categories.add('其他')

    cats_sorted = sorted(categories, key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99)

    return {
        'id': pkg_id,
        'appId': app_id,
        'name': app_name,
        'categories': cats_sorted,
        'groupCount': group_count,
    }


def load_all_apps():
    apps = []
    for fname in sorted(os.listdir(APPS_DIR)):
        if fname.endswith('.ts'):
            try:
                app = parse_app_file(os.path.join(APPS_DIR, fname))
                apps.append(app)
            except Exception as e:
                print(f'[WARN] 解析失败 {fname}: {e}')
    return apps


def build_html(apps):
    apps_json = json.dumps(apps, ensure_ascii=False)
    categories_json = json.dumps(CATEGORY_ORDER, ensure_ascii=False)
    colors_json = json.dumps(CATEGORY_COLORS, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GKD 规则选择器</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px; position: sticky; top: 0; z-index: 100; }}
  .header-top {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
  .header-title {{ font-size: 20px; font-weight: 700; color: #f1f5f9; display: flex; align-items: center; gap: 10px; }}
  .stats {{ font-size: 13px; color: #94a3b8; }}
  .stats span {{ color: #38bdf8; font-weight: 600; }}
  .toolbar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 12px; }}
  .search-box {{ flex: 1; min-width: 200px; max-width: 360px; padding: 8px 14px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: 14px; outline: none; }}
  .search-box:focus {{ border-color: #38bdf8; }}
  .btn {{ padding: 7px 14px; border-radius: 7px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: all .15s; }}
  .btn-primary {{ background: #2563eb; color: #fff; }}
  .btn-primary:hover {{ background: #1d4ed8; }}
  .btn-success {{ background: #16a34a; color: #fff; }}
  .btn-success:hover {{ background: #15803d; }}
  .btn-danger {{ background: #dc2626; color: #fff; }}
  .btn-danger:hover {{ background: #b91c1c; }}
  .btn-ghost {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
  .btn-ghost:hover {{ background: #334155; color: #e2e8f0; }}
  .btn-ghost.active {{ background: #0ea5e9; color: #fff; border-color: #0ea5e9; }}
  .cat-filters {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }}
  .cat-btn {{ padding: 4px 10px; border-radius: 20px; border: 1.5px solid transparent; cursor: pointer; font-size: 12px; font-weight: 500; transition: all .15s; background: #1e293b; color: #94a3b8; border-color: #334155; }}
  .cat-btn:hover {{ opacity: 0.85; }}
  .cat-btn.active {{ color: #fff; }}
  .main {{ padding: 16px 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }}
  .card {{ background: #1e293b; border: 1.5px solid #334155; border-radius: 10px; padding: 12px 14px; cursor: pointer; transition: all .15s; user-select: none; display: flex; align-items: flex-start; gap: 10px; }}
  .card:hover {{ border-color: #475569; background: #263347; }}
  .card.selected {{ border-color: #2563eb; background: #1e3a5f; }}
  .card-check {{ width: 18px; height: 18px; border-radius: 4px; border: 2px solid #475569; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center; transition: all .15s; }}
  .card.selected .card-check {{ background: #2563eb; border-color: #2563eb; }}
  .card-check svg {{ display: none; }}
  .card.selected .card-check svg {{ display: block; }}
  .card-body {{ flex: 1; min-width: 0; }}
  .card-name {{ font-size: 14px; font-weight: 600; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .card-id {{ font-size: 11px; color: #64748b; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .card-cats {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }}
  .badge {{ padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 500; color: #fff; opacity: 0.9; }}
  .card-groups {{ font-size: 11px; color: #64748b; margin-top: 4px; }}
  .empty {{ text-align: center; padding: 80px 20px; color: #475569; font-size: 16px; }}
  .save-bar {{ position: fixed; bottom: 0; left: 0; right: 0; background: #1e293b; border-top: 1px solid #334155; padding: 12px 24px; display: flex; align-items: center; gap: 12px; z-index: 100; }}
  .save-bar-info {{ flex: 1; font-size: 14px; color: #94a3b8; }}
  .save-bar-info span {{ color: #38bdf8; font-weight: 600; }}
  .toast {{ position: fixed; top: 80px; right: 24px; background: #16a34a; color: #fff; padding: 12px 20px; border-radius: 10px; font-size: 14px; z-index: 200; animation: fadeIn .2s; display: none; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-8px); }} to {{ opacity: 1; transform: none; }} }}
  .hidden {{ display: none !important; }}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <div class="header-title">
      📋 GKD 规则选择器
    </div>
    <div class="stats">
      共 <span id="totalCount">0</span> 个APP &nbsp;·&nbsp;
      显示 <span id="visibleCount">0</span> 个 &nbsp;·&nbsp;
      已选 <span id="selectedCount">0</span> 个
    </div>
  </div>
  <div class="toolbar">
    <input class="search-box" type="text" id="searchInput" placeholder="🔍 搜索 APP 名称或包名…" oninput="filterApps()">
    <button class="btn btn-ghost" onclick="selectAllVisible()">全选当前</button>
    <button class="btn btn-ghost" onclick="deselectAllVisible()">取消当前</button>
    <button class="btn btn-ghost" onclick="selectAll()">全选</button>
    <button class="btn btn-danger" onclick="deselectAll()">清空</button>
  </div>
  <div class="cat-filters" id="catFilters"></div>
</div>
<div class="main">
  <div class="grid" id="appGrid"></div>
  <div class="empty hidden" id="emptyMsg">没有匹配的 APP</div>
</div>
<div class="save-bar">
  <div class="save-bar-info">已选 <span id="saveCount">0</span> 个 APP，将删除其余 <span id="deleteCount">0</span> 个</div>
  <button class="btn btn-ghost" onclick="loadSaved()">加载已保存</button>
  <button class="btn btn-success" onclick="saveSelected()">💾 保存到 JSON</button>
</div>
<div class="toast" id="toast"></div>

<script>
const ALL_APPS = {apps_json};
const CATEGORIES = {categories_json};
const CAT_COLORS = {colors_json};

let selected = new Set(ALL_APPS.map(a => a.id));
let activeCategories = new Set();
let searchQuery = '';

// 初始化分类筛选按钮
function initCatFilters() {{
  const container = document.getElementById('catFilters');
  CATEGORIES.forEach(cat => {{
    const count = ALL_APPS.filter(a => a.categories.includes(cat)).length;
    if (count === 0) return;
    const btn = document.createElement('button');
    btn.className = 'cat-btn';
    btn.dataset.cat = cat;
    btn.style.borderColor = CAT_COLORS[cat] || '#334155';
    btn.textContent = `${{cat}} (${{count}})`;
    btn.onclick = () => toggleCat(cat, btn);
    container.appendChild(btn);
  }});
  // 其他分类
  const othCount = ALL_APPS.filter(a => a.categories.includes('其他') || a.categories.length === 0).length;
  if (othCount > 0) {{
    const btn = document.createElement('button');
    btn.className = 'cat-btn';
    btn.dataset.cat = '其他';
    btn.style.borderColor = '#94a3b8';
    btn.textContent = `其他 (${{othCount}})`;
    btn.onclick = () => toggleCat('其他', btn);
    container.appendChild(btn);
  }}
}}

function toggleCat(cat, btn) {{
  if (activeCategories.has(cat)) {{
    activeCategories.delete(cat);
    btn.classList.remove('active');
    btn.style.background = '';
    btn.style.color = '';
  }} else {{
    activeCategories.add(cat);
    btn.classList.add('active');
    btn.style.background = CAT_COLORS[cat] || '#94a3b8';
    btn.style.color = '#fff';
  }}
  filterApps();
}}

function getVisibleApps() {{
  return ALL_APPS.filter(app => {{
    const q = searchQuery.toLowerCase();
    if (q && !app.name.toLowerCase().includes(q) && !app.id.toLowerCase().includes(q)) return false;
    if (activeCategories.size > 0) {{
      const appCats = app.categories.length > 0 ? app.categories : ['其他'];
      if (!appCats.some(c => activeCategories.has(c))) return false;
    }}
    return true;
  }});
}}

function renderApps() {{
  const visible = getVisibleApps();
  const grid = document.getElementById('appGrid');
  const empty = document.getElementById('emptyMsg');
  grid.innerHTML = '';
  if (visible.length === 0) {{
    empty.classList.remove('hidden');
    return;
  }}
  empty.classList.add('hidden');

  visible.forEach(app => {{
    const isSelected = selected.has(app.id);
    const card = document.createElement('div');
    card.className = 'card' + (isSelected ? ' selected' : '');
    card.dataset.id = app.id;
    card.onclick = () => toggleApp(app.id, card);

    const cats = app.categories.length > 0 ? app.categories : ['其他'];
    const badges = cats.map(c => `<span class="badge" style="background:${{CAT_COLORS[c] || '#94a3b8'}}">${{c}}</span>`).join('');

    card.innerHTML = `
      <div class="card-check">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M2 6l3 3 5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-name" title="${{app.name}}">${{app.name}}</div>
        <div class="card-id" title="${{app.id}}">${{app.id}}</div>
        <div class="card-cats">${{badges}}</div>
        <div class="card-groups">${{app.groupCount}} 个规则组</div>
      </div>
    `;
    grid.appendChild(card);
  }});
  updateStats();
}}

function toggleApp(id, card) {{
  if (selected.has(id)) {{
    selected.delete(id);
    card.classList.remove('selected');
  }} else {{
    selected.add(id);
    card.classList.add('selected');
  }}
  updateStats();
}}

function updateStats() {{
  const visible = getVisibleApps();
  document.getElementById('totalCount').textContent = ALL_APPS.length;
  document.getElementById('visibleCount').textContent = visible.length;
  document.getElementById('selectedCount').textContent = selected.size;
  document.getElementById('saveCount').textContent = selected.size;
  document.getElementById('deleteCount').textContent = ALL_APPS.length - selected.size;
}}

function filterApps() {{
  searchQuery = document.getElementById('searchInput').value;
  renderApps();
}}

function selectAllVisible() {{
  getVisibleApps().forEach(a => selected.add(a.id));
  renderApps();
}}

function deselectAllVisible() {{
  getVisibleApps().forEach(a => selected.delete(a.id));
  renderApps();
}}

function selectAll() {{
  ALL_APPS.forEach(a => selected.add(a.id));
  renderApps();
}}

function deselectAll() {{
  selected.clear();
  renderApps();
}}

function showToast(msg, isError) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = isError ? '#dc2626' : '#16a34a';
  t.style.display = 'block';
  setTimeout(() => {{ t.style.display = 'none'; }}, 2500);
}}

async function saveSelected() {{
  const data = Array.from(selected).sort();
  try {{
    const res = await fetch('/save', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ selected: data }}),
    }});
    const result = await res.json();
    if (result.ok) {{
      showToast(`✅ 已保存 ${{data.length}} 个APP到 selected_apps.json`);
    }} else {{
      showToast('❌ 保存失败: ' + result.error, true);
    }}
  }} catch(e) {{
    showToast('❌ 请求失败: ' + e.message, true);
  }}
}}

async function loadSaved() {{
  try {{
    const res = await fetch('/load');
    const result = await res.json();
    if (result.ok && result.selected) {{
      selected = new Set(result.selected);
      renderApps();
      showToast(`📂 已加载 ${{result.selected.length}} 个选中项`);
    }} else {{
      showToast('⚠️ 暂无保存记录', true);
    }}
  }} catch(e) {{
    showToast('❌ 加载失败: ' + e.message, true);
  }}
}}

// 初始化
initCatFilters();
renderApps();
</script>
</body>
</html>'''


class Handler(BaseHTTPRequestHandler):
    apps_cache = None

    def log_message(self, format, *args):
        pass  # 关闭默认日志

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            if Handler.apps_cache is None:
                print('正在解析规则文件…')
                Handler.apps_cache = load_all_apps()
                print(f'共加载 {len(Handler.apps_cache)} 个 APP 规则')
            html = build_html(Handler.apps_cache).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html))
            self.end_headers()
            self.wfile.write(html)

        elif self.path == '/load':
            if os.path.exists(OUTPUT_FILE):
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_json({'ok': True, 'selected': data.get('selected', [])})
            else:
                self.send_json({'ok': False})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode('utf-8'))
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f'[保存] 已选 {len(data.get("selected", []))} 个APP → {OUTPUT_FILE}')
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()


def main():
    import sys
    port = 8765
    server = HTTPServer(('0.0.0.0', port), Handler)
    url = f'http://127.0.0.1:{port}'
    sys.stdout.write(f'\nGKD 规则选择器已启动\n')
    sys.stdout.write(f'访问地址: {url}\n')
    sys.stdout.write(f'结果文件: {OUTPUT_FILE}\n')
    sys.stdout.write(f'按 Ctrl+C 停止服务\n\n')
    sys.stdout.flush()

    def open_browser():
        import time
        time.sleep(0.8)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止。')


if __name__ == '__main__':
    main()
