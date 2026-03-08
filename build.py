#!/usr/bin/env python
"""Build FolderSizeViewer.exe and run a basic smoke test."""
import subprocess, sys, time, os
from pathlib import Path

ROOT = Path(__file__).parent
EXE  = ROOT / "dist" / "FolderSizeViewer.exe"

def run(cmd, **kw):
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(r.returncode)

# 0. Generate icon
run([sys.executable, "generate_icon.py"])

# 1. Install pyinstaller if missing
run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

# 2. Build
run(["pyinstaller", "build.spec", "--clean", "--noconfirm"])

# 3. Verify exe exists
if not EXE.exists():
    print("ERROR: exe not found at", EXE); sys.exit(1)
print(f"\nBuild OK — {EXE.stat().st_size / 1e6:.1f} MB")

# 4. Smoke test: launch exe with a known path, let it run 5s, check it doesn't crash
test_path = str(ROOT)
print(f"\nSmoke test: launching {EXE.name} {test_path} (5 s timeout)...")
p = subprocess.Popen([str(EXE), test_path])
time.sleep(5)
rc = p.poll()
if rc is not None:
    print(f"FAIL — exe exited prematurely with code {rc}"); sys.exit(1)
p.terminate()
print("Smoke test PASSED — exe launched and stayed alive.")
