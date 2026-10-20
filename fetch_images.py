#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 image_manifest.json 把 wiki 图片下载到本地 images/（离线查看用）。
   限速 + 429 退避重试，可断点续传（跳过已存在的有效图片）。"""
import json, os, sys, time, urllib.parse, subprocess, threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "raw", "image_manifest.json")
UA = "IsaacDataCollector/1.0 (personal data archive; contact: local user)"
API = "https://bindingofisaacrebirth.wiki.gg/wiki/Special:FilePath/"

manifest = json.load(open(MANIFEST, encoding="utf-8"))

# 下载优先级：饰品/卡牌优先（识别需要），道具次之，其余最后
PRIORITY = ["trinket", "pickup", "collectible", "player", "transformation", "pool", "stage", "entity"]
def prio(item):
    rel = item[0]
    cat = rel.split("/")[1] if "/" in rel else ""
    return PRIORITY.index(cat) if cat in PRIORITY else 99

only = None
for i, a in enumerate(sys.argv):
    if a == "--only" and i + 1 < len(sys.argv):
        only = [x.strip() for x in sys.argv[i + 1].split(",")]

jobs = list(manifest.items())
if only:
    jobs = [(rel, fn) for rel, fn in jobs if any(f"/{c}/" in rel for c in only)]
jobs.sort(key=prio)

MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8")


def valid(p):
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return False
    with open(p, "rb") as f:
        h = f.read(8)
    return any(h.startswith(m) for m in MAGIC)


# 只下载缺失的
todo = []
for rel, fn in jobs:
    if not valid(os.path.join(ROOT, rel)):
        todo.append((rel, fn))
print(f"共 {len(jobs)} 张，需下载 {len(todo)} 张", flush=True)

# 全局限速：控制请求启动间隔
lock = threading.Lock()
last = [0.0]
MIN_INTERVAL = 0.45


def throttle():
    with lock:
        now = time.time()
        wait = last[0] + MIN_INTERVAL - now
        if wait > 0:
            time.sleep(wait)
        last[0] = time.time()


def fetch(item):
    rel, fn = item
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    url = API + urllib.parse.quote(fn.replace(" ", "_"))
    for attempt in range(6):
        throttle()
        r = subprocess.run(
            ["curl", "-sSL", "--max-time", "45", "-H", f"User-Agent: {UA}",
             "-o", p, "-w", "%{http_code}", url],
            capture_output=True, text=True)
        code = (r.stdout or "").strip()[-3:]
        if code == "200" and valid(p):
            return 1
        if code == "429" or code.startswith("5"):
            time.sleep(8 * (attempt + 1))     # 退避
            continue
        # 其它错误：稍等再试
        time.sleep(2)
    try:
        if os.path.exists(p):
            os.remove(p)
    except OSError:
        pass
    return 0


ok = 0
with ThreadPoolExecutor(max_workers=2) as ex:
    for n, res in enumerate(ex.map(fetch, todo), 1):
        ok += res
        if n % 25 == 0 or n == len(todo):
            print(f"  进度 {n}/{len(todo)}（成功 {ok}）", flush=True)

print(f"完成：成功 {ok} / {len(todo)}", flush=True)
tot = sum(os.path.getsize(os.path.join(d, f))
          for d, _, fs in os.walk(os.path.join(ROOT, "images")) for f in fs)
print(f"images/ 大小：{tot/1024/1024:.1f} MB", flush=True)
