import os
import subprocess

import crcmod
from pydub import AudioSegment

crc32_func = crcmod.predefined.mkCrcFun("crc-32")


def process_binary_data(data):
    # Check if the packet header is "50 44"
    if data[:2] != b"\x50\x44":
        raise ValueError("Invalid packet header")

    # Check the packet length
    packet_length = int.from_bytes(data[2:6], "little")
    if packet_length != len(data) - 14:
        raise ValueError("Invalid packet length")

    # Check the CRC
    calculated_crc = crc32_func(data[14:])
    received_crc = int.from_bytes(data[10:14], "little")
    if calculated_crc != received_crc:
        print("Invalid CRC")
        # raise ValueError("Invalid CRC")

    channel_data = data[14:]
    return channel_data


def convert_pcm_to_wav(input_file, output_file, sample_rate=8000, channels=1):
    command = [
        "ffmpeg",
        "-f", "s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-i", input_file,
        "-c:a", "copy",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-y",
        output_file
    ]

    subprocess.run(command, check=True)


def split_channels(segment: AudioSegment):
    samples = segment.get_array_of_samples()
    mono_channels = []

    for i in range(segment.channels):
        samples_for_current_channel = samples[i :: segment.channels]
        mono_data = samples_for_current_channel.tobytes()
        mono_channels.append(segment._spawn(mono_data, overrides={"channels": 1}))
    return mono_channels


if __name__ == "__main__":
    segment = AudioSegment.from_file("data.wav")
    channels = split_channels(segment)

    for i, channel in enumerate(channels):
        channel.export(f"data_{i}.wav", format="wav")
