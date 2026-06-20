#!/usr/bin/env python3

import datetime
import shlex
import subprocess
import time

import schedule
from openrgb import OpenRGBClient
from openrgb.utils import DeviceType, ModeFlags, RGBColor


PRIMARY_WAN = "vlan603"
PRIMARY_METRIC = 500
BACKUP_WAN = "igc0"
FAILOVER_METRIC = 50
FAILOVER_SERVICE = "metatron-wan-failover.service"

STATE_FIBER = "fiber"
STATE_LTE = "lte"
STATE_OFFLINE = "offline"


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


def route_field(tokens, field):
    try:
        index = tokens.index(field)
    except ValueError:
        return None

    try:
        return tokens[index + 1]
    except IndexError:
        return None


def route_metric(tokens):
    value = route_field(tokens, "metric")
    if value is None:
        return 0

    try:
        return int(value)
    except ValueError:
        return 0


def default_routes():
    try:
        output = subprocess.check_output(
            ["ip", "-4", "route", "show", "default"],
            text=True,
        )
    except Exception:
        return []

    routes = []
    for line in output.splitlines():
        tokens = shlex.split(line)
        if not tokens or tokens[0] != "default":
            continue

        routes.append(
            {
                "dev": route_field(tokens, "dev"),
                "proto": route_field(tokens, "proto"),
                "metric": route_metric(tokens),
            }
        )

    return routes


def failover_service_active():
    try:
        subprocess.run(
            ["systemctl", "is-active", "--quiet", FAILOVER_SERVICE],
            check=True,
            timeout=1,
        )
        return True
    except Exception:
        return False


def network_state():
    if not failover_service_active():
        return STATE_OFFLINE

    routes = default_routes()

    has_failover_override = any(
        route["dev"] == BACKUP_WAN
        and route["proto"] == "static"
        and route["metric"] == FAILOVER_METRIC
        for route in routes
    )
    if has_failover_override:
        return STATE_LTE

    has_primary_route = any(
        route["dev"] == PRIMARY_WAN and route["metric"] == PRIMARY_METRIC
        for route in routes
    )
    if has_primary_route:
        return STATE_FIBER

    has_backup_route = any(route["dev"] == BACKUP_WAN for route in routes)
    if has_backup_route:
        return STATE_LTE

    return STATE_OFFLINE


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


def lte_fallback():
    dev = connect()
    dev.set_mode("strobe")
    dev.leds[0].set_color(RGBColor.fromHEX("#ffbf00"))


day_start = datetime.time(7, 0, 0)
day_start_mode = rainbow
day_end = datetime.time(0, 0, 0)
day_end_mode = off


def main():
    schedule.every().day.at(day_start.strftime("%H:%M")).do(day_start_mode)
    schedule.every().day.at(day_end.strftime("%H:%M")).do(day_end_mode)

    boot()

    previous_state = None

    while True:
        current_state = network_state()

        if current_state == STATE_FIBER:
            if previous_state != STATE_FIBER:
                boot()
            schedule.run_pending()
        elif current_state == STATE_LTE:
            if previous_state != STATE_LTE:
                lte_fallback()
        else:
            if previous_state != STATE_OFFLINE:
                no_inet()

        previous_state = current_state
        time.sleep(2)


if __name__ == "__main__":
    main()
