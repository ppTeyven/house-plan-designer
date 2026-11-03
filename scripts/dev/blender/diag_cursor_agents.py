"""在 Cursor 状态库副本中查找【残留后台 Agent】的记录。

【目的】
用户投诉 UI 里的多 Agent 面板关不掉（点了 Stop All 没反应）。
已确认那两个 Agent 【进程数为 0】，是 UI 僵尸条目。
本脚本只读副本，找出 Cursor 把 Agent 状态存在哪个 key，
以便判断是否有办法在不改 Cursor 内部状态的前提下清掉。

注意：只读副本，绝不写回原库。
"""
import sqlite3
import shutil
import tempfile
import os
import json

src = r"C:\Users\zzkkg\AppData\Roaming\Cursor\User\globalStorage\state.vscdb"
tmp = os.path.join(tempfile.gettempdir(), "vsdb_copy.sqlite")
for ext in ("", "-wal", "-shm"):
    if os.path.exists(src + ext):
        shutil.copy(src + ext, tmp + ext)

c = sqlite3.connect(tmp)
cur = c.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("TABLES:", [r[0] for r in cur.fetchall()])

NEEDLES = ["stretch fix", "1-frame stretch", "Continue 2D-3D"]

for t in ("ItemTable",):
    try:
        cur.execute("SELECT key, length(value) FROM %s" % t)
        rows = cur.fetchall()
        print("\n%s total rows: %d" % (t, len(rows)))
        for k, ln in rows:
            if any(n.lower() in k.lower() for n in NEEDLES):
                print("  KEY MATCH:", k, "len", ln)
        # 再按 value 内容搜
        print("\n--- 按 value 搜索 ---")
        cur.execute("SELECT key, value FROM %s" % t)
        hits = 0
        for k, v in cur.fetchall():
            if not v:
                continue
            s = v if isinstance(v, str) else str(v)
            if any(n in s for n in NEEDLES):
                print("  VAL MATCH key=", k, "len", len(s))
                hits += 1
                if hits > 10:
                    break
        if not hits:
            print("  (无)")
    except Exception as e:
        print("ERR", t, e)

# 也扫 workspaceStorage 里每个库的 ItemTable
ws = r"C:\Users\zzkkg\AppData\Roaming\Cursor\User\workspaceStorage"
print("\n=== workspaceStorage ===")
for d in sorted(os.listdir(ws)):
    p = os.path.join(ws, d, "state.vscdb")
    if not os.path.exists(p):
        continue
    try:
        c2 = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
        cu2 = c2.cursor()
        cu2.execute("SELECT key, value FROM ItemTable")
        for k, v in cu2.fetchall():
            if not v:
                continue
            s = v if isinstance(v, str) else str(v)
            if any(n in s for n in NEEDLES):
                print("  [%s] key=%s len=%d" % (d[:8], k, len(s)))
        c2.close()
    except Exception as e:
        print("  [%s] ERR %s" % (d[:8], e))

c.close()
print("\nDONE")
