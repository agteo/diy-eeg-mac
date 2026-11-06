# Watch the live signal

Install once, using [INSTALL.md](INSTALL.md). These are the commands for a later session.

The board sends samples over Bluetooth. The Mac receiver turns that into an LSL stream named `Custom_ESP32_EEG`. The plot reads that stream. USB-C can power the board during a resistor-dummy test. It does not carry the samples. Disconnect USB-C before electrodes are attached to a person.

## Each session

Turn on Bluetooth. Power the board and leave it running the firmware (press the reset button once if it is still in the loader).

Terminal 1:

From the repository root:

```zsh
source .venv/bin/activate
diy-eeg-receiver
```

Wait until it prints `Connected. LSL stream Custom_ESP32_EEG is live`. Leave this window open. It stays quiet while data is flowing.

Terminal 2, from the repository root:

```zsh
source .venv/bin/activate
mne-lsl viewer -s Custom_ESP32_EEG
```

That command opens two windows. **Scope settings** is the control panel. The scrolling traces are in the plot window, which opens to its right. If you only see the numbers 0–7, look beside or behind Scope settings for the plot.

The receiver in Terminal 1 has to stay connected. Close the Scope settings window to stop the viewer. `Ctrl-C` in that terminal interrupts it less cleanly. `Ctrl-C` in Terminal 1 stops the receiver.

These controls change the display only. A LabRecorder file still contains the unfiltered stream.

## Scope settings

The numbers `0`–`7` are the eight board channels. This stream has no electrode names, so the viewer uses those indexes. With the daily montage, `0`–`3` are O1, Oz, O2, and POz, and `4` is Fz on J3 pin 5+. The firmware derives bias from board channels 1–4, so Fz is recorded and is not part of that mix. Channels `5`–`7` stay in the stream even when nothing is connected to them.

Highlighted cells are the ones drawn on the plot. Click one cell to show only that channel. Hold Command and click to add or remove channels. Shift-click selects a range. For the daily montage, select `0` through `4`.

| Control | What to do |
| --- | --- |
| Scale | Vertical range in microvolts. `1e2` means 100 µV per channel. Scroll on the plot window to change it. If a trace is pinned to the top or bottom, pick a larger scale (`1e3`, `1e4`). If it looks like a flat line in the middle, pick a smaller one (`1e1`, `1e0`). |
| Time (s) | Seconds visible across the plot. The default is 10. The maximum is 30. |
| CAR | Common average reference. It subtracts the average of the selected channels from each of them. Leave it off when some selected channels are not connected, because those inputs pull the average around. |
| Detrend | Subtracts a running average so a trace sits nearer zero. Leave it off unless a channel has a large offset. |
| Bandpass Filter | Shows only the frequencies between the two boxes, in hertz. `1.00` to `40.00` is a useful starting display. The low value must stay at least 1 Hz below the high value. |
| Show LPT events | Draws hardware trigger marks. This board does not send a trigger channel, so leave it off. |

A startup warning that the channel description could not be read is expected. The viewer then labels the channels `0`–`7` and continues.

## If the receiver keeps printing “Not found”

The board is not advertising `ESP32_EEG_DATA`. From the firmware directory, after holding the boot button, tapping reset, and releasing boot:

From `Software/Firmware_Platformio_Project`:

```zsh
pio run -t upload -e esp32-s3-devkitc-1
```

Press reset once after the upload. `pio device monitor -e esp32-s3-devkitc-1` should print `Setup complete`. Press `Ctrl-C`, then start `diy-eeg-receiver` again.
