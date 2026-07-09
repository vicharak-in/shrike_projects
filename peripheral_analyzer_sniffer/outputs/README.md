# Output Validation Results

This directory contains representative output captures obtained during validation of the Peripheral Analyzer Sniffer.

The screenshots demonstrate successful real-time monitoring, decoding, and visualization of UART, I²C, and SPI communication protocols using the FPGA-based analyzer running on the Shrike Lite platform.

---

## Directory Structure

```text
outputs/
├── README.md
│
├── uart/
│   ├── uart_output.png
│   └── uart_waveform.png
│
├── i2c/
│   ├── i2c_img1.png
│   ├── i2c_img2.png
│   └── i2c_img3.png
│
└── spi/
    ├── spi_img1.png

```

## UART Validation

The UART subsystem was validated by transmitting user-generated text messages through the ESP8266 UART interface using PuTTY.

Example messages used during testing include:

- `connection * 12309 % AS`
- `peripheral ANALYZER sniffer`

The analyzer successfully reconstructed complete UART messages and generated waveform visualizations for each received frame.

## I²C Validation

The I²C subsystem was validated using an ESP8266 configured as an I²C master. User-entered characters were transmitted as individual I²C transactions to slave address `0x48`.

Example data captured during testing includes:

- `S`
- `E`
- `R`
- `e`
- `n`
- `e`
- ` `
- `9`
- `1`

For each transaction, the analyzer successfully detected:

- START condition
- Slave address `0x48`
- Data byte
- ACK response
- STOP condition

## SPI Validation

The SPI subsystem was validated using an ESP8266 configured as an SPI master. Text entered through PuTTY was transmitted over SPI and monitored by the FPGA.

Example messages captured during testing include:

- `work @ 100`
- `* 5339 033 peculiar`

The analyzer successfully reconstructed SPI transactions, counted transferred bytes, decoded MOSI data, monitored MISO responses, and displayed complete transaction details in the GUI.

---
