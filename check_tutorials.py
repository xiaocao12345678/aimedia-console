
import sys
sys.path.insert(0, ".")
from ui.key_manager import ROWS, TUTORIALS
import subprocess

print("平台覆盖:", [r[0] for r in ROWS] == list(TUTORIALS.keys()) or (set(r[0] for r in ROWS) == set(TUTORIALS)))
for p, hint, console in ROWS:
    t = TUTORIALS[p]
    print(f"{p:<8} steps={len(t['steps'])} tips={len(t['tips'])} docs={t['docs']}")
urls = []
for p, t in TUTORIALS.items():
    urls += [(p, "docs", t["docs"]), (p, "console", t["console"])]
for p, kind, u in urls:
    r = subprocess.run(["curl","-s","-o","/dev/null","-L","--max-time","20",
                        "-A","Mozilla/5.0 Chrome/130","-w","%{http_code}",u], capture_output=True, text=True)
    print(f"  {r.stdout}  {p} {kind}  {u}")
