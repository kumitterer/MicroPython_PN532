# SPDX-FileCopyrightText: 2015-2018 Tony DiCola for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
``adafruit_pn532.i2c``
====================================================

This module will let you communicate with a PN532 RFID/NFC shield or breakout
using I2C.

* Author(s): Original Raspberry Pi code by Tony DiCola, CircuitPython by ladyada,
             refactor by Carter Nelson

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_PN532.git"

import time
from machine import I2C, Pin
from micropython import const
from pn532.pn532 import PN532, BusyError

try:
    from typing import Optional, Union
except ImportError:
    pass

_I2C_ADDRESS = const(0x24)


class PN532_I2C(PN532):
    """Driver for the PN532 connected over I2C."""

    def __init__(
        self,
        i2c: I2C,
        address: int = _I2C_ADDRESS,
        *,
        irq: Optional[DigitalInOut] = None,
        reset: Optional[DigitalInOut] = None,
        req: Optional[DigitalInOut] = None,
        debug: bool = False
    ) -> None:
        """Create an instance of the PN532 class using I2C. Note that PN532
        uses clock stretching. Optional IRQ pin (not used),
        resetp pin and debugging output.

        :param ~busio.I2C i2c: The I2C bus the PN532 is connected to.
        :param int address: The I2C device address. Defaults to :const:`0x24`
        :param digitalio.DigitalInOut irq: board pin the PN532 IRQ is connected to
        :param digitalio.DigitalInOut reset: board pin the PN532 RSTOUT_N is connected to
        :param digitalio.DigitalInOut req: board pin the PN532 P32 is connected to
        :param bool debug: if True print additional debug statements. Defaults to False

        **Quickstart: Importing and using the device**

            Here is an example of using the :class:`PN532_I2C` class.
            First you will need to import the libraries to use the sensor

            Once this is done you can define your `board.I2C` object and define your object

            .. code-block:: python

                i2c = machine.I2C(0, scl=SCL_PIN, sda=SDA_PIN)
                pn532 = PN532_I2C(i2c, debug=False, reset=RESET_PIN, req=REQ_PIN)
                # Configure PN532 to communicate with MiFare cards
                pn532.SAM_configuration()

            Now you have access to the attributes and functions of the PN532 RFID/NFC
            shield or breakout

            .. code-block:: python

                uid = pn532.read_passive_target(timeout=0.5)

        """
        self.debug = debug
        self._req = req
        self._i2c = i2c
        super().__init__(debug=debug, irq=irq, reset=reset)

    def _wakeup(self) -> None:
        """Send any special commands/data to wake up PN532"""
        if self._reset_pin:
            self._reset_pin.value = True
            time.sleep(0.01)
        if self._req:
            self._req.direction = Direction.OUTPUT
            self._req.value(False)
            time.sleep(0.01)
            self._req.value(True)
            time.sleep(0.01)
        self.low_power = False
        self.SAM_configuration()  # Put the PN532 back in normal mode

    def _wait_ready(self, timeout: float = 1) -> bool:
        """Poll PN532 if status byte is ready, up to `timeout` seconds"""
        status = bytearray(1)
        timestamp = time.monotonic()
        while (time.monotonic() - timestamp) < timeout:
            try:
                with self._i2c:
                    self._i2c.readfrom_into(address, status)
            except OSError:
                continue
            if status == b"\x01":
                return True  # No longer busy
            time.sleep(0.01)  # let's ask again soon!
        # Timed out!
        return False

    def _read_data(self, count: int) -> bytearray:
        """Read a specified count of bytes from the PN532."""
        # Build a read request frame.
        frame = bytearray(count + 1)
        with self._i2c as i2c:
            i2c.readfrom_into(address, frame, stop=1)  # read status byte!
            if frame[0] != 0x01:  # not ready
                raise BusyError
            i2c.readfrom_into(address, frame)  # ok get the data, plus statusbyte
        if self.debug:
            print("Reading: ", [hex(i) for i in frame[1:]])
        return frame[1:]  # don't return the status byte

    def _write_data(self, framebytes: bytes) -> None:
        """Write a specified count of bytes to the PN532"""
        with self._i2c as i2c:
            i2c.writeto(address, framebytes)
