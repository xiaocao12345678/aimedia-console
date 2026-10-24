#!/bin/bash
# 真正根因：p4a 给某些包用内联 setup.py 构建 wheel（File "<string>", line 2 就是它），
# pip 默认开 build isolation，隔离环境里没有 Cython 就失败。
# 处理：① 给 hostpython 装 Cython ② 给 p4a 的每一条 pip 命令加 --no-build-isolation。
set -uo pipefail

NB="/root/.local/share/python-for-android/build/other_builds/hostpython3/desktop/hostpython3/native-build"
SP="$NB/root/usr/local/lib/python3.14/site-packages"

echo "=== 1. hostpython 就位检查 ==="
HPY=""
for c in "$NB/root/usr/local/bin/python3" "$NB/root/usr/local/bin/python3.14" "$NB/python3"; do
  [ -x "$c" ] && { HPY="$c"; break; }
done
echo "hostpython = ${HPY:-未找到}"
if [ -n "${HPY:-}" ]; then
  "$HPY" -V 2>&1 | head -1
  # 修坏掉的 pip：清掉再 ensurepip
  rm -rf "$SP"/pip "$SP"/pip-*.dist-info 2>/dev/null || true
  "$HPY" -m ensurepip --upgrade --default-pip >/dev/null 2>&1 || true
  "$HPY" -m pip --version 2>&1 | tail -1
  "$HPY" -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ \
      --trusted-host mirrors.aliyun.com "cython>=0.29.34,<4" 2>&1 | tail -2
  "$HPY" -c "import Cython; print('hostpython Cython', Cython.__version__)" 2>&1 | tail -1
fi

echo "=== 2. 给 p4a 的 pip 调用加 --no-build-isolation ==="
for f in /root/p4a_src/pythonforandroid/pythonpackage.py /root/p4a_src/pythonforandroid/build.py /root/p4a_src/pythonforandroid/recipe.py; do
  [ -f "$f" ] || continue
  cp "$f" "$f.bak" 2>/dev/null || true
  # 在 pip install / pip wheel 命令里补 --no-build-isolation（幂等）
  python3 - "$f" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
orig = s
# pip 调用形如 ("install", "-U", ...) 或 ["install", ...]
s = re.sub(r'("install",\s*\n?\s*"-U",)', r'\1\n                    "--no-build-isolation",', s)
s = re.sub(r'(\[?"wheel",)', r'\1\n                    "--no-build-isolation",', s) if 'wheel",' in s else s
if s != orig:
    open(p, "w", encoding="utf-8").write(s)
    print(f"  补丁写入 {p}")
else:
    print(f"  无需改动 {p}")
PY
done

grep -rn "no-build-isolation" /root/p4a_src/pythonforandroid/*.py 2>/dev/null | head -5

echo "=== 3. 重跑构建 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
export PIP_NO_BUILD_ISOLATION=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
