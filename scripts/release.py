"""Validation and packaging for the FlexiHAL Modulus release matrix."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "f446re_flexi_cnc_"
BASE = 0x08010000
END = 0x08080000
FAMILY = 0x57755A57


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def command_arguments(command):
    if os.name != "nt":
        return shlex.split(command)
    import ctypes
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not pointer:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [pointer[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(pointer)


def profiles():
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read(ROOT / "platformio.ini")
    return [s[4:] for s in config.sections() if s.startswith("env:")]


def preflight():
    environments = profiles()
    if len(environments) != 17 or not all(e.startswith(PREFIX) for e in environments):
        raise ValueError("Expected all 17 FlexiHAL environments")
    if (ROOT / "platformio.local.ini").exists():
        raise ValueError("Release builds must not use platformio.local.ini")
    status = run("git", "submodule", "status", "--recursive")
    if any(line.startswith(("-", "+", "U")) for line in status.splitlines()):
        raise ValueError("Submodules are missing or differ from the recorded commits")
    if re.search(r'path\s*=\s*rgb\s*$', (ROOT / ".gitmodules").read_text(), re.M):
        raise ValueError("Obsolete RGB submodule is still registered")
    return environments


def filename(environment, version):
    if environment not in profiles():
        raise ValueError("Unknown environment")
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Invalid release version")
    return f"FlexiHAL-Modulus-{environment.removeprefix(PREFIX)}-{version}.uf2"


def validate_uf2(data, binary):
    if not binary or BASE + len(binary) > END:
        raise ValueError("Firmware is empty or exceeds application flash")
    count = (len(binary) + 255) // 256
    if len(data) != count * 512:
        raise ValueError("Incorrect UF2 file length")
    restored = bytearray()
    for index in range(count):
        block = data[index * 512:(index + 1) * 512]
        header = struct.unpack_from("<8I", block)
        expected = (0x0A324655, 0x9E5D5157, 0x2000, BASE + index * 256,
                    256, index, count, FAMILY)
        if header != expected or struct.unpack_from("<I", block, 508)[0] != 0x0AB16F30:
            raise ValueError(f"Invalid UF2 header, address or family in block {index}")
        if header[3] + header[4] > END:
            raise ValueError("UF2 writes beyond application flash")
        restored.extend(block[32:288])
    if restored[:len(binary)] != binary or any(restored[len(binary):]):
        raise ValueError("UF2 payload differs from firmware.bin")


def verify(environment, version):
    build = ROOT / ".pio" / "build" / environment
    uf2 = build / filename(environment, version)
    validate_uf2(uf2.read_bytes(), (build / "firmware.bin").read_bytes())
    print(f"Validated {uf2.name}")
    return uf2


def audit(environment, version):
    preflight()
    database = json.loads((ROOT / "compile_commands.json").read_text())
    if any("/rgb/" in entry["file"].replace("\\", "/") for entry in database):
        raise ValueError("RGB plugin is compiled")
    entry = next(e for e in database if ("/" + e["file"].replace("\\", "/")).endswith("/Src/driver.c"))
    if environment not in entry["output"].replace("\\", "/").split("/"):
        raise ValueError("Compilation database belongs to another environment")
    command = entry.get("arguments") or command_arguments(entry["command"])
    args = []
    skip = False
    for arg in command:
        if skip:
            skip = False
        elif arg == "-o":
            skip = True
        elif arg != "-c":
            args.append(arg)
    args.extend(["-E", "-dM"])
    output = subprocess.check_output(args, cwd=entry["directory"], text=True)
    macros = dict(re.findall(r"^#define (\w+)\s+([^\n]+)$", output, re.M))
    for key, value in {"MPG_ENABLE": "2", "KEYPAD_ENABLE": "0", "MPG_STREAM": "0"}.items():
        if macros.get(key) != value:
            raise ValueError(f"Unexpected effective {key}: {macros.get(key)}")
    if macros.get("STATUS_LIGHT_ENABLE", "0") != "0":
        raise ValueError("Statuslight is enabled")
    uf2 = verify(environment, version)
    destination = ROOT / "outputs" / environment
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(uf2, destination / uf2.name)
    core = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))
    packages = {}
    for name in ("framework-stm32cubef4", "toolchain-gccarmnoneeabi", "tool-ldscripts-ststm32", "tool-scons"):
        packages[name] = json.loads((core / "packages" / name / "package.json").read_text())["version"]
    manifest = {
        "environment": environment, "version": version,
        "commit": run("git", "rev-parse", "HEAD"),
        "source_dirty": bool(run("git", "status", "--porcelain", "--untracked-files=no")),
        "submodules": run("git", "submodule", "status", "--recursive").splitlines(),
        "platformio": run("pio", "--version"),
        "platform": "ststm32@" + json.loads((core / "platforms" / "ststm32" / "platform.json").read_text())["version"],
        "packages": packages, "compiler": run(command[0], "--version").splitlines()[0],
        "settings": {key: macros.get(key, "0") for key in
                     ("MPG_ENABLE", "KEYPAD_ENABLE", "STATUS_LIGHT_ENABLE", "MPG_STREAM")},
        "file": uf2.name, "sha256": hashlib.sha256(uf2.read_bytes()).hexdigest(),
        "hardware_tested": False,
    }
    (destination / f"{environment}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Compiler settings verified and packaged: {environment}")


def combine(version):
    source = ROOT / "outputs" / "artifacts"
    manifests = [json.loads(p.read_text()) for p in source.glob("*.json")]
    if sorted(m["environment"] for m in manifests) != sorted(profiles()):
        raise ValueError("Release does not contain exactly the complete profile matrix")
    expected = {m["file"] for m in manifests}
    if {p.name for p in source.glob("*.uf2")} != expected:
        raise ValueError("UF2 asset set differs from the manifests")
    destination = ROOT / "outputs" / "release"
    destination.mkdir(parents=True, exist_ok=False)
    checksums = []
    for manifest in sorted(manifests, key=lambda m: m["file"]):
        if manifest["version"] != version or manifest["commit"] != run("git", "rev-parse", "HEAD"):
            raise ValueError("Release version or source commit mismatch")
        if manifest["source_dirty"]:
            raise ValueError("Release was built from modified sources")
        path = source / filename(manifest["environment"], version)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest["sha256"]:
            raise ValueError("Artifact checksum mismatch")
        shutil.copy2(path, destination / path.name)
        checksums.append(f"{digest}  {path.name}")
    (destination / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n")
    (destination / "build-manifest.json").write_text(json.dumps(manifests, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["profiles", "preflight", "verify", "audit", "combine"])
    parser.add_argument("--environment")
    parser.add_argument("--version", default=os.environ.get("RELEASE_VERSION", "v0.1.0-rc.1"))
    options = parser.parse_args()
    if options.action == "profiles":
        print(json.dumps({"environment": profiles()}, separators=(",", ":")))
    elif options.action == "preflight":
        print(f"Validated {len(preflight())} profiles and all submodule commits")
    elif options.action == "combine":
        combine(options.version)
    else:
        if not options.environment:
            parser.error("--environment is required")
        globals()[options.action](options.environment, options.version)
