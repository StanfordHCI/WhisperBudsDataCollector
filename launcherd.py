import subprocess

from pyjoystick.sdl2 import run_event_loop


def print_add(joy):
    print('Added a joystick')


def print_remove(joy):
    print('Removed a joystick')


def key_received(key):
    print('Key:', key)
    if key.get_value() == 1:
        if key.keyname == "Button 8":  # HK
            subprocess.Popen(['python3', 'launcher.py'])

        if key.keyname == "Button 4":  # Left Shoulder
            subprocess.Popen(['xset s activate'], shell=True, env={'DISPLAY': ':0'})
        else:
            # wake up the display
            subprocess.Popen(['xset s reset && xset dpms force on'], shell=True, env={'DISPLAY': ':0'})


run_event_loop(print_add, print_remove, key_received)
