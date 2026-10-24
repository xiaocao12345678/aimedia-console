#!/bin/bash
# 最后一块拼图：
#   p4a 把 'android' 当成纯 Python 包交给 pip 去 PyPI 找 wheel，但 android 是 p4a 自带 recipe
#   （setup.py 第 2 行 from Cython.Build import cythonize，还依赖 ANDROID_LIBS_DIR），
#   必须由 recipe 交叉编译，不该走 pip。
# 处理：在收集 python_modules 时把 'android' 剔除，让它走 recipe 的 build_arch。
set -uo pipefail

B="/root/p4a_src/pythonforandroid/build.py"
cp -f "$B" "$B.bak_android"

python3 - "$B" <<'PY'
import ast, io, sys

p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()

if "AI_MEDIA_SKIP_ANDROID" in s:
    print("补丁已存在")
    raise SystemExit(0)

anchor = "    try:\n        shprint(\n            pip, 'install', '--no-build-isolation', *modules,"
if anchor not in s:
    print("!! 找不到 anchor，尝试宽松匹配")
    anchor = "    try:\n        shprint(\n            pip, 'install', *modules,"
    if anchor not in s:
        print("!! 仍然找不到，放弃")
        raise SystemExit(1)

patch = '''    # AI_MEDIA_SKIP_ANDROID: 'android' 是 p4a 自带 recipe（需要交叉编译 + ANDROID_LIBS_DIR），
    # 不是 PyPI 上的纯 Python 包，交给 pip 会报 No matching distribution found。
    # 从 python_modules 里剔除，让它走 recipe 的 build_arch。
    if "android" in modules:
        modules = [m for m in modules if m != "android"]
        print("[ai-media] 跳过 pip 安装 'android'，改由 recipe 编译")

'''
s = s.replace(anchor, patch + anchor, 1)
ast.parse(s)
io.open(p, "w", encoding="utf-8").write(s)
print("补丁已插入 build.py")
PY

python3 -c "import ast;ast.parse(open('$B',encoding='utf-8').read());print('语法 OK')" || { cp -f "$B.bak_android" "$B"; echo "已回滚"; exit 1; }
grep -n -A3 "AI_MEDIA_SKIP_ANDROID" "$B" | head -8

echo "=== 重跑 ==="
export PIP_FIND_LINKS=/root/pipwheels
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
bash /root/run_full_build.sh > /root/full5.log 2>&1
echo "--- 结果 ---"
ls -lah /root/*.apk 2>/dev/null || echo "无 APK"
grep -E "Successfully built|Building android|No matching distribution|p4a 退出码|ModuleNotFound" /root/full5.log | tail -8
