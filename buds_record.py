import bluetooth
import time
import sys
import multiprocessing

from decoder import process_binary_data, convert_pcm_to_wav

# Configuration
uuid = ""
mac_addr = ""
expected_string = b"I'm OK !\x00"

sample_rate = 16000
n_channels = 3


def buds_init():
    service_matches = bluetooth.find_service(uuid=uuid, address=mac_addr)
    if len(service_matches) == 0:
        print("Couldn't find the service.")
        sys.exit(1)

    return (mac_addr, service_matches[0]["port"])


def record_data(addr, file_name, recording_flag, byte_counter):
    # Create a Bluetooth socket and connect to the specified address and port
    print("Waiting for connection...")
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    sock.connect(addr)
    sock.settimeout(10.0)

    # Wait for the expected string
    while True:
        line = sock.recv(1024)
        print("Received:", len(line), line[:20].hex())
        if line == expected_string:
            print("Received expected string")
            break
        time.sleep(0.1)

    sock.send(b"MIC=3,1")
    line = sock.recv(1024).decode("utf-8").strip()
    assert line == "MIC=3,1", "Received unexpected response: " + line
    print("Sent MIC=3,1")

    # Continuously read data from the Bluetooth socket and save it to the file
    with open(file_name + ".pcm", "wb") as f_dec:
        while recording_flag.value:
            data = sock.recv(664)
            if data:
                # print("Received", len(data), "bytes:", data[:20].hex())
                dec_data = process_binary_data(data)
                f_dec.write(dec_data)
                byte_counter.value += len(dec_data)

    sock.send(b"MIC=3,0")
    time.sleep(0.1)
    sock.close()
    print("Sent MIC=3,0")


def buds_start_recording(sock, file_name):
    recording_flag = multiprocessing.Value("b", True)
    byte_counter = multiprocessing.Value("i", 0)
    record_process = multiprocessing.Process(target=record_data, args=(sock, file_name, recording_flag, byte_counter))
    record_process.start()

    return record_process, recording_flag, byte_counter


def buds_end_recording(process, file_name, recording_flag):
    recording_flag.value = False
    process.join(30.0)
    if process.is_alive():
        print("Buds recording process is still alive. Terminating...")
        process.terminate()

    convert_pcm_to_wav(file_name + ".pcm", file_name + ".wav", sample_rate=sample_rate, channels=n_channels)
    print("Buds recording ended.")


if __name__ == "__main__":
    file_name = "data"
    sock = buds_init()

    try:
        record_process, recording_flag, byte_counter = buds_start_recording(sock, file_name)
        record_process.join()

    except KeyboardInterrupt:
        buds_end_recording(record_process, file_name, recording_flag)
        print("Total bytes recorded:", byte_counter.value)
