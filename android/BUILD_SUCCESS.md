# APK 构建成功记录

## 结论

APK 已通过 GitHub Actions 云端构建产出，本地 WSL + p4a 那条路已放弃（不可行）。

| 项 | 值 |
|---|---|
| APK 文件 | `android/bin/AI多模态控制台-debug-arm64.apk` |
| 大小 | 30,152,214 字节（28.8 MB） |
| SHA-256 | `eb2e8b3d9ef69924c61d57e42c8b9befabf13f33bf35bfd03ad8ac5bf90a50a2` |
| 包名 | `org.aimedia.aimedia` |
| 架构 | arm64-v8a |
| 最低版本 | Android 5.0（API 21） |
| Python | 3.10（p4a 2023.9.16 自带） |
| 签名 | debug |
| 构建 run | `40088659520`（success，BUILD SUCCESSFUL in 1m 3s） |
| 仓库 | https://github.com/xiaocao12345678/aimedia-console （私有） |

APK 内已核验：`lib/arm64-v8a/libpython3.10.so`、`classes.dex`、`assets/private.tar`
（82 个文件，含 `assets/NotoSansCJKsc-Regular.otf` 与全部 `core/*.pyc`）。

## 可用的构建参数

```bash
p4a apk \
  --private . \
  --package org.aimedia.aimedia \
  --name "AI多模态控制台" \
  --version 1.0.0 \
  --requirements "python3,kivy,requests,urllib3,certifi,idna,charset-normalizer,pyjnius" \
  --android-api 31 \
  --minsdk 21 \
  --arch arm64-v8a \
  --bootstrap sdl2 \
  --ndk-dir "$ANDROID_HOME/ndk/25.2.9519653" \
  --sdk-dir "$ANDROID_HOME" \
  --permission INTERNET \
  --permission MANAGE_EXTERNAL_STORAGE \
  --permission READ_EXTERNAL_STORAGE \
  --permission WRITE_EXTERNAL_STORAGE \
  --permission READ_MEDIA_IMAGES \
  --permission READ_MEDIA_VIDEO \
  --debug
```

工具链：`python-for-android==2023.9.16` + `cython<3` + Python 3.11（宿主）+ NDK 25b + API 31。

## 六个必须遵守的约束（踩过的坑）

1. **runner 没有 API 31** —— 必须 `sdkmanager "platforms;android-31"` 先装，否则
   `Requested API target 31 is not available`。
2. **不能用 `p4a ... | tee`** —— 管道退出码取自 tee，失败也显示 success。必须 `set -o pipefail`。
3. **NDK 必须 25b，不能用 runner 默认的 27** —— NDK 27 移除了 `ALooper_pollAll`，
   SDL2 老版本编译失败：`'ALooper_pollAll' is unavailable`。
4. **必须显式 `--bootstrap sdl2`** —— 否则生成 APK 阶段报 `TypeError: None is not allowed for bootstrap`
   （此时 dist 已建好，只有最后一步挂）。
5. **参数名是 `--minsdk`，不是 `--min-api`** —— 后者报 `unrecognized arguments`。
6. **`--minsdk` 必须等于 NDK 编译目标（21）** —— 传 24 会报
   `--minsdk argument does not match the api that is compiled against`。

## 重新出包

改完代码 push 到 main（且改动落在 `android/**`），Actions 自动构建；
或在 Actions 页面手动 `Run workflow`。产物在 run 页面底部 Artifacts → `aimedia-debug-apk.zip`。

国内网络下载 artifact 约 20–30 KB/s，28.9 MB 需要十来分钟，用 `curl -C -` 断点续传更稳。

## 首次安装后

进「密钥」页重新填六家平台 Key —— APK 不含 `config.json`（`.gitignore` 已排除）。
