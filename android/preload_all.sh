#!/bin/bash
# p4a 的下载逻辑：packages/<recipe>/<file> 存在 且 packages/<recipe>/.mark-<file> 存在 才跳过下载。
# 所以预置包必须同时写 .mark，否则会被 rm 掉重下（之前就栽在这）。
set -uo pipefail

python3 - <<'PY'
import os, re, subprocess, urllib.parse

RECIPES = "/root/p4a_src/pythonforandroid/recipes"
PKG = "/root/.local/share/python-for-android/packages"
ORDER = ["hostpython3", "libffi", "openssl", "sdl2_image", "sdl2_mixer",
         "sdl2_ttf", "sqlite3", "python3", "sdl2", "pyjnius", "kivy"]

# gitee 镜像（国内 2MB/s 左右），仓库名按 p4a 里的上游名猜
GITEE = {
    "cpython": "cpython", "libffi": "libffi", "kivy": "kivy",
    "pyjnius": "pyjnius", "SDL": "SDL", "sqlite": "sqlite",
}


def recipe_info(name):
    p = os.path.join(RECIPES, name, "__init__.py")
    if not os.path.isfile(p):
        return None
    txt = open(p, encoding="utf-8", errors="ignore").read()
    ver = None
    for pat in (r"^\s*version\s*=\s*['\"]([^'\"]+)['\"]", r"^\s*version\s*=\s*\(\s*['\"]([^'\"]+)['\"]"):
        m = re.search(pat, txt, re.M)
        if m:
            ver = m.group(1)
            break
    url = None
    m = re.search(r"^\s*url\s*=\s*['\"]([^'\"]+)['\"]", txt, re.M)
    if m:
        url = m.group(1)
    if not url or not ver:
        return None
    url = url.replace("{version}", ver)
    fname = urllib.parse.urlparse(url).path.split("/")[-1]
    return ver, url, fname


def try_download(url, dest, timeout=600):
    r = subprocess.run(["curl", "-fsSL", "--max-time", str(timeout), "-o", dest, url],
                       capture_output=True)
    if r.returncode != 0 or not os.path.exists(dest):
        return False
    size = os.path.getsize(dest)
    if size < 50_000:      # 太小基本是错误页
        os.remove(dest)
        return False
    return size


def gitee_mirror(url, ver):
    """把 github 的 archive / releases 地址映射到 gitee 镜像。"""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/(?:archive(?:/refs/tags)?/(.+?)\.(tar\.gz|zip)|releases/download/[^/]+/(.+))$", url)
    if not m:
        return None
    org, repo, tag, ext, rel = m.groups()
    gname = GITEE.get(repo) or GITEE.get(org)
    if not gname:
        return None
    if tag:
        return f"https://gitee.com/mirrors/{gname}/repository/archive/{tag}.{ext}"
    return None


print(f"{'recipe':14s} {'文件':38s} {'来源':10s} 大小")
print("-" * 78)

ok, fail = [], []
for name in ORDER:
    info = recipe_info(name)
    if not info:
        print(f"{name:14s} (recipe 里没有 url/version，跳过)")
        continue
    ver, url, fname = info
    d = os.path.join(PKG, name)
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, fname)
    mark = os.path.join(d, f".mark-{fname}")

    # 已就位就跳过
    if os.path.exists(target) and os.path.getsize(target) > 50_000 and os.path.exists(mark):
        print(f"{name:14s} {fname:38s} {'已有':10s} {os.path.getsize(target)//1024} KB")
        ok.append(name)
        continue

    cands = []
    gm = gitee_mirror(url, ver)
    if gm:
        cands.append(("gitee", gm))
    # 非 GitHub 的官方源国内也慢（openssl.org 实测 0），优先国内镜像
    if "openssl.org" in url:
        cands.append(("清华",
                      url.replace("https://www.openssl.org/source/",
                                  "https://mirrors.tuna.tsinghua.edu.cn/openssl/source/")))
    cands.append(("官方", url))

    done = None
    for label, u in cands:
        try:
            sz = try_download(u, target)
            if sz:
                done = (label, sz)
                break
        except Exception:
            pass
    if done:
        open(mark, "w").write(url)
        print(f"{name:14s} {fname:38s} {done[0]:10s} {done[1]//1024} KB")
        ok.append(name)
    else:
        print(f"{name:14s} {fname:38s} {'失败':10s}")
        for f in (target,):
            if os.path.exists(f):
                os.remove(f)
        fail.append(name)

print()
print(f"就绪 {len(ok)} 个：{', '.join(ok)}")
if fail:
    print(f"失败 {len(fail)} 个：{', '.join(fail)}")
PY
