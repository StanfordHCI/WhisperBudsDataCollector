import os
import signal
import subprocess
import time
import threading
import tkinter as tk
import tkinter.scrolledtext as st
import netifaces

from pyjoystick.sdl2 import run_event_loop

os.environ["DISPLAY"] = ":0"
processes = []


def killall():
    # Get a list of all the PIDs
    pids = [pid for pid in os.listdir("/proc") if pid.isdigit()]

    for pid in pids:
        try:
            # Read the command line used to run the process
            command_path = open(os.path.join("/proc", pid, "cmdline"), "rb").read()
            command = command_path.decode("utf-8")

            if "python3" in command and ("launcher.py" in command or "gui.py" in command or "gen.py" in command):
                os.kill(int(pid), signal.SIGKILL)
        except IOError:
            continue


def read_output(process, text_box, post_action=None):
    for line in iter(process.stdout.readline, b""):
        text_box.insert(tk.END, line.decode())
        text_box.see(tk.END)
        root.update()

    if post_action is not None:
        post_action()


def speech_action():
    process = subprocess.Popen(["python3", "gui.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    processes.append(process)
    threading.Thread(target=read_output, args=(process, text_box)).start()


def exit_action():
    for process in processes:
        process.terminate()
    time.sleep(1.0)
    killall()
    root.destroy()


def generate_action():
    pass


def noise_action():
    pass


root = tk.Tk()

# Set the window size
root.geometry("800x480")

# Buttons
button_frame = tk.Frame(root)
button_frame.pack()

exit_button = tk.Button(button_frame, text="Exit", command=exit_action)
exit_button.grid(row=1, column=0)

speech_button = tk.Button(button_frame, text="Speech", command=speech_action)
speech_button.grid(row=0, column=1)

generate_button = tk.Button(button_frame, text="Generate", command=generate_action)
generate_button.grid(row=1, column=2)

noise_button = tk.Button(button_frame, text="Noise", command=noise_action)
noise_button.grid(row=2, column=1)

# Text box
text_box = st.ScrolledText(root, height=12)
text_box.pack()


# Function to get all IP addresses
def get_ip_addresses():
    ip_addresses = []
    for interface in netifaces.interfaces():
        addr = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addr:
            ip_addresses.append(addr[netifaces.AF_INET][0]["addr"])
    return ip_addresses


# Label to display IP addresses
ip_label = tk.Label(root, text=f"IP Addresses: {', '.join(get_ip_addresses())}")
ip_label.pack()


def add_joystick(joy):
    print("Added a joystick")


def remove_joystick(joy):
    print("Removed a joystick")


def is_focused():
    return root.focus_displayof() == root


def key_received(key):
    if is_focused():
        print("Key:", key)
        text_box.insert(tk.END, f"Pressed {str(key.controller_key_name)} {int(key.get_value())}\n")
        text_box.see(tk.END)
        root.update()
        if key.controller_key_name == "leftx" and key.get_value() == -1:  # Left
            exit_button.invoke()
        elif key.controller_key_name == "leftx" and key.get_value() == 1:  # Right
            generate_button.invoke()
        elif key.controller_key_name == "lefty" and key.get_value() == -1:  # Up
            speech_button.invoke()
        elif key.controller_key_name == "lefty" and key.get_value() == 1:  # Down
            noise_button.invoke()


stick_process = threading.Thread(target=run_event_loop, args=(add_joystick, remove_joystick, key_received))
stick_process.start()

root.mainloop()
