"""Run a checked local release build with project-local caches and outputs."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from release import filename

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--environment", default="f446re_flexi_cnc_printnc")
parser.add_argument("--version", default="v0.1.0-rc.1")
parser.add_argument("--clean-only", action="store_true", help="Clean this profile's build files without building or deleting packaged UF2s")
args = parser.parse_args()
filename(args.environment, args.version)  # Validate before invoking PlatformIO.
environment = dict(os.environ)
environment.update({
    "PLATFORMIO_CORE_DIR": str(ROOT / ".tools" / "platformio"),
    "PLATFORMIO_BUILD_DIR": str(ROOT / ".pio" / "build"),
    "RELEASE_VERSION": args.version,
    "PYTHONIOENCODING": "utf-8",
})
pio = shutil.which("pio")
if not pio:
    raise SystemExit("Install PlatformIO Core 6.1.19 first")
if "version 6.1.19" not in subprocess.check_output([pio, "--version"], text=True, env=environment):
    raise SystemExit("This release requires PlatformIO Core 6.1.19")
commands = (
    [sys.executable, "scripts/release.py", "preflight"],
    [pio, "run", "-e", args.environment],
    [pio, "run", "-e", args.environment, "-t", "compiledb"],
    [sys.executable, "scripts/release.py", "audit", "--environment", args.environment],
)
if args.clean_only:
    commands = ([pio, "run", "-e", args.environment, "-t", "clean"],)
for command in commands:
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
