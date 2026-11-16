"""Constants for the local Tapo C200 integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "tapo_c200"

DEFAULT_USERNAME = "admin"
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)

CONF_RTSP_USERNAME = "rtsp_username"
CONF_RTSP_PASSWORD = "rtsp_password"

# pytapo's moveMotorStep(direction) takes a 0-359 "angle" that is really a
# direction selector, not degrees of travel. Measured on a C200 5.0
# (fw 1.2.1 Build 250324) by reading ptz.status angle_x / angle_y around each
# call:
#   90  -> angle_y increases (looks UP)
#   270 -> angle_y decreases (looks DOWN)
#   0   -> angle_x increases (pans one way, call it CLOCKWISE seen from above)
#   180 -> angle_x decreases (opposite)
# At either end of the range the camera returns -64304 MOTOR_LOCKED_ROTOR,
# which is normal and recoverable by moving the other way.
PTZ_DIRECTIONS: dict[str, int] = {
    "up": 90,
    "down": 270,
    "clockwise": 0,
    "counter_clockwise": 180,
}

# Error codes worth recognising (from pytapo/const.py, verified against the
# camera). Kept here so entity code does not depend on pytapo internals.
ERROR_MOTOR_BUSY = -64303
ERROR_MOTOR_LOCKED = -64304
ERROR_PRESET_NOT_FOUND = -64302

# A one-step PTZ nudge takes ~2 s to physically travel and report the new
# angle (measured: moveMotorStep(90) -> angle_y -15 -> +55 over ~2 s). Reading
# the position before then returns the OLD value, so writes schedule a re-read
# instead of refreshing immediately. Calibration sweeps the whole range and is
# much slower.
MOTOR_SETTLE_SECONDS = 5.0
MOTOR_CALIBRATION_SECONDS = 35.0
