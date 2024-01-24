import multiprocessing
import time
import wave

import numpy as np
import pyaudio

FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Number of audio channels
RATE = 48000  # Sample rate (in Hz)


def calc_volume(in_data):
    data = np.frombuffer(in_data, dtype=np.int16)
    volume = np.average(np.abs(data))
    volume_log = 10 * np.log10(volume) if volume > 0 else 0
    return volume_log


def record(device_id, file_name, recording_flag, byte_counter, volume_log):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=4096,
                        input_device_index=device_id)

    sound_file = wave.open(file_name, 'wb')
    sound_file.setnchannels(CHANNELS)
    sound_file.setsampwidth(audio.get_sample_size(FORMAT))
    sound_file.setframerate(RATE)

    count = 1
    while recording_flag.value:
        data = stream.read(4096, exception_on_overflow=False)
        sound_file.writeframes(data)
        byte_counter.value += len(data)

        if count % 4 == 0:
            volume_log.value = calc_volume(data)
        count += 1

    stream.stop_stream()
    stream.close()
    audio.terminate()
    sound_file.close()


def mic_init():
    audio = pyaudio.PyAudio()
    for i in range(audio.get_device_count()):
        if 'USB Audio Device' in audio.get_device_info_by_index(i)['name']:
            return i
    raise Exception('USB Audio Device not found')


def mic_start_recording(device_id, file_name):
    recording_flag = multiprocessing.Value('b', True)
    byte_counter = multiprocessing.Value('i', 0)
    volume_log = multiprocessing.Value('d', 0.0)
    process = multiprocessing.Process(target=record,
                                      args=(
                                          device_id, file_name + '_front.wav', recording_flag, byte_counter,
                                          volume_log))
    process.start()
    return process, recording_flag, byte_counter, volume_log


def mic_end_recording(process, recording_flag):
    recording_flag.value = False
    process.join(5.0)
    if process.is_alive():
        print("Mic recording process is still alive. Terminating...")
        process.terminate()


if __name__ == '__main__':
    device_id = mic_init()
    process, recording_flag, byte_counter, volume_log = mic_start_recording(device_id, 'test')
    time.sleep(5)
    mic_end_recording(process, recording_flag)
    print('Done')
