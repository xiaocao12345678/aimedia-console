# AI 多模态控制台 · Android 版

手机 / 平板上用的版本。调的还是那六家国内平台（火山方舟、阿里百炼、腾讯混元、智谱 GLM、百度千帆、MiniMax），
图像理解 / 生图 / 视频 / 视频编辑四种能力全在。

## 和桌面版的关系

核心调用逻辑**是同一份代码**，不是重写：

```
android/core/
  providers.py     ← 与桌面版逐字相同：模型清单、能力分派
  adapters.py      ← 与桌面版逐字相同：六家平台的请求契约
  net.py           ← 与桌面版逐字相同：请求、脱敏日志、轮询、下载
  media.py         ← 与桌面版逐字相同：素材转 URL/base64、方舟 Files API 上传
  analysis.py      ← 与桌面版逐字相同：工作流提示词解析
  error_hint.py    ← 与桌面版逐字相同：错误码 → 下一步该干什么
  providers_util.py← 与桌面版逐字相同
  paths.py         ← 重写：Android 目录规则
  config.py        ← 改了两行：Key / 配置存放位置
  runner.py        ← 重写：PyQt 的 QThread+信号 → threading+回调
```

界面（Kivy）是新的，桌面版的 PyQt6 界面无法在 Android 上运行。

## 界面

    顶栏      AI 多模态控制台 · [密钥] [日志]
    内容区    四个页签，每页自带「平台 ▾ + 模型 ▾」两列下拉
    状态栏    当前进度 / 错误提示（3 秒后回"就绪"）
    底栏      理解 | 生图 | 视频 | 改视频

- **理解**：选图（最多 4 张）+ 提问 → 结果可长按复制
- **生图**：提示词 + 尺寸 + 张数，可选参考图（有则图生图），结果九宫格缩略图，点开看大图
- **视频**：提示词 + 可选首帧图 + 尺寸 + 时长
- **改视频**：参考视频（本地或公网 URL）+ 参考图（≤3）+ 指令 + 分辨率/时长；平台只列三家（火山 / 百炼 / MiniMax）
- **密钥**：六家各一行，密码框 + 保存 + 打开控制台；带「获取 Key」和「模型开通」说明
- **日志**：滚动查看全部请求与错误，可清空 / 复制

## 文件放在哪

| 内容 | Android 路径 |
|---|---|
| 生成的图片、视频 | `/sdcard/Download/AI多模态控制台/` |
| 配置与 Key | 应用私有目录（`/data/user/0/org.aimedia.aimedia/files/`） |
| 运行日志 | 应用私有目录 `logs/app_YYYYMMDD.log` |

写 `/sdcard/Download` 需要 **MANAGE_EXTERNAL_STORAGE**（Android 11+ 叫「所有文件访问」）。
首次启动会跳系统设置页让你授权；不给也能用，只是产物会落到应用私有目录，相册里看不到。

## 字体

Kivy 自带字体没有中文，不处理就是一片方块。程序按顺序找：

1. `assets/NotoSansCJKsc-Regular.otf`（打包内置，16.4 MB，SIL OFL 许可，从 Ubuntu 的 fonts-noto-cjk 提取的 SC 字面）
2. Android 系统字体：`/system/fonts/NotoSansCJK-Regular.ttc`、`MiSans-Regular.ttf`、`OPPOSans-Regular.ttf` 等
3. 桌面调试时回退到 `C:/Windows/Fonts/msyh.ttc`（**不进 APK**）

启动日志第一行会写实际用了哪个字体，字体有问题看那里。

## 构建（Windows + WSL）

前提：WSL2 Ubuntu 24.04（已装好 JDK 17、buildozer 1.6.0、fonts-noto-cjk）。

```bash
# 一次配好环境（换阿里云源、装 JDK/构建工具/字体/buildozer）
bash android/setup_wsl2.sh

# 构建（会 rsync 到 /root/build_apk 再打包；首次要下 Android SDK/NDK）
bash android/build_apk.sh
```

产物：`/root/build_apk/bin/*.apk`，复制回 Windows：

```bash
cp /root/build_apk/bin/*.apk /mnt/d/项目/AI多模态控制台/android/bin/
```

### 构建时踩过的坑（都在脚本里处理了）

| 现象 | 原因 | 处理 |
|---|---|---|
| `apt-get install` 403 Forbidden | 清华源挡住了代理出口 IP | 换阿里云源（`setup_wsl2.sh`） |
| p4a clone 龟速 / 502 | GitHub 直连不稳 | 从 PyPI 下 sdist + git insteadOf 重写到本地仓库（`fix_p4a_final.sh`） |
| `git config --get remote.origin.url` 失败 | PyPI 包没有 .git | 在 p4a 目录 `git init` + commit + `remote.origin.url` 保持官方 URL（靠 insteadOf 重定向） |
| `error: externally-managed-environment` | Ubuntu 24.04 的 PEP 668 | `PIP_BREAK_SYSTEM_PACKAGES=1` |
| buildozer 在 root 下要交互确认 | `warn_on_root` | spec 里设 `warn_on_root = 0` |

## 还没验证的

- **真机运行**：本机没有连 Android 设备，APK 只验证到「构建成功 + 文件结构正确」。真机装上去若要调，主要会出在文件选择权限和软键盘遮挡上。
- **视频内嵌播放**：现在生成完只给路径，让系统相册/文件管理器打开（Android 7+ 的 `file://` 需要 FileProvider，绕开更稳）。
- **平板/横屏**：布局按竖屏设计，横屏需要再调一轮。
