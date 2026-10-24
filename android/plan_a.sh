#!/bin/bash
# A 方案：精确改 p4a 的 pythonpackage.py 两处
#   ① 临时 venv 里 pip install -U pip wheel 时，顺带装 cython（走阿里云镜像）
#   ② pip download 加 --no-build-isolation，直接用 venv 里的 cython
set -uo pipefail

P="/root/p4a_src/pythonforandroid/pythonpackage.py"
[ -f "$P.bak" ] && cp -f "$P.bak" "$P"   # 先回到干净版本
cp -f "$P" "$P.beforeA"

python3 - "$P" <<'PY'
import ast, io, sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8").read()
lines = src.splitlines(True)
done = {"cython": False, "noiso": False}

for i, line in enumerate(lines):
    stripped = line.strip()
    indent = line[: len(line) - len(line.lstrip())]

    # ① 在 venv 里装 cython（原来只装 pip wheel）
    if stripped == '"install", "-U", "pip", "wheel",':
        extra = (
            f'{indent}"install", "-U", "pip", "wheel", "cython<4",\n'
            f'{indent}"--index-url", "https://mirrors.aliyun.com/pypi/simple/",\n'
            f'{indent}"--trusted-host", "mirrors.aliyun.com",\n'
        )
        lines[i] = extra
        done["cython"] = True
        continue

    # ② pip download 关掉 build isolation
    if stripped == '"download", "--no-deps", "-r", "../requirements.txt",':
        extra = (
            f'{indent}"download", "--no-deps", "--no-build-isolation",\n'
            f'{indent}"--index-url", "https://mirrors.aliyun.com/pypi/simple/",\n'
            f'{indent}"--trusted-host", "mirrors.aliyun.com",\n'
            f'{indent}"-r", "../requirements.txt",\n'
        )
        lines[i] = extra
        done["noiso"] = True
        continue

new = "".join(lines)
print("① cython 补丁:", done["cython"])
print("② no-build-isolation 补丁:", done["noiso"])
if not (done["cython"] and done["noiso"]):
    print("!! 有补丁没匹配上，放弃修改")
    sys.exit(1)

ast.parse(new)          # 语法自检
io.open(p, "w", encoding="utf-8").write(new)
print("语法 OK，已写入")
PY

[ $? -ne 0 ] && { echo "补丁失败，恢复原文件"; cp -f "$P.beforeA" "$P"; exit 1; }

echo "=== 改动确认 ==="
grep -n -A3 '"install", "-U", "pip"' "$P" | head -6
grep -n -A4 '"download", "--no-deps"' "$P" | head -8

echo "=== 重跑构建 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
