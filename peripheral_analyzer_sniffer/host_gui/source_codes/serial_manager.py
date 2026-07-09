import serial
import time


class SerialManager:

    def __init__(self):
        self.serial_port = None

    def connect(self, port_name, baudrate=115200):
        try:
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                timeout=0.05
            )
            # Write import extended_decoder in case the board is idle at REPL prompt.
            # If the board is already running, this is ignored since the script doesn't read stdin.
            self.serial_port.write(b"\r\nimport extended_decoder\r\n")
            return True
        except Exception as e:
            print(f"Connection Error: {e}")
            return False

    def disconnect(self):

        if self.serial_port:

            if self.serial_port.is_open:
                self.serial_port.close()

            self.serial_port = None

    def is_connected(self):

        return (
            self.serial_port is not None
            and self.serial_port.is_open
        )

    def read_line(self):

        if not self.is_connected():
            return None

        try:

            line = self.serial_port.readline()

            if not line:
                return None

            return line.decode(
                "utf-8",
                errors="ignore"
            ).strip()

        except Exception as e:

            print(f"Read Error: {e}")
            return None

    def read_available(self):

        if not self.is_connected():
            return []

        try:

            lines = []

            while self.serial_port.in_waiting:

                line = self.serial_port.readline()

                if not line:
                    continue

                decoded = line.decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if decoded:
                    lines.append(decoded)

            return lines

        except Exception as e:

            print(f"Read Error: {e}")
            return []

    def write_data(self, data):

        if not self.is_connected():
            return False

        try:

            self.serial_port.write(
                data.encode()
            )

            return True

        except Exception as e:

            print(f"Write Error: {e}")
            return False
        