"""Select the native macOS interpreter before importing binary image libraries."""
import os
import platform
import subprocess
import sys

def native_python():
    # Universal Python inherits Rosetta from an Intel Node/npm process; installed
    # Pillow wheels may be arm64. This is explicit host selection, not a retry
    # after an import/build failure. Preserve -m when restarting module commands.
    if sys.platform=='darwin' and platform.machine()=='x86_64':
        result=subprocess.run(['/usr/sbin/sysctl','-in','sysctl.proc_translated'],capture_output=True,text=True,check=True)
        if result.stdout.strip()=='1':
            print('Using native arm64 Python for the artwork export.',flush=True)
            os.execv('/usr/bin/arch',['arch','-arm64',sys.executable,*sys.orig_argv[1:]])
