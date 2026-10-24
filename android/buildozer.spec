[app]
# 应用名（会显示在桌面图标下面和任务管理器里）
title = AI多模态控制台
package.name = aimedia
package.domain = org.aimedia

source.dir = .
source.include_exts = py,png,jpg,jpeg,otf,ttf,atlas,kv,json,txt
source.exclude_dirs = logs,buildozer_build,__pycache__,bin
source.exclude_patterns = *.pyc,*.bak

version = 1.0.0

# python3 + kivy 必备；requests 及其依赖显式写全，避免 p4a 解析漏掉
requirements = python3,kivy==2.3.1,requests,urllib3,certifi,idna,charset-normalizer,plyer,pyjnius

# 竖屏，全屏关掉（保留状态栏，软键盘才能正常顶起）
orientation = portrait
fullscreen = 0

# Android 权限：联网 + 读写外部存储（产物放 /sdcard/Download/AI多模态控制台）
android.permissions = INTERNET,MANAGE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO

# targetSdk 34（Android 14 要求），minSdk 24 覆盖到 Android 7
android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

# 图标（512×512 PNG，放在 assets 下）
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/icon.png

# 主题与元信息
android.meta_data = 
android.app_version = 1.0.0

[buildozer]
log_level = 2
warn_on_root = 0
