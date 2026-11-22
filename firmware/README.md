# ⚡ ESP32 RFID Attendance Reader — Firmware & Wiring Guide

This directory contains the production-quality Arduino C++ firmware for the **Fitness Temple** RFID gym entrance reader.

---

## 📌 Bill of Materials (BOM)

| Component | Description | Recommended Qty |
|-----------|-------------|-----------------|
| **ESP32 DevKit V1** | 30-pin or 38-pin ESP-WROOM-32 microcontroller | 1 |
| **RC522 RFID Module** | 13.56 MHz RFID Reader + SPI interface | 1 |
| **RFID Cards / Keyfobs** | Mifare Classic 1K (13.56 MHz) | 1+ |
| **Green 5mm LED** | Attendance Marked / Already Marked / Linked feedback | 1 |
| **Red 5mm LED** | Expired / Inactive / Unknown / Error feedback | 1 |
| **Active 5V / 3.3V Buzzer** | Audio feedback | 1 |
| **Resistors** | 220Ω (for LEDs) | 2 |
| **Breadboard & Jumper Wires** | Female-to-Male and Male-to-Male | 1 set |
| **Micro-USB Cable** | Data cable for flashing & powering | 1 |

---

## 🔌 Complete Pin Wiring Table

> [!CAUTION]
> **CRITICAL: Connect RC522 VCC to ESP32 `3V3` (3.3V) ONLY!**
> Do NOT connect RC522 VCC to `5V` / `VIN`. Connecting to 5V will permanently burn the RC522 IC.

| RC522 RFID Pin | ESP32 GPIO Pin | Wire Function | Notes |
|----------------|----------------|---------------|-------|
| **VCC**        | **3V3**        | 3.3V Power    | **Must be 3.3V** |
| **RST**        | **GPIO 22**    | Reset         | Digital Output |
| **GND**        | **GND**        | Common Ground | Shared ground |
| **IRQ**        | *Unconnected*  | Interrupt     | Not used |
| **MISO**       | **GPIO 19**    | SPI MISO      | Standard ESP32 VSPI |
| **MOSI**       | **GPIO 23**    | SPI MOSI      | Standard ESP32 VSPI |
| **SCK**        | **GPIO 18**    | SPI SCK       | Standard ESP32 VSPI |
| **SDA (SS)**   | **GPIO 5**     | SPI Chip Select| Standard ESP32 VSPI |

### Indicator & Buzzer Wiring

| Peripheral | Positive (+) Leg / Anode | Negative (-) Leg / Cathode |
|------------|--------------------------|----------------------------|
| **Green LED** | **GPIO 26** (via 220Ω resistor) | **GND** |
| **Red LED** | **GPIO 27** (via 220Ω resistor) | **GND** |
| **Active Buzzer** | **GPIO 25** | **GND** |

---

## 🎵 Visual & Acoustic Feedback Table

| `/scan` Status | Green LED | Red LED | Buzzer Pattern | Meaning |
|----------------|-----------|---------|----------------|---------|
| `marked` | Solid ON (1.5s) | OFF | 1 crisp beep (150ms) | Attendance logged successfully |
| `already_marked` | 2 Pulses | OFF | 2 short beeps (100ms each) | Member already checked in today |
| `linked` | Alternate blink | Alternate blink | 3 happy celebratory beeps | New card successfully registered to member |
| `expired` | OFF | 3 Pulses | 3 warning beeps (200ms each) | Membership has expired |
| `inactive` | OFF | Solid ON (2s) | 1 long buzz (800ms) | Lost/stolen card deactivated |
| `unknown` / `rejected` | OFF | 5 Fast blinks | Rapid error clicks | Unregistered card or invalid device key |
| *Offline Queued* | Pulse once | Pulse once | 2 short blips | No WiFi; stored in offline buffer |

---

## 🛠️ Arduino IDE Setup & Flashing

### 1. Install Arduino IDE
Download [Arduino IDE 2.x](https://www.arduino.cc/en/software).

### 2. Add ESP32 Board Support
1. Go to **File → Preferences**.
2. In **Additional boards manager URLs**, add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Go to **Tools → Board → Boards Manager**, search for `esp32` by Espressif, and install.

### 3. Install Required Libraries
Go to **Sketch → Include Library → Manage Libraries...** and install:
1. **MFRC522** by *GithubCommunity* (v1.4.10+)
2. **ArduinoJson** by *Benoit Blanchon* (v6.21.0+)

### 4. Configure `esp32_rfid_reader.ino`
Open `firmware/esp32_rfid_reader/esp32_rfid_reader.ino` and update:
```cpp
const char* WIFI_SSID     = "Your_WiFi_Name";
const char* WIFI_PASSWORD = "Your_WiFi_Password";

// Change to your laptop/server IP address on the local WiFi network:
const char* SERVER_URL    = "http://192.168.1.100:8000/scan";
const char* DEVICE_KEY    = "testdevice123";
```

### 5. Flash to ESP32
1. Select Board: **Tools → Board → ESP32 Arduino → DOIT ESP32 DEVKIT V1**
2. Select Port: **Tools → Port → COM...** (check Device Manager on Windows)
3. Click **Upload** (hold the `BOOT` button on the ESP32 if the serial monitor hangs on `Connecting.......___`).
4. Open **Serial Monitor** at **115200 baud**.
