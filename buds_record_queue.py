import bluetooth
import time
import sys
import multiprocessing

from decoder import process_binary_data

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


def record_data(addr, queue, closing_flag):
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
    time.sleep(0.1)
    line = sock.recv(7).decode("utf-8").strip()
    assert line == "MIC=3,1", "Received unexpected response: " + line
    print("Sent MIC=3,1")

    # Continuously read data from the Bluetooth socket and save it to the file
    while closing_flag.value:
        data = sock.recv(664)
        if data:
            dec_data = process_binary_data(data)
            queue.put(dec_data, timeout=5)

    sock.send(b"MIC=3,0")
    time.sleep(0.1)
    sock.close()
    print("Sent MIC=3,0")
    queue.close()


def buds_start_recording(sock, queue):
    closing_flag = multiprocessing.Value("b", True)
    record_process = multiprocessing.Process(target=record_data, args=(sock, queue, closing_flag))
    record_process.start()

    return record_process, closing_flag


def buds_end_recording(process, closing_flag):
    closing_flag.value = False
    process.join(10.0)
    if process.is_alive():
        print("Buds recording process is still alive. Terminating...")
        process.terminate()

    print("Buds recording ended.")


if __name__ == "__main__":
    queue = multiprocessing.Queue()
    addr = buds_init()

    try:
        record_process, closing_flag = buds_start_recording(addr, queue)
        while True:
            queue.get()
    except KeyboardInterrupt:
        buds_end_recording(record_process, closing_flag)
