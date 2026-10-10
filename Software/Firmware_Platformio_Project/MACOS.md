# Firmware workflow on macOS

This is the upstream ESP32-S3 PlatformIO project. The project configuration targets `esp32-s3-devkitc-1`, uses Arduino, and configures 8 MB flash plus PSRAM.

## Install PlatformIO

One practical command-line route is:

```zsh
brew install pipx
pipx ensurepath
pipx install platformio
```

Restart Terminal after `pipx ensurepath`, then confirm:

```zsh
pio --version
```

The PlatformIO IDE extension for VS Code is an alternative if you prefer a graphical workflow.

## Build and flash

From this directory:

```zsh
pio run
pio run --target upload
pio device monitor --baud 115200
```

Select the correct serial port if PlatformIO cannot detect the board automatically. The USB connection used to build, flash, or monitor is for bench work only. Disconnect USB-C before connecting electrodes to a person.

After the board is battery-powered, the macOS host package at `src/diy_eeg_mac/` discovers the BLE stream named `ESP32_EEG_DATA` and publishes it as LSL stream `Custom_ESP32_EEG`.
