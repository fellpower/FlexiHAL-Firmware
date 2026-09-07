
# FlexiHAL firmware for Modulus

UF2 firmware for the **STM32F446 FlexiHAL** and the Modulus UART pendant.
Forked from [Expatria-Technologies/STM32F4xx](https://github.com/Expatria-Technologies/STM32F4xx),
branch `F446_Flexi_HAL`, baseline `bd233169ef05596c463c73416007f2f2caa97128`.

[Download releases](https://github.com/fellpower/FlexiHAL-Firmware/releases)

## Modulus changes

All 17 machine profiles use `MPG_ENABLE=2` and `KEYPAD_ENABLE=0`.
The statuslight plugin, its build flags and the obsolete `rgb` submodule are
removed. Existing per-profile axis, auto-squaring, spindle/Modbus, probe, ATC,
Ethernet and SD options are retained.

Modulus communicates through the ESP32-S3 bridge and the FlexiHAL MPG UART.
MPG mode 2 switches with the `0x8B` command on that stream. The board maps MPG
to stream 0 / USART1 (PA9 TX, PA10 RX); Modbus retains its separate stream.
**Ethernet/SD builds also use UART for MPG. Telnet-MPG is not implemented.**

## Choose a firmware

Asset names contain only firmware variant and release version, for example
`FlexiHAL-Modulus-printnc-v0.1.0-rc.1.uf2`. Add `f446re_flexi_cnc_` to a variant
below to obtain its PlatformIO environment name.

| Variant | Existing machine configuration |
| --- | --- |
| `printnc` | PrintNC, three axes, ganged Y and auto-square, safety door |
| `printnc_eth_sd` | PrintNC plus Ethernet/SD |
| `printnc_eth_sd_4x` | PrintNC plus fourth axis and Ethernet/SD |
| `ygang_eth_sd_prb` | Three axes, ganged Y/auto-square, Ethernet/SD |
| `ygang_eth_sd_prb_4x` | Four axes, ganged Y/auto-square, Ethernet/SD |
| `3axis_prb` | Three axes |
| `4axis_prb` | Four axes |
| `5axis_prb` | Five axes |
| `3axis_eth_sd_prb` | Three axes, Ethernet/SD |
| `4axis_eth_sd_prb` | Four axes, Ethernet/SD |
| `4axis_eth_sd_prb_door` | Four axes, Ethernet/SD, safety door |
| `5axis_eth_sd_prb` | Five axes, Ethernet/SD |
| `xgang_eth_sd_prb` | Three axes, ganged X/auto-square, Ethernet/SD |
| `xgang_ygang_eth_sd_prb` | Three axes, ganged X and Y/auto-square, Ethernet/SD |
| `3axis_billmill` | Billmill, three axes, Ethernet/SD, no jerk acceleration |
| `5axis_billmill` | Billmill, five axes, Ethernet/SD, jerk acceleration |
| `5axis_billmill_jerk` | Upstream legacy name: actually **three axes**, Ethernet/SD, jerk acceleration and ATCI |

Profile names and settings are preserved from upstream, including the Billmill
naming inconsistency. Inspect `platformio.ini` before selecting a machine
configuration. The files are not interchangeable across different axis setups.

## Local build

On Windows, start `./build.ps1` in PowerShell for the numbered selection menu,
similar to the Modulus launcher. Choose **build + UF2** or **clean**, then one of
the 17 profiles or **all profiles**. When building, accept the latest local
version tag or enter a release version. The verified UF2 path is shown when done;
the menu stays open for another selection. `0` returns or exits.

Direct commands are also supported:

```powershell
.\build.ps1 -List
.\build.ps1 -Environment printnc -Version v0.1.0-rc.1
.\build.ps1 -Environment printnc,printnc_eth_sd
.\build.ps1 -All
.\build.ps1 -Environment printnc -Clean
```

The launcher works from any current directory. Clean only removes generated
build files for the selected profile; packaged UF2s in `outputs` are retained.
It does not flash hardware or publish a GitHub release.

Requires Python 3.11 or newer and **PlatformIO Core 6.1.19** on PATH.
The STM32 platform, framework and ARM compiler versions are pinned in
`platformio.ini`. Submodules stay pinned to the commits recorded in Git.

```powershell
git clone --recurse-submodules --branch F446_Flexi_HAL https://github.com/fellpower/FlexiHAL-Firmware.git N:\Projekte\FlexiHAL-Firmware
cd N:\Projekte\FlexiHAL-Firmware
python scripts/build.py --environment f446re_flexi_cnc_printnc --version v0.1.0-rc.1
```

The wrapper isolates PlatformIO caches under `.tools/platformio`, build files
under `.pio/build`, and verified deliverables under `outputs/<environment>`.
It overrides inherited PlatformIO build-directory settings. Release builds
reject `platformio.local.ini` to prevent undocumented local options.

List all environments with `python scripts/release.py profiles`. To build
another variant, pass its full environment name to `scripts/build.py`.

## Automated releases and verification

GitHub Actions builds all 17 profiles on branch pushes, pull requests and manual
runs. Version tags matching `v*` publish a release only after the entire matrix
passes. For example, tag the reviewed commit with `v0.1.0-rc.1` and push that tag.
Tags with a suffix such as `-rc.1` publish prereleases. Non-tag CI builds use
`v0.1.0-rc.1` for artifact naming and do not publish releases.

Each build checks the effective preprocessor settings (MPG=2, keypad=0,
statuslight off), absence of RGB-plugin compilation, UF2 headers, family ID,
block addresses, flash bounds and payload equality with `firmware.bin`.
Negative tests cover damaged headers, payloads, truncation, bootloader addresses
and oversized images. Releases include `SHA256SUMS.txt` and
`build-manifest.json` with source/submodule commits and tool versions.

**Hardware testing is pending.** Before considering a release hardware-validated,
test Modulus UART communication, MPG takeover/release, return to the normal
sender, and the relevant machine functions. No automated workflow flashes a
controller. UF2 files target the existing FlexiHAL bootloader at application
address `0x08010000`, family `0x57755a57`; they do not include the bootloader.

## Upstream

Original licensing and copyright notices are retained.

[![flag](https://github.com/user-attachments/assets/cc374372-1558-45c4-848a-76a7169151ab)](/README_cdn.md)

# Elbows up.
