import bluetooth
import cbor
import os
from PySide6.QtCore import QStandardPaths
import json

class Config(object):
    _instance = None
    config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.load()
        return cls._instance
    
    def load(self):
        conf_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir)
        self.conf = os.path.join(conf_dir, 'config.json')
        if os.path.exists(self.conf):
            with open(self.conf) as cf:
                try:
                    self.config = json.load(cf)
                except:
                    print('error to load config, use {}')
                    pass
        return self.config
    
    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        with open(self.conf, 'w') as cf:
            json.dump(self.config, cf)


def find_keyboard():
    print('find keyboard ...')
    target_name = "Fruit2pi_Keyboard"
    target_address = None

    nearby_devices = bluetooth.discover_devices()

    for bdaddr in nearby_devices:
        print(bluetooth.lookup_name(bdaddr))
        if target_name == bluetooth.lookup_name( bdaddr ):
            target_address = bdaddr
            break
    if target_address:
        config = Config()
        config.set('addr', target_address)
    return target_address


def connect_keyboard(addr):
    print('connecting keyboard ...')
    sock=bluetooth.BluetoothSocket(bluetooth.L2CAP)
    bluetooth.set_l2cap_mtu( sock, 65535 )
    try:
        sock.connect((addr, 21))
        print('keyboard connected')
    except:
        print('failed to connect')
        sock = None
    return sock

def send_command(sock, command):
    sock.send(cbor.dumps(command))
    return cbor.loads(sock.recv(65535))


if __name__ == '__main__':
    config = Config()
    addr = config.get('addr') or find_keyboard()
    if addr:
        sock = connect_keyboard(addr)
        if sock:
            print(send_command(sock, ['list']))
    else:
        print("could not find target bluetooth device nearby")
