import os

import threading
import time
import tkinter as tk
from tkinter import ttk

from pyjoystick.sdl2 import run_event_loop

from buds_record import buds_init, buds_start_recording, buds_end_recording
from mic_record import mic_init, mic_start_recording, mic_end_recording
from text import TextGenerator

os.environ["DISPLAY"] = ":0"


def get_file_name():
    i = 0
    while True:
        file_name = f"runs/{time.strftime('%m%d_%H%M')}_{i}"
        if not os.path.exists(file_name + ".dat"):
            return file_name
        i += 1


class SilentSpeechRecorder:
    def __init__(self):
        self.start_time = time.time()
        self.sentence_count = 0
        self.restarting = False
        self.pop = False

        self.file_name = get_file_name()
        self.f_data = open(self.file_name + ".dat", "w", encoding="utf-8")

        self.window = tk.Tk()
        self.window.geometry("800x480")
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=3)
        self.init_ui()

        self.init_button()
        self.start_recording()

        self.sentence = None
        self.text_gen = TextGenerator()

        self.window.after(100, self.update_time_label)
        self.window.after(100, self.update_volume_bar)
        self.window.after(100, self.update_buds_byte_count_label)

        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.paused = False
        self.buds_start_bytes = -1

    def init_ui(self):
        # Instruction box
        self.instruction_box = tk.Text(self.window, bg="lightgrey", font=("Arial", 20, "bold"), height=1)
        self.instruction_box.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.instruction_box.tag_config("blue", foreground="blue")

        # Original text box
        self.text_box = tk.Text(self.window, font=("Times New Roman", 18), height=8, wrap=tk.WORD)
        self.text_box.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.time_since = tk.Label(self.window, text="Time since: 0s")
        self.time_since.grid(row=2, column=0, padx=5, pady=5, sticky="W")

        self.sentence_count_label = tk.Label(self.window, text=f"Sentence count: {self.sentence_count}")
        self.sentence_count_label.grid(row=3, column=0, padx=5, pady=5, sticky="W")

        self.buds_byte_count_label = tk.Label(self.window, text="Buds byte count: 0")
        self.buds_byte_count_label.grid(row=3, column=0, padx=5, pady=5, sticky="E")

        self.next_btn = tk.Button(self.window, text="Next", command=self.next_button)
        self.next_btn.grid(row=0, column=1, rowspan=2, sticky="ns", padx=5, pady=5)

        self.pause_btn = tk.Button(self.window, text="Paused", command=self.pause_button, state=tk.DISABLED)
        self.pause_btn.grid(row=2, column=1, sticky="s", padx=5, pady=5)

        self.restart_btn = tk.Button(self.window, text="Restart", command=self.restart_button)
        self.restart_btn.grid(row=3, column=1, sticky="ns", padx=5, pady=5)

        self.volume_bar = ttk.Progressbar(
            self.window, orient="vertical", maximum=100, style="black.Horizontal.TProgressbar"
        )
        self.volume_bar.grid(row=0, column=2, rowspan=4, padx=5, pady=5, sticky="ns")

    def update_time_label(self):
        self.time_since["text"] = f"Time since: {int(time.time() - self.start_time)}s"
        self.window.after(100, self.update_time_label)

    def update_volume_bar(self):
        self.volume_bar["value"] = 0
        self.window.after(10, self.update_volume_bar)

    def update_buds_byte_count_label(self):
        self.buds_byte_count_label["text"] = f"Buds byte count: {self.buds_byte_counter.value}"
        self.window.after(100, self.update_buds_byte_count_label)

    def start_recording(self):
        addr = buds_init()
        self.buds_record_process, self.buds_recording_flag, self.buds_byte_counter = buds_start_recording(
            addr, self.file_name
        )

        device_id = mic_init()
        self.mic_record_process, self.mic_recording_flag, self.mic_byte_counter, self.volume_log = mic_start_recording(
            device_id, self.file_name
        )

    def add_joystick(self, joy):
        print("Added a joystick")

    def remove_joystick(self, joy):
        print("Removed a joystick")

    def key_received(self, key):
        print("Key:", key)
        if key.get_value() == 1:
            if key.keyname == "Button 0":  # A
                self.next_btn.invoke()
            elif key.keyname == "Button 1":  # B
                self.pause_btn.invoke()
            elif key.keyname == "Button 6":  # SELECT
                self.close()
            elif key.keyname == "Button 7":  # START
                self.restart_btn.invoke()

    def init_button(self):
        self.stick_process = threading.Thread(
            target=run_event_loop, args=(self.add_joystick, self.remove_joystick, self.key_received)
        )
        self.stick_process.daemon = True
        self.stick_process.start()

    def next_button(self):
        if self.buds_start_bytes > 0 and self.buds_byte_counter.value - self.buds_start_bytes > 30 * 16000 * 3 * 2:
            self.paused = True
        if not self.paused:
            if self.sentence is not None:
                buds_end_bytes = self.buds_byte_counter.value
                # buds_end_bytes = 0
                mic_end_bytes = self.mic_byte_counter.value
                # mic_end_bytes = 0
                data_str = (
                    f"{self.buds_start_bytes}:{buds_end_bytes} {self.mic_start_bytes}:{mic_end_bytes} {self.sentence}"
                )
                self.f_data.write(data_str + "\n")
                self.sentence_count += 1
                self.sentence_count_label["text"] = f"Sentence count: {self.sentence_count}"

            self.pop = (self.sentence_count % 10 == 0) and not self.pop

            if not self.pop:
                self.sentence = self.text_gen()

                # Clear previous text, select a random sentence from text_arr
                self.text_box.delete("1.0", tk.END)
                self.text_box.insert(tk.END, self.sentence)

                # Change the color of the text based on the sentence count
                self.instruction_box.delete("1.0", tk.END)
                if self.sentence_count < 30:
                    self.instruction_box.insert(tk.END, "Please speak in a whisper.")
                elif self.sentence_count < 60:
                    self.instruction_box.insert(tk.END, "Please speak normally.", "blue")
                else:
                    self.instruction_box.insert(tk.END, "TEST END. Thank you.", "red")
            else:
                self.sentence = None

                self.text_box.delete("1.0", tk.END)
                self.text_box.insert(tk.END, "POP")

                self.instruction_box.delete("1.0", tk.END)
                self.instruction_box.insert(tk.END, "Please pop.")

        # Enable the pause button
        self.pause_btn.configure(state=tk.NORMAL, text="Pause")
        self.paused = False

        # Set the byte counters
        self.buds_start_bytes = self.buds_byte_counter.value
        # self.buds_start_bytes = 0
        self.mic_start_bytes = self.mic_byte_counter.value
        # self.mic_start_bytes = 0

    def pause_button(self):
        # Disable the pause button and change its text to "Paused"
        self.pause_btn.configure(state=tk.DISABLED, text="Paused")
        # Ignore the last data
        # self.sentence = None
        self.paused = True

    def restart_button(self):
        self.restarting = True

        self.close()
        self.start_time = time.time()
        self.sentence_count = 0
        self.sentence_count_label["text"] = f"Sentence count: {self.sentence_count}"
        self.sentence = None
        self.pop = False

        self.file_name = get_file_name()
        self.f_data = open(self.file_name + ".dat", "w")

        self.instruction_box.delete("1.0", tk.END)
        self.text_box.delete("1.0", tk.END)
        self.pause_btn.configure(state=tk.DISABLED, text="Paused")
        self.start_recording()

        self.restarting = False

    def close(self):
        self.f_data.close()

        buds_end_recording(self.buds_record_process, self.file_name, self.buds_recording_flag)
        mic_end_recording(self.mic_record_process, self.mic_recording_flag)

        print("Bye.")
        if not self.restarting:
            self.window.destroy()


if __name__ == "__main__":
    try:
        recorder = SilentSpeechRecorder()
        recorder.window.mainloop()
    except KeyboardInterrupt:
        recorder.close()
