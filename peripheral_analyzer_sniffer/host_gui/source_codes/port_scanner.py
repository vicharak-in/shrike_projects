from serial.tools import list_ports


def get_available_ports():
    ports = []

    for port in list_ports.comports():
        ports.append(port.device)

    return ports