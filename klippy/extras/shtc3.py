# Support for SHTC3 temperature & humidity sensor
# Based on Adafruit library

import logging
from . import bus
from struct import unpack_from

REPORT_TIME = .8
DEFAULT_ADDR = 0x70  # SHTC3 I2C Address

READID = 0xEFC8  # Read Out of ID Register
SOFTRESET = 0x805D  # Soft Reset
SLEEP = 0xB098  # Enter sleep mode
WAKEUP = 0x3517  # Wakeup mode
CHIP_ID = 0x807  # CHIP ID
NORMAL_TFFIRST = 0x7866  # Normal measurement, temp first with Clock Stretch disabled


class SHTC3:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.i2c = bus.MCU_I2C_from_config(
            config, default_addr=DEFAULT_ADDR, default_speed=100000
        )
        self.mcu = self.i2c.get_mcu()
        self.min_temp = 0
        self.max_temp = 0
        self.temp = 0
        self.humidity = 0
        self.sample_timer = None
        self.max_sample_time = None
        self.printer.add_object("shtc3 " + self.name, self)
        #if self.printer.get_start_args().get("debugoutput") is not None:
        #    return
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

    def handle_connect(self):
        #self.reactor.pause(self.reactor.monotonic() + 0.2)
        #self.write_register(0xC8)
        
        #if chip_id != CHIP_ID:
        #    logging.info("SHTC3: Unknown Chip ID received %#x" % chip_id)
        #else:
        #    logging.info("SHTC3: Found SHTC3  at %#x" % (self.i2c.i2c_address))
        #self.reactor.pause(self.reactor.monotonic() + .5)
        #self.i2c.i2c_write(SOFTRESET)
        #self.reactor.pause(self.reactor.monotonic() + .5)
        #self.i2c.i2c_write(NORMAL_TFFIRST)
        #self.reactor.pause(self.reactor.monotonic() + .5)
        

        self.sample_timer = self.reactor.register_timer(self.sample_sensor)
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)
        #self.reactor.update_timer(self.sample_timer, self.reactor.NOW)
    def setup_minmax(self, min_temp, max_temp):
        self.min_temp = min_temp
        self.max_temp = max_temp
        
    def setup_callback(self, cb):
        self._callback = cb
    
    def sample_sensor(self, eventtime):
        self.sleep(False)
        self.reactor.pause(self.reactor.monotonic() + 0.1)
        self.recv = self.get_measurements()
        self.temp_data = self.recv[0:2]
        self.temp_crc = self.recv[2]
        self.raw_temp = unpack_from(">H", self.temp_data)[0]
        self.raw_temp = ((4375 * self.raw_temp) >> 14) - 4500
        self.temp = self.raw_temp / 100.0
        self.humidity_data = self.recv[3:5]
        self.humidity_crc = self.recv[5]
        self.raw_humidity = unpack_from(">H", self.humidity_data)[0]
        self.raw_humidity = (625 * self.raw_humidity) >> 12
        self.humidity = self.raw_humidity / 100.0
        self.reactor.pause(self.reactor.monotonic() + 0.1)
        self.sleep(True)
        self.reactor.pause(self.reactor.monotonic() + 0.5)
        measured_time = self.reactor.monotonic()
        self._callback(self.mcu.estimated_print_time(measured_time), self.temp)
        return measured_time + REPORT_TIME
    
    #def read_register(self, reg_name, read_len):
            # read a single register
        #regs = [self.chip_registers[reg_name]]
    #    params = self.i2c.i2c_read(regs, read_len)
    #    return bytearray(params['response'])
    
    #def init_sensor(self, eventtime):
    def write_register(self, data):
        if type(data) is not list:
            data = [data]
        data.insert(0,0xEF)
        self.i2c.i2c_write(data)


    def wake_up_send(self):
        data = [0x35,0x17]
        self.i2c.i2c_write(data)
    def sleep_send(self):
        data = [0xB0,0x98]
        self.i2c.i2c_write(data)
    def get_measurements(self):
        data = [0x78,0x66]
        self.i2c.i2c_write(data)
        self.reactor.pause(self.reactor.monotonic() + .1)
        data = []
        recv = self.i2c.i2c_read(data, 6)
        return bytearray(recv['response'])


    def sleep(self, sleep_enabled):
        if sleep_enabled:
            self.sleep_send()
        else:
            self.wake_up_send()
        #time.sleep(0.001)
        #self.reactor.pause(self.reactor.monotonic() + 0.002)

    def get_status(self, eventtime):
        data = {
            'temperature': round(self.temp, 2)
        }
        data['humidity'] = self.humidity
        return data

def load_config(config):
    # Register sensor
    logging.info("SHTC3 init")
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("SHTC3", SHTC3)