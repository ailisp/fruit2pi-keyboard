#!/usr/bin/python3
import sys
import dbus


class BtkDataClient():
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.btkservice = self.bus.get_object(
            'org.fruit2pi.btkbservice', '/org/fruit2pi/btkbservice')
        self.iface = dbus.Interface(self.btkservice, 'org.fruit2pi.btkbservice')

    def send_control_data(self, data):
        self.iface.send_control_data(data)

    def send_data(self, data):
        self.iface.send_data(data)


if __name__ == "__main__":
    argv = sys.argv
    if(len(argv) < 2):
        print("Usage: send.py [-c] num1 num2 ... numn ")
        exit()
    send_control = False
    if argv[1] == '-c':
        send_control = True
        del argv[1]
    data = list(map(int, sys.argv[1:]))
    dc = BtkDataClient()
    if send_control:
        print("Sending control: ", data)
        dc.send_control_data(data)
    else:
        print("Sending: ", data)
        dc.send_data(data)
    print("Done.")
