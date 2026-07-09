# MicroPython Firmware

This directory contains the MicroPython firmware used on the RP2040 of the Shrike Lite board.

---

## Files

### `decoder.py`

**Main application file**

This is the primary firmware for the Peripheral Analyzer Sniffer and is the file that should be executed by the user.

Functions:

- Programs the FPGA using the provided bitstream
- Initializes SPI communication with the FPGA
- Creates the RP2040 I²C slave interface
- Reads decoded protocol packets from the FPGA
- Parses UART, I²C, and SPI events
- Displays decoded protocol information in the Thonny Shell
- Forwards decoded packets to the Host GUI

To start the analyzer:

```text
Run: decoder.py
```

---

### `rp2040_slave.py`

**Support library**

This file implements the RP2040 I²C slave driver used by the analyzer.

Functions:

- RP2040 hardware I²C slave configuration
- START/STOP detection
- Data reception handling
- Read request handling
- I²C event state machine

This file is automatically imported by `decoder.py` and should not normally be executed directly.

---

### `main.py`

**Standalone I²C slave test program**

This file was used during development to verify the RP2040 I²C slave interface independently of the FPGA protocol analyzer.

Functions:

- Creates an I²C slave at address `0x48`
- Displays received bytes
- Reports START and STOP conditions
- Verifies I²C communication with external masters

This file is intended for testing and debugging purposes only.

---

## Typical Usage

1. Copy all firmware files to the RP2040.
2. Copy `FPGA_bitstream_MCU.bin` to the RP2040 filesystem.
3. Open Thonny IDE.
4. Run `decoder.py`.
5. The FPGA is programmed automatically and protocol monitoring begins.

Expected startup output:

```text
[shrike_flash] FPGA programming done.

Protocol Analyzer
```
---
