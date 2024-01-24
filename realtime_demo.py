import math
import multiprocessing
import time
import tkinter as tk
import wave

import numpy as np
from gradio_client import Client

from buds_record_queue import buds_end_recording, buds_init, buds_start_recording

GRADIO_SERVER_URL = ""
TIME_DELTA = 1.2
TIME_MAX = 25


class TranscriptionApp:
    def __init__(self):
        self.client = Client(GRADIO_SERVER_URL)
        print("Backend connected.")

        self.addr = buds_init()
        self.queue = multiprocessing.Queue()
        self.recording_process, self.closing_flag = buds_start_recording(self.addr, self.queue)

        self.root = tk.Tk()
        self.root.title("Transcription App")

        self.text = tk.Text(self.root)
        self.text.pack()

        self.record_button = tk.Button(self.root, text="Start Recording", command=self.toggle_recording)
        self.record_button.pack()

        self.is_recording = False
        self.current_data = bytes()
        self.total_bytes = 0
        self.last_time = time.time()

        self.root.after(10, self.fetch)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def fetch(self):
        data = bytes()
        while not self.queue.empty():
            _data = self.queue.get()
            data += _data
        self.total_bytes += len(data)

        self.root.after(10, self.fetch)

        if not self.is_recording or not data:
            return

        self.current_data += data

        if time.time() - self.last_time > TIME_DELTA:
            self.last_time = time.time()
            self.do_inference(self.current_data, self.total_bytes)

            if len(self.current_data) > 16000 * 6 * TIME_MAX:
                self.toggle_recording()

    def do_inference(self, data, total_bytes):
        start_bytes = total_bytes - len(data)
        # align by 6
        data = data[6 * math.ceil(start_bytes / 6) - start_bytes :]
        data = data[: len(data) - len(data) % 6]
        print("Inference", len(data) / 6 / 16000, "seconds")

        audio_data = np.frombuffer(data, dtype=np.int16)
        audio_data = audio_data.reshape(-1, 3)
        with wave.open("data.wav", "wb") as wav_file:
            # Set the parameters: (nchannels, sampwidth, framerate, nframes, comptype, compname)
            wav_file.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav_file.writeframes(audio_data[:, 1].tobytes())
        self.client.submit("data.wav", api_name="/predict", result_callbacks=self.display_result)

    def display_result(self, result):
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, result)

    def toggle_recording(self):
        if not self.is_recording:
            self.record_button.config(text="Stop Recording")
            self.is_recording = True
            self.last_time = time.time()
        else:
            self.record_button.config(text="Start Recording")
            self.do_inference(self.current_data, self.total_bytes)
            self.is_recording = False
            self.current_data = bytes()

    def run(self):
        self.root.mainloop()

    def close(self):
        buds_end_recording(self.recording_process, self.closing_flag)
        self.root.destroy()


if __name__ == "__main__":
    app = TranscriptionApp()
    app.run()
    print("Bye")
