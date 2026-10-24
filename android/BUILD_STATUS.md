# Android APK 构建状态（交接文档）

最后更新：2026-10-24 17:31 CST

## 结论

**APK 尚未产出。** 构建卡在 p4a 收集 Python 包元数据阶段的一个 Cython 依赖上。
界面、代码、构建环境、Python 3.12 交叉编译、pyjnius 编译**都已打通**。

## 已经打通的部分（都验证过）

| 环节 | 状态 | 说明 |
|---|---|---|
| Kivy 界面六页 | ✅ | 截图见 `logs/pv_*.png`，中文渲染/圆角/下拉都正常 |
| 核心逻辑复用 | ✅ | `core/providers.py` 等与桌面版逐字相同 |
| JDK / SDK / NDK | ✅ | JDK17 / SDK 458M（platform-34 + build-tools 34）/ NDK r25b 1.7G |
| gradle 8.14.3 | ✅ | 已放进 wrapper 缓存（hash 自己算的），maven 指阿里云 |
| 10 个 recipe 源码包 | ✅ | 走 PowerShell + 代理下完，已打 `.mark` |
| **Python 3.12.8 交叉编译** | ✅ | 关键突破：`grpmodule.c`/`pwdmodule.c` 用 8 个桩函数绕过 NDK 缺失的 libc 函数 |
| **pyjnius 1.7.0** | ✅ | 日志：`Successfully built pyjnius-1.7.0-cp312-cp312-android_24_arm64_v8a.whl` |
| kivy 2.3.1 / SDL2 / openssl / libffi / sqlite3 | ✅ | 编译产物在 `build/other_builds/` |

## 卡住的确切位置

```
Collecting setuptools
  → /tmp/build-env-<hash>/lib/python3.12/site-packages/setuptools/build_meta.py:333
    get_requires_for_build_wheel → run_setup → exec(code)
  → File "<string>", line 2
  → ModuleNotFoundError: No module named 'Cython'
```

含义：某个包的 sdist 在 pip 的隔离环境里执行 `setup.py`，而该 `setup.py` 第 2 行 import Cython；
隔离环境只装了 setuptools，没装 Cython。

## 已试过、无效的手段（别再重复）

| 手段 | 结果 |
|---|---|
| `export PIP_NO_BUILD_ISOLATION=1` | 无效 |
| `pythonpackage.py` 的 `pip download` 加 `--no-build-isolation` | 无效（改了，仍出新的 build-env） |
| `build.py:643` 的 `pip install` 加 `--no-build-isolation` | 无效 |
| `build.py:755` 的 `pip install --report` 加 `--no-build-isolation` | 无效 |
| 给 hostpython3 的 site-packages 装 cython | 装上了（有 `cython` 可执行），但不影响隔离环境 |
| 在 `entrypoints.py` 顶部 hook `subprocess.Popen`，给 pip 命令自动补参数 | 无效 |
| 把所有 Cython/setuptools/wheel 的 wheel 下到 `/root/pipwheels` 并设 `PIP_FIND_LINKS` | 无效 |
| 给 kivy/pyjnius 的 sdist 补 `pyproject.toml`（requires 含 cython） | **对 pyjnius 有效**（已编出 wheel），对当前失败点无效 |

## 下一个 Session 的第一步

在 `bash android/run_full_build.sh` 的完整日志里（重定向到文件）搜 `Collecting ` 与 `Building wheel for`：

```bash
bash /root/run_full_build.sh > /root/full4.log 2>&1
grep -nE "Collecting |Building wheel for|Processing " /root/full4.log | tail -20
```

拿到**具体包名**后，两种修法：

1. **预置该包的 wheel**：把它下到 `.buildozer`/`packages` 对应目录，让 pip 走 `--only-binary`，不进 sdist 构建；
2. **给该包 sdist 补 `pyproject.toml`**：`build-system.requires = ["setuptools>=61", "wheel", "cython>=0.29.34,<4"]`，
   这招对 pyjnius 已经验证有效。

备选路线：换更老的 p4a（2024 版，默认 Python 3.11 + Kivy 2.3.0），那套组合社区验证充分，
但要重新走一遍依赖下载（`packages/` 缓存可复用一部分）。

## 环境位置（都在 WSL Ubuntu-24.04 里，root 用户）

```
/root/p4a_src                  p4a 源码（pip install -e 安装，改这里生效）
/root/build_apk                app 源码副本（由 run_full_build.sh 的 rsync 生成）
/root/p4a_app                  p4a 使用的 --private 目录
/root/android_sdk              SDK
/root/android_ndk              NDK r25b
/root/pipwheels                预下载的 cython/setuptools/wheel
/root/.local/share/python-for-android/    p4a 的 build / packages / dists 缓存（2.5 G）
/root/.gradle/wrapper/dists    gradle 8.14.3
```

## 本项目内的脚本索引

| 脚本 | 用途 |
|---|---|
| `setup_wsl2.sh` | 换阿里云源 + JDK17 + buildozer + fonts-noto-cjk |
| `setup_sdk.sh` | 腾讯镜像装 SDK / platform-34 / build-tools / NDK |
| `preload_all.sh` | 从 recipe 提取包清单并预下载 + 打 `.mark` |
| `fetch_pkgs.ps1` | Windows 侧走代理下载全部源码包（PowerShell，curl 会 error 23） |
| `distribute_pkgs.sh` | 把包分发进 p4a 缓存并打 mark |
| `disable_jxl.sh` / `stub_jxl*.sh` | SDL2_image 关掉 JXL/AVIF + 8 个桩函数 |
| `plan_b.sh` | Python 3.14 → 3.12.8 |
| `plan_b5_stub.sh` | grpmodule/pwdmodule 桩（monkey patch `apply_patches`） |
| `pip_hook.sh` / `run_full_build.sh` | 最后一轮：pip hook + 完整构建 |

## 桌面版（完好的保底交付）

```
D:\项目\AI多模态控制台\dist\AI多模态控制台\AI多模态控制台.exe
3,178,115 字节 · SHA-256 47c1ea452e381f7183fc13c078ba799c51f8fccd3e046adf8228ac827560caa2
五家平台 Key 已内置，冷启动约 1 秒
```
