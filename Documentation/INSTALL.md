# Install

One-time setup for the Mac host tools and, separately, the firmware tools. Day-to-day commands are in [VISUALIZE.md](VISUALIZE.md).

## Host tools

Use Python 3.11, 3.12, or 3.13. This project pins `bleak` 0.22, which does not install on Python 3.14 or 3.15. On this Mac, `python3` may be 3.15, so create the environment with Homebrew’s 3.11:

```zsh
cd /Users/alext/Documents/Experiments/diy-eeg
rm -rf .venv
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

`python --version` should print `Python 3.11.15` (or another 3.11–3.13 release). `diy-eeg-receiver` should then be on your `PATH` inside this environment.

Later terminals need `source .venv/bin/activate` again. They do not need a new install.

If a new command is added to the repo after this install, refresh the same environment once:

```zsh
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Firmware tools

PlatformIO is only needed to build or upload firmware. The project is `Software/Firmware_Platformio_Project`, environment `esp32-s3-devkitc-1`. Install notes are in [the firmware guide](../Software/Firmware_Platformio_Project/MACOS.md).

On this Mac, `pio` is the pipx install at `~/.local/bin/pio`.

## Visualizer

Install the viewer into the same environment. The command itself is in [VISUALIZE.md](VISUALIZE.md).

```zsh
source .venv/bin/activate
python -m pip install mne-lsl PyQt5
```
