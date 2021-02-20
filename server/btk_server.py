#!/usr/bin/python3
#
# fruit2pi Bluetooth keyboard/Mouse emulator DBUS Service
#

from __future__ import absolute_import, print_function
from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import socket
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import logging
from logging import debug, info, warning, error
import selectors
import threading
from cbor._cbor import dumps, loads

logging.basicConfig(level=logging.DEBUG)

def list_programs():
    return {'files': ['foo', 'bar']}

def edit_program(name, code):
    return {'status': 'success'}

def delete_programs(names):
    return {'status': 'success'}

def set_program(name):
    return {'status': 'success'}
    

def process_command(data):
    try:
        cmds = loads(data)
    except:
        return {'error': 'parse'}
    if type(cmds) != list or not cmds:
        return {'error': 'format'}
    cmd = cmds[0]
    args = cmds[1:]
    if cmd == 'list':
        return list_programs()
    elif cmd == 'edit':
        if len(args) != 2:
            return {'error': 'format'}
        name = args[0]
        code = args[1]
        return edit_program(name, code)
    elif cmd == 'delete':
        if not args:
            return {'error': 'format'}
        return delete_programs(args)
    elif cmd == 'set':
        if len(args) != 1:
            return None
        name = args[0]
        return set_program(name)
    else:
        return {'error': 'format'}



class BTKbDevice():
    # change these constants
    MY_DEV_NAME = "Fruit2pi_Keyboard"

    # define some constants
    P_CTRL = 17  # Service port - must match port configured in SDP record
    P_INTR = 19  # Service port - must match port configured in SDP record#Interrrupt port
    # dbus path of the bluez profile we will create
    # file path of the sdp record to load
    SDP_RECORD_PATH = sys.path[0] + "/sdp_record.xml"
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self):
        print("2. Setting up BT device")
        self.init_bt_device()
        self.init_bluez_profile()

    # configure the bluetooth hardware device
    def init_bt_device(self):
        print("3. Configuring Device name " + BTKbDevice.MY_DEV_NAME)
        # set the device class to a keybord and set the name
        os.system("hciconfig hci0 up")
        os.system("hciconfig hci0 class 0x0025C0")
        os.system("hciconfig hci0 name " + BTKbDevice.MY_DEV_NAME)
        # make the device discoverable
        os.system("hciconfig hci0 piscan")

    # set up a bluez profile to advertise device capabilities from a loaded service record
    def init_bluez_profile(self):
        print("4. Configuring Bluez Profile")
        # setup profile options
        service_record = self.read_sdp_service_record()
        opts = {
            "AutoConnect": True,
            "ServiceRecord": service_record
        }
        # retrieve a proxy for the bluez profile interface
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object(
            "org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
        manager.RegisterProfile("/org/bluez/hci0", BTKbDevice.UUID, opts)
        print("6. Profile registered ")

    # read and return an sdp record from a file
    def read_sdp_service_record(self):
        print("5. Reading service record")
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except:
            sys.exit("Could not open the sdp record. Exiting...")
        return fh.read()

    # listen for incoming client connections
    def listen(self):
        print("\033[0;33m7. Waiting for connections\033[0m")
        self.scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.scommand = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.scommand.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind these sockets to a port - port zero to select next available
        self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
        self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))
        self.scommand.bind((socket.BDADDR_ANY, 21))

        # Start listening on the server sockets
        self.scontrol.listen(5)
        self.sinterrupt.listen(5)
        self.scommand.listen(5)

        self.scontrol.setblocking(False)
        self.sinterrupt.setblocking(False)
        self.scommand.setblocking(False)

        sel = selectors.DefaultSelector()
        def accept_control(sock, mask):
            self.ccontrol, cinfo = sock.accept()
            self.ccontrol.setblocking(False)
            print ("\033[0;32mGot a connection on the control channel from %s \033[0m" % cinfo[0])
        sel.register(self.scontrol, selectors.EVENT_READ, accept_control)

        def accept_interrupt(sock, mask):
            self.cinterrupt, cinfo = sock.accept()
            self.ccontrol.setblocking(False)
            print (
                "\033[0;32mGot a connection on the interrupt channel from %s \033[0m" % cinfo[0])
        sel.register(self.sinterrupt, selectors.EVENT_READ, accept_interrupt)

        def read_command(conn, mask):
            data = conn.recv(65535)  # Should be ready
            if data:
                resp = process_command(data)
                conn.send(dumps(resp))
            else:
                print('closing', conn)
                sel.unregister(conn)
                conn.close()

        def accept_command(sock, mask):
            self.ccommand, cinfo = sock.accept()
            self.ccommand.setblocking(False)
            print (
                "\033[0;32mGot a connection on the command port from %s \033[0m" % cinfo[0])
            sel.register(self.ccommand, selectors.EVENT_READ, read_command)
        sel.register(self.scommand, selectors.EVENT_READ, accept_command)

        while True:
            events = sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
    
    # send a string to the bluetooth host machine
    def send_string(self, message):
        try:
            print('--------------')
            print(bytes(message))
            self.cinterrupt.send(bytes(message))
        except OSError as err:
            print('error in send_string')
            error(err)

    def send_control_string(self, message):
        try:
            print('--------------')
            print(bytes(message))
            self.ccontrol.send(bytes(message))
        except OSError as err:
            print('error in send_control_string')
            error(err)


class BTKbService(dbus.service.Object):
    def __init__(self):
        print("1. Setting up service")
        # set up as a dbus service
        bus_name = dbus.service.BusName(
            "org.fruit2pi.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(
            self, bus_name, "/org/fruit2pi/btkbservice")
        # create and setup our device
        self.device = BTKbDevice()
        # start listening for connections
        t = threading.Thread(target=self.device.listen, args=())
        t.daemon = True
        t.start()

    @dbus.service.method('org.fruit2pi.btkbservice', in_signature='yay')
    def send_keys(self, modifier_byte, keys):
        print("Get send_keys request through dbus")
        print("key msg: ", keys)
        state = [ 0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0 ]
        state[2] = int(modifier_byte)
        count = 4
        for key_code in keys:
            if(count < 10):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)

    @dbus.service.method('org.fruit2pi.btkbservice', in_signature='yay')
    def send_mouse(self, modifier_byte, keys):
        state = [0xA1, 2, 0, 0, 0, 0]
        count = 2
        for key_code in keys:
            if(count < 6):
                state[count] = int(key_code)
            count += 1
        self.device.send_string(state)
    
    @dbus.service.method('org.fruit2pi.btkbservice', in_signature='ay')
    def send_data(self, data):
        self.device.send_string(data)

    @dbus.service.method('org.fruit2pi.btkbservice', in_signature='ay')
    def send_control_data(self, data):
        self.device.send_control_string(data)


# main routine
if __name__ == "__main__":
    # we an only run as root
    try:
        if not os.geteuid() == 0:
            sys.exit("Only root can run this script")

        DBusGMainLoop(set_as_default=True)
        myservice = BTKbService()
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        sys.exit()
