# Watch the live signal

Install once, using [INSTALL.md](INSTALL.md). These are the commands for a later session.

The board sends samples over Bluetooth. The Mac receiver turns that into an LSL stream named `Custom_ESP32_EEG`. The plot reads that stream. USB-C can power the board during a resistor-dummy test. It does not carry the samples. Disconnect USB-C before electrodes are attached to a person.

## Each session

Turn on Bluetooth. Power the board and leave it running the firmware (press the reset button once if it is still in the loader).

Terminal 1:

```zsh
cd /Users/alext/Documents/Experiments/diy-eeg
source .venv/bin/activate
diy-eeg-receiver
```

Wait until it prints `Connected. LSL stream Custom_ESP32_EEG is live`. Leave this window open. It stays quiet while data is flowing.

Terminal 2, with the same environment activated:

```zsh
cd /Users/alext/Documents/Experiments/diy-eeg
source .venv/bin/activate
mne-lsl viewer -s Custom_ESP32_EEG
```

That is the command that opens the live view. The receiver in Terminal 1 has to stay connected. Close the viewer window to stop it. `Ctrl-C` in Terminal 1 stops the receiver.

## If the receiver keeps printing “Not found”

The board is not advertising `ESP32_EEG_DATA`. From the firmware directory, after holding the boot button, tapping reset, and releasing boot:

```zsh
cd /Users/alext/Documents/Experiments/diy-eeg/Software/Firmware_Platformio_Project
pio run -t upload -e esp32-s3-devkitc-1
```

Press reset once after the upload. `pio device monitor -e esp32-s3-devkitc-1` should print `Setup complete`. Press `Ctrl-C`, then start `diy-eeg-receiver` again.
