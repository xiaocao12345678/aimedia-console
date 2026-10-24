# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['PyQt6.QtNetwork'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'numpy', 'matplotlib', 'pandas', 'scipy', 'pytest', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineQuick', 'PyQt6.QtQuick', 'PyQt6.QtQml', 'PyQt6.QtQuickWidgets', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets', 'PyQt6.QtSpatialAudio', 'PyQt6.Qt3DCore', 'PyQt6.QtBluetooth', 'PyQt6.QtCharts', 'PyQt6.QtDataVisualization', 'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtLocation', 'PyQt6.QtNfc', 'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets', 'PyQt6.QtPositioning', 'PyQt6.QtRemoteObjects', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtSql', 'PyQt6.QtStateMachine', 'PyQt6.QtTest', 'PyQt6.QtTextToSpeech', 'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI多模态控制台',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI多模态控制台',
)
