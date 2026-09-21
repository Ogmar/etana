# Etana Mission — MCU & LoRa Module Technical Review

**High-Altitude Balloon Project**
Author: Adam Ghieh — 7 September 2026

This document reviews a few candidate micro-controllers (MCUs) and a couple of
LoRa modules and conducts an informal comparison analysis to match component
specifications to project requirements.

## Selection Criteria

The component selection criteria were established for the following
specifications:

- MCU must read data from 7+ sensors and communicate with the LoRa module.
- MCU must operate at low temperature (−55 °C).
- MCU should operate for extended duration (hours or days).
- LoRa module must operate at the ISED RSS-247 specified bandwidth (902–928 MHz).

## Micro-controller Selection

The candidate MCUs were selected from the STM32 product lines for their robust
ARM Cortex-based architectures, ease of access and prototyping, reliability, and
customization options. Low-power options were explored, including the U3 Series
and L4/L4+ Series. The following table details the key points:

| Microcontroller | Processor | Clock Speed | Flash Memory | SRAM | Special Features (partial list) | Temperature Range | Cost per Unit |
|-----------------|-----------|-------------|--------------|------|---------------------------------|-------------------|---------------|
| STM32U3 | Arm Cortex-M33 | 96 MHz | 2 MB | 640 KB | SPI, 12-bit ADC, FD-CAN, I²C, I3C, DAC, USART, DSP, HSP | −40 °C ~ 85 °C | $7 – $10 |
| STM32L4 | Arm Cortex-M4 | 80–120 MHz | 1 MB | 320 KB | SPI, 12-bit ADC, CAN, I²C, DAC, USART, DSP | −40 °C ~ 85 °C | $2 – $18 |
| STM32L4+ | Arm Cortex-M4 | 120 MHz | 2 MB | 640 KB | SPI, 12-bit ADC, CAN, I²C, DAC, USART, DSP, Graphics | −40 °C ~ 85 °C | $7 – $15 |

It is to be noted that none of the selected candidates (and most MCUs on the
market) perfectly match the temperature range required, and thus special
consideration may be taken in the design to ensure the components operate within
their respective ranges. In addition, the 12-bit ADC hardware for each MCU listed
above may be over-sampled to provide resolutions up to 16 bits if required.

Taking into consideration the specifications listed above with the project
requirements, the recommended MCU series is the **STM32L4**, since it provides all
required features with many options to customize with changing requirements at a
low cost per unit.

## LoRa Module Selection

Implementing LoRa communication requires an antenna and a LoRa transceiver module
which interfaces with the selected MCU through SPI. The **RFM95W** transceiver
module can be used for prototyping; however, its operating range is above −20 °C
and cannot be used for the final design. A good alternative is the **SX1261/2** or
**SX1276/7/8/9**. They would all fit the requirements at a cost between $10 – $16
per unit. A simple wire antenna may be used, or a specialized one if required.
