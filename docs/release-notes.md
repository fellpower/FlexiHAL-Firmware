Modulus UART-MPG firmware for the STM32F446 FlexiHAL, based on Expatria's
`F446_Flexi_HAL` branch. All 17 original machine profiles are included.

- MPG mode 2: software switching with the `0x8B` command on the MPG UART.
- Keypad disabled (`KEYPAD_ENABLE=0`).
- Statuslight plugin and its RGB submodule removed.
- Existing per-profile machine, spindle, probing and network options retained.

Choose the UF2 matching your machine profile; `printnc` is the original PrintNC
configuration. Ethernet/SD variants still use UART for MPG. **Telnet-MPG is not
implemented.**

These files passed compilation, effective compiler-setting checks, and UF2
payload/address/family validation. **Hardware testing is still pending.**
In particular, test the Modulus connection, MPG takeover/release and machine
functions before treating this firmware as hardware-validated.

Use the FlexiHAL UF2 bootloader. The application starts at `0x08010000`; the
bootloader is not included. `SHA256SUMS.txt` contains UF2 checksums and
`build-manifest.json` records the exact source, submodule and tool versions.
