# FPGA Bitstream

This directory contains the FPGA configuration file used by the RP2040 firmware.

## File

```
fpga_based_cordic_digital_communication_demonstrator.bin
```

The bitstream is automatically programmed onto the FPGA by the MicroPython firmware. Manual FPGA programming is **not required**.

---

# Using the Bitstream

Upload the MicroPython firmware:

```
firmware/cordic.py
```

to the onboard RP2040.

When the script is executed, it automatically:

1. Resets the FPGA.
2. Programs the FPGA using:

```
bitstream/FPGA_bitstream_MCU.bin
```

3. Waits for successful configuration.
4. Starts communication with the FPGA.

A successful initialization appears as:

```text
[shrike_flash] FPGA reset done
[shrike_fpga] Starting FPGA flash...
[shrike_fpga] flashing: FPGA_bitstream_MCU.bin
[shrike_flash] FPGA programming done.
```

---

# Running the Demonstrator

After the FPGA has been programmed automatically, the project can be used in two ways.

## Option 1 — Thonny Shell

Run:

```
firmware/cordic.py
```

The script communicates with the FPGA and displays FPGA-generated CORDIC results directly in the Thonny Shell.

Example output:

```text
Angle Mode: d
Enter the Angle: 30

Calculated Values
-----------------
SIN : 0.50390624
COS : 0.86718750
TAN : 0.59375000

Expected Values
---------------
SIN : 0.50000000
COS : 0.86602548
TAN : 0.57735030
```

This mode is intended for evaluating the FPGA CORDIC engine and comparing the computed values with software-generated reference values.

---

## Option 2 — Desktop Host GUI

The Host GUI executable is available from the **Releases** section of this repository.

The GUI communicates with the FPGA through the RP2040 and provides:

- BPSK Modulation
- QPSK Modulation
- Binary / ASCII Input
- Real-Time Waveforms
- Constellation Diagram
- CORDIC Calculator
- Live FPGA-generated SIN, COS and TAN values
- I/Q Components
- Symbol Statistics
- Data Export

---

## Note

All trigonometric calculations are performed inside the FPGA.

The RP2040 acts only as an SPI ↔ USB Serial bridge and automatically programs the FPGA using the supplied bitstream during startup.
