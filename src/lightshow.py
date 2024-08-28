#!/usr/bin/env python3

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType, ModeFlags
import ifaddr
import schedule
import time
import datetime


def connect():
    client = OpenRGBClient()
    return client.get_devices_by_type(DeviceType.MOTHERBOARD)[0]


def rainbow():
    dev = connect()
    rainbow = next(filter(lambda m: m.name.lower() == "rainbow", dev.modes), None)
    if (
        rainbow is None
        or ModeFlags.HAS_SPEED not in rainbow.flags
        or dev.active_mode == rainbow.id
    ):
        return
    rainbow.speed = 254
    dev.set_mode(rainbow)
    dev.save_mode()


def checkInetStatus():
    egress_if = next(
        filter(lambda a: a.nice_name == "vlan603", ifaddr.get_adapters()), None
    )
    if egress_if is None:
        off()
        return False
    return True


def off():
    dev = connect()
    dev.set_mode("Off")


def boot():
    current = datetime.datetime.now().time()

    if day_start <= current and (
        current < day_end if day_end > datetime.time(0) else current > day_end
    ):
        day_start_mode()
    else:
        day_end_mode()


def no_inet():
    dev = connect()
    dev.set_mode("strobe")
    dev.leds[0].set_color(RGBColor.fromHEX("#ff0000"))


day_start = datetime.time(7, 0, 0)
day_start_mode = rainbow
day_end = datetime.time(0, 0, 0)
day_end_mode = off

schedule.every().day.at(day_start.strftime("%H:%M")).do(day_start_mode)
schedule.every().day.at(day_end.strftime("%H:%M")).do(day_end_mode)

boot()

inet_status = not checkInetStatus()

while True:
    if checkInetStatus():
        if not inet_status:
            boot()
        schedule.run_pending()
        inet_status = True
    else:
        if inet_status:
            no_inet()
        inet_status = False
    time.sleep(2)
