"""Constants for the local Tapo C200 integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "tapo_c200"

DEFAULT_USERNAME = "admin"
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)

CONF_RTSP_USERNAME = "rtsp_username"
CONF_RTSP_PASSWORD = "rtsp_password"

# PTZ nudges use moveMotor(x, y), NOT moveMotorStep(direction).
#
# moveMotorStep starts a CONTINUOUS move that never stops on its own - measured
# on a C200 5.0 (fw 1.2.1 Build 250324): one call at direction 0 swept angle_x
# 162 -> 208 -> 259 -> 311 -> 340 (the hard limit) and stayed there. There is no
# stop command: motorMove(0,0) answers -64304 MOTOR_LOCKED_ROTOR mid-travel and
# does not halt anything, and ptz writes all return -40101.
#
# moveMotor(x, y) is a finite RELATIVE move and x/y are DEGREES (verified:
# moveMotor(20, 0) moved angle_x exactly +20.00; moveMotor(0, -5) moved angle_y
# exactly -5.00). It is the only usable primitive for a button.
PTZ_NUDGE_DEGREES = 15
PTZ_TILT_NUDGE_DEGREES = 10

# (dx, dy) per button. +y is up, +x pans clockwise seen from above.
PTZ_DIRECTIONS: dict[str, tuple[int, int]] = {
    "up": (0, PTZ_TILT_NUDGE_DEGREES),
    "down": (0, -PTZ_TILT_NUDGE_DEGREES),
    "clockwise": (PTZ_NUDGE_DEGREES, 0),
    "counter_clockwise": (-PTZ_NUDGE_DEGREES, 0),
}

# Error codes worth recognising (from pytapo/const.py, verified against the
# camera). Kept here so entity code does not depend on pytapo internals.
ERROR_MOTOR_BUSY = -64303
ERROR_MOTOR_LOCKED = -64304
ERROR_PRESET_NOT_FOUND = -64302

# A nudge takes a moment to travel and report the new angle. Reading the
# position immediately returns the OLD value, so writes schedule a re-read
# instead of refreshing right away. Calibration sweeps the whole range and is
# much slower.
MOTOR_SETTLE_SECONDS = 5.0
MOTOR_CALIBRATION_SECONDS = 35.0
