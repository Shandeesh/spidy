# -*- mode: python ; coding: utf-8 -*-
import sys
sys.setrecursionlimit(5000)

block_cipher = None

# Add static directories and config directories
added_files = [
    ('Trading_Backend', 'Trading_Backend'),
    ('AI_Engine', 'AI_Engine'),
    ('Shared_Data', 'Shared_Data'),
    ('Frontend_Dashboard/dashboard_app/out', 'Frontend_Dashboard/dashboard_app/out'),
]

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'Trading_Backend.mt5_bridge.bridge_server',
    'AI_Engine.brain.brain_server',
    'sentiment_analyzer',
    'google.generativeai',
    'langchain_openai',
    'langchain_core.prompts',
    'langchain_core.output_parsers',
    'MetaTrader5',
    'webview',
    'winreg',
    'dotenv',
]

import os
BASE_DIR = os.path.dirname(os.path.abspath('spidy_desktop.py'))

a = Analysis(
    ['spidy_desktop.py'],
    pathex=[
        os.path.join(BASE_DIR, 'AI_Engine'),
        os.path.join(BASE_DIR, 'Trading_Backend'),
        os.path.join(BASE_DIR, 'Trading_Backend/mt5_bridge'),
    ],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Set console=False to hide the background terminal since we have a webview GUI
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Spidy',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Spidy',
)
