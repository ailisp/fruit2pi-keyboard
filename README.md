# Setup steps

## Setup

On Raspberry Pi Zero W, flush a Raspberry Pi Lite OS. Login with username `pi` and password `raspberry`. 
Bootup and connect to WIFI with `raspi-config` command. 
Then install git and clone this repo:
```
sudo apt update
sudo apt install git
git clone https://github.com/ailisp/BL_KEYBOARD_RPI
```

Then install and start this tool (will also make this tool start on boot):
```
cd BL_KEYBOARD_RPI
sudo ./setup.sh
```
