from machine import Timer
try:
    from pybytes_protocol import PybytesProtocol
except:
    from _pybytes_protocol import PybytesProtocol

__DEFAULT_HOST = "mqtt.pycom.io"


class __PERIODICAL_PIN:
    TYPE_DIGITAL = 0
    TYPE_ANALOG = 1
    TYPE_VIRTUAL = 2

    def __init__(self, persistent, pin_number, message_type, message, pin_type):
        self.persistent = persistent
        self.pin_number = pin_number
        self.message_type = message_type
        self.message = message
        self.pin_type = pin_type


class Pybytes:
    def __init__(self, config):
        self.__conf = config
        self.__frozen = globals().get('__name__') == '_pybytes'
        self.__custom_message_callback = None
        self.__pybytes_protocol = PybytesProtocol(self.__conf, self.__recv_message)
        self.__custom_message_callback = None

        # START code from the old boot.py
        import machine
        import micropython
        import os
        from binascii import hexlify

        wmac = hexlify(machine.unique_id()).decode('ascii')
        print("WMAC: %s" % wmac)
        print("Firmware: %s" % os.uname().release)
        # print(micropython.mem_info())
        # STOP code from the old boot.py

    def connect_wifi(self, reconnect=True, check_interval=0.5):
        return self.__pybytes_protocol.connect_wifi(reconnect, check_interval)

    def connect_nbiot(self, reconnect=True, check_interval=0.5):
        return self.__pybytes_protocol.connect_nbiot(reconnect, check_interval)

    def connect_lora_abp(self, timeout, nanogateway=False):
        return self.__pybytes_protocol.connect_lora_abp(timeout, nanogateway)

    def connect_lora_otta(self, timeout=15, nanogateway=False):
        return self.__pybytes_protocol.connect_lora_otta(timeout, nanogateway)

    def connect_sigfox(self):
        self.__pybytes_protocol.connect_sigfox()

    def disconnect(self):
        self.__pybytes_protocol.disconnect()

    def send_custom_message(self, persistent, message_type, message):
        self.__pybytes_protocol.send_user_message(persistent, message_type, message)

    def set_custom_message_callback(self, callback):
        self.__custom_message_callback = callback

    def send_ping_message(self):
        self.__pybytes_protocol.send_ping_message()

    def send_info_message(self):
        self.__pybytes_protocol.send_info_message()

    def send_scan_info_message(self):
        self.__pybytes_protocol.send_scan_info_message(None)

    def send_digital_pin_value(self, persistent, pin_number, pull_mode):
        self.__pybytes_protocol.send_pybytes_digital_value(persistent, pin_number, pull_mode)

    def send_analog_pin_value(self, persistent, pin):
        self.__pybytes_protocol.send_pybytes_analog_value(persistent, pin)

    def send_virtual_pin_value(self, persistent, pin, value):
        self.__pybytes_protocol.send_pybytes_custom_method_values(persistent, pin, [value])

    def register_periodical_digital_pin_publish(self, persistent, pin_number, pull_mode, period):
        self.send_digital_pin_value(persistent, pin_number, pull_mode)
        periodical_pin = __PERIODICAL_PIN(persistent, pin_number, None, None,
                                          __PERIODICAL_PIN.TYPE_DIGITAL)
        Timer.Alarm(self.__periodical_pin_callback, period, arg=periodical_pin, periodic=True)

    def register_periodical_analog_pin_publish(self, persistent, pin_number, period):
        self.send_analog_pin_value(persistent, pin_number)
        periodical_pin = __PERIODICAL_PIN(persistent, pin_number, None, None,
                                          __PERIODICAL_PIN.TYPE_ANALOG)
        Timer.Alarm(self.__periodical_pin_callback, period, arg=periodical_pin, periodic=True)

    def add_custom_method(self, method_id, method):
        self.__pybytes_protocol.add_custom_method(method_id, method)

    def enable_terminal(self):
        self.__pybytes_protocol.enable_terminal()

    def send_battery_level(self, battery_level):
        self.__pybytes_protocol.set_battery_level(battery_level)
        self.__pybytes_protocol.send_battery_info()

    def send_custom_location(self, pin, x, y):
        self.__pybytes_protocol.send_custom_location(pin, x, y)

    def __periodical_pin_callback(self, periodical_pin):
        if (periodical_pin.pin_type == __PERIODICAL_PIN.TYPE_DIGITAL):
            self.send_digital_pin_value(periodical_pin.persistent, periodical_pin.pin_number, None)
        elif (periodical_pin.pin_type == __PERIODICAL_PIN.TYPE_ANALOG):
            self.send_analog_pin_value(periodical_pin.persistent, periodical_pin.pin_number)

    def __recv_message(self, message):
        if self.__custom_message_callback is not None:
            self.__custom_message_callback(message)

    def __process_protocol_message(self):
        pass

    def is_connected(self):
        try:
            return self.__pybytes_protocol.is_connected()
        except:
            return False

    def connect(self):
        try:
            lora_joining_timeout = 15  # seconds to wait for LoRa joining

            if not self.__conf['network_preferences']:
                print("network_preferences are empty, set it up in /flash/pybytes_config.json first")

            for net in self.__conf['network_preferences']:
                if net == 'nbiot':
                    if self.connect_nbiot():
                        break
                elif net == 'wifi':
                    if self.connect_wifi():
                        break
                elif net == 'lora_abp':
                    if self.connect_lora_abp(lora_joining_timeout):
                        break
                elif net == 'lora_otaa':
                    if self.connect_lora_otta(lora_joining_timeout):
                        break
                elif net == 'sigfox':
                    if self.connect_sigfox():
                        break
                else:
                    print("Can't establish a connection with the networks specified")
                    # soft reset
                    exit()

            import time
            time.sleep(.1)
            if self.is_connected():
                if self.__frozen:
                    print('Pybytes connected successfully (using the built-in pybytes library)')
                else:
                    print('Pybytes connected successfully (using a local pybytes library)')

                # SEND DEVICE'S INFORMATION
                self.send_info_message()

                # ENABLE TERMINAL
                self.enable_terminal()
            else:
                print('ERROR! Could not connect to Pybytes!')

        except Exception as ex:
            print("Unable to connect to Pybytes: {}".format(ex))


    def write_config(self, file='/flash/pybytes_config.json', silent=False):
        try:
            import json
            f = open(file,'w')
            f.write(json.dumps(self.__conf))
            f.close()
            if not silent:
                print("Pybytes configuration written to {}".format(file))
        except Exception as e:
            if not silent:
                print("Exception: {}".format(e))

    def print_cfg_msg(self):
        if self.__conf.get('cfg_msg') is not None:
            import time
            time.sleep(.1)
            print(self.__conf['cfg_msg'])
            time.sleep(.1)

    def print_config(self):
        for key in self.__conf.keys():
            print('{} = {}'.format(key,self.__conf.get(key)))

    def get_config(self, key=None):
        if key is None:
            return self.__conf
        else:
            return self.__conf.get(key)

    def set_config(self, key=None, value=None):
        if key is None and value is not None:
            self.__conf = value
        elif key is not None:
            self.__conf[key] = value
        else:
            raise ValueError('You need to either specify a key or a value!')

    def read_config(self, file='/flash/pybytes_config.json'):
        try:
            import json
            f = open(file,'r')
            jfile = f.read()
            f.close()
            try:
                pybytes_config = json.loads(jfile.strip())
                print("Pybytes configuration read from {}".format(file))
            except Exception as ex:
                print("Error reading {} file!\n Exception: {}".format(file, ex))
        except Exception as ex:
            print("Cannot open {}: {}".format(file, ex))

    def export_config(self, file='/flash/pybytes_config.json'):
        try:
            import json
            f = open(file,'w')
            f.write(json.dumps(self.__conf))
            f.close()
            print("Pybytes configuration exported to {}".format(file))
        except Exception as e:
            print("Exception: {}".format(e))