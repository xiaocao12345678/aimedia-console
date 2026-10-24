@echo off
chcp 65001 >nul
REM ============================================================
REM  AI 多模态控制台 · 一键打包（onedir，启动快）
REM  用法：双击本文件，等它跑完；产物在 dist\AI多模态控制台\
REM ============================================================
setlocal

set PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if not exist "%PY%" (
    echo [错误] 没找到 Python 3.11：%PY%
    echo 请先安装 Python 3.11，或修改本文件里的 PY 路径。
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/4] 生成图标...
"%PY%" make_icon.py || goto :fail

echo [2/4] 清理旧的 build / dist...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/4] 打包（onedir）...
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed ^
  --name "AI多模态控制台" --icon "assets\app.ico" ^
  --add-data "assets;assets" ^
  --hidden-import PyQt6.QtNetwork ^
  --exclude-module tkinter --exclude-module numpy --exclude-module matplotlib ^
  --exclude-module pandas --exclude-module scipy --exclude-module pytest ^
  --exclude-module PyQt6.QtWebEngineCore --exclude-module PyQt6.QtWebEngineWidgets ^
  --exclude-module PyQt6.QtWebEngineQuick --exclude-module PyQt6.QtQuick ^
  --exclude-module PyQt6.QtQml --exclude-module PyQt6.QtQuickWidgets ^
  --exclude-module PyQt6.QtMultimedia --exclude-module PyQt6.QtMultimediaWidgets ^
  --exclude-module PyQt6.QtSpatialAudio --exclude-module PyQt6.Qt3DCore ^
  --exclude-module PyQt6.QtBluetooth --exclude-module PyQt6.QtCharts ^
  --exclude-module PyQt6.QtDataVisualization --exclude-module PyQt6.QtDesigner ^
  --exclude-module PyQt6.QtHelp --exclude-module PyQt6.QtLocation ^
  --exclude-module PyQt6.QtNfc --exclude-module PyQt6.QtPdf ^
  --exclude-module PyQt6.QtPdfWidgets --exclude-module PyQt6.QtPositioning ^
  --exclude-module PyQt6.QtRemoteObjects --exclude-module PyQt6.QtSensors ^
  --exclude-module PyQt6.QtSerialPort --exclude-module PyQt6.QtSql ^
  --exclude-module PyQt6.QtStateMachine --exclude-module PyQt6.QtTest ^
  --exclude-module PyQt6.QtTextToSpeech --exclude-module PyQt6.QtWebChannel ^
  --exclude-module PyQt6.QtWebSockets ^
  app.py
if errorlevel 1 goto :fail

echo [4/4] 复制配置与说明...
set OUT=dist\AI多模态控制台
if exist "%APPDATA%\AI多模态控制台\config.json" (
    copy /y "%APPDATA%\AI多模态控制台\config.json" "%OUT%\config.json" >nul
    echo     已带入现有配置（六家平台的 Key）
) else (
    echo     [提示] 没有找到现有配置，首次运行请在「平台密钥」里填写
)
if exist "使用说明.txt" copy /y "使用说明.txt" "%OUT%\使用说明.txt" >nul

echo.
echo ============ 打包完成 ============
echo 产物目录：%CD%\%OUT%
echo 启动方式：双击 %OUT%\AI多模态控制台.exe
echo.
dir /b "%OUT%"
echo.
pause
exit /b 0

:fail
echo.
echo [失败] 打包过程出错，上面的日志里有原因。
pause
exit /b 1
