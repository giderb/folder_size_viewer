# build.spec
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],          # project root on sys.path → 'from src.X import Y' works
    binaries=[],
    datas=[
        ('src/fonts', 'fonts'),   # → _MEIPASS/fonts/  (matches frozen-mode fix in styles.py)
        ('src/icon.png', '.'),    # → _MEIPASS/icon.png
    ],
    hiddenimports=[
        # PyQt6 internals
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # pywin32 (optional but should be bundled; metadata.py guards with try/except)
        'win32security',
        'win32api',
        'win32con',
        'win32timezone',
        'pywintypes',
        # All src submodules (ensures nothing is missed)
        'src.models',
        'src.scanner',
        'src.treemap',
        'src.treemap_widget',
        'src.sidebar',
        'src.toolbar_widget',
        'src.styles',
        'src.metadata',
        'src.main_window',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pytest_cov', '_pytest', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FolderSizeViewer',
    icon='src/icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,        # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
