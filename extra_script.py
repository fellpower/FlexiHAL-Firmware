"""Create and validate the Modulus UF2 as a required post-build step."""
import os
from pathlib import Path
import re
import subprocess
import sys

Import("env")

if not Path(env.subst("$BUILD_DIR")).resolve().is_relative_to(Path(env.subst("$PROJECT_DIR")).resolve()):
    raise ValueError("Build directory must be inside this project; use python scripts/build.py")

version = os.environ.get("RELEASE_VERSION", "v0.1.0-rc.1")
if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
    raise ValueError("Invalid RELEASE_VERSION")


def after_build(source, target, env):
    root = Path(env.subst("$PROJECT_DIR"))
    build = Path(env.subst("$BUILD_DIR"))
    variant = env.subst("$PIOENV").removeprefix("f446re_flexi_cnc_")
    binary = build / "firmware.bin"
    uf2 = build / f"FlexiHAL-Modulus-{variant}-{version}.uf2"
    subprocess.run([
        sys.executable, str(root / "uf2conv.py"), "-c", "-b", "0x08010000",
        "-f", "0x57755a57", str(binary), "--output", str(uf2),
    ], cwd=root, check=True)
    subprocess.run([
        sys.executable, str(root / "scripts" / "release.py"), "verify",
        "--environment", env.subst("$PIOENV"), "--version", version,
    ], cwd=root, check=True)


env.AddPostAction("buildprog", after_build)
