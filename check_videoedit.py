import sys
sys.path.insert(0, ".")
from core import providers
print("支持视频编辑的平台:", providers.platforms_for("video_edit"))
for p in providers.platforms_for("video_edit"):
    print(f"  {p}: {[m for m,_ in providers.models_for(p,'video_edit')]}")
print()
print("各能力平台数:", {c: len(providers.platforms_for(c)) for c in ("understand","image","video","video_edit")})
