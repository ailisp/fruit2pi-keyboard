#! /bin/bash
apt install -y tmux
apt install -y bluez bluez-tools bluez-firmware
apt install -y python3 python3-dev python3-dbus python3-pyudev python3-evdev python3-gi python3-cbor

cp dbus/org.fruit2pi.btkbservice.conf /etc/dbus-1/system.d
cp /lib/systemd/system/bluetooth.service ./bluetooth.service.bk
cp bluetooth.service /lib/systemd/system/bluetooth.service
systemctl daemon-reload
systemctl start bluetooth.service
systemctl enable bluetooth.service
