
import sys, re
sys.path.insert(0, ".")
from ui.key_manager import ROWS, TUTORIALS

row = [r for r in ROWS if r[0] == "阿里百炼"][0]
print("密钥行控制台:", row[2])
t = TUTORIALS["阿里百炼"]
print("教程 console:", t["console"])
print("教程 docs   :", t["docs"])
print("步骤数:", len(t["steps"]), "提示数:", len(t["tips"]))
for i, s in enumerate(t["steps"], 1):
    links = re.findall(r'href="([^"]+)"', s)
    print(f"  {i}. {s[:60]}{'...' if len(s)>60 else ''}")
    for l in links:
        print("     链接:", l)
