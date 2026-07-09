import shrike
from machine import Pin, SPI
import time

from rp2040_slave import RP2040_Slave

shrike.flash("FPGA_bitstream_MCU.bin")

reset_pin = Pin(14, Pin.OUT)

reset_pin.value(0)
time.sleep(0.1)

reset_pin.value(1)
time.sleep(0.1)

cs = Pin(1, Pin.OUT, value=1)

spi = SPI(
    0,
    baudrate=100000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(2),
    mosi=Pin(3),
    miso=Pin(0)
)

slave = RP2040_Slave(
    i2c_id=1,
    sda=18,
    scl=19,
    i2c_address=0x48
)

uart_message = ""
slave_message = ""
i2c_lines = []

def spi_read(n):
    tx = bytes([0] * n)
    rx = bytearray(n)

    cs.value(0)
    spi.write_readinto(tx, rx)
    cs.value(1)

    return rx

def spi_command(cmd):
    cs.value(0)
    spi.write(bytes([cmd]))
    cs.value(1)

print()
print("Protocol Analyzer")
print()

spi_command(0xC1)

while True:

    event = slave.handle_event()

    if event == RP2040_Slave.I2CStateMachine.I2C_RECEIVE:

        b = slave.Read_Data_Received()

        if 32 <= b <= 126:
            slave_message += chr(b)

    elif event == RP2040_Slave.I2CStateMachine.I2C_FINISH:

        if slave_message:

            print()
            print("PROTOCOL DETECTED : I2C SLAVE")
            print("MESSAGE :", slave_message)
            print()

        slave_message = ""

    data = spi_read(64)

    i = 0

    while i < len(data):

        b = data[i]
        
        if b == 0x00:
            i += 1
            continue
    
        if b == 0x01:
            i2c_lines = ["START"]
            i += 1
            continue

        if b == 0x02:
            i2c_lines.append("STOP")
            print()
            print("PROTOCOL DETECTED : I2C")
            for x in i2c_lines:
                print(x)
            print()
            i2c_lines = []
            i += 1
            continue

        if b == 0x03:
            if i + 2 >= len(data):
                break
            addr = data[i + 1]
            ack  = data[i + 2]
            rw = "READ" if (addr & 1) else "WRITE"
            i2c_lines.append(
                "ADDR 0x%02X (%s) %s" % (addr >> 1, rw, "ACK" if ack == 0x05 else "NACK")
            )
            i += 3
            continue
     
        if b == 0x04:
            if i + 2 >= len(data):
                break
            val = data[i + 1]
            ack = data[i + 2]
            i2c_lines.append(
                "DATA 0x%02X %s" % (val, "ACK" if ack == 0x05 else "NACK")
            )
            i += 3
            continue
   
        if b == 0xF1:
            if i + 1 >= len(data):
                break
            ch = data[i + 1]
            if ch in (0x0D, 0x0A):
                if uart_message:
                    print()
                    print("PROTOCOL DETECTED : UART")
                    print("MESSAGE :", uart_message)
                    print()
                    uart_message = ""
            elif 32 <= ch <= 126:
                uart_message += chr(ch)
            i += 2
            continue

        if b == 0xC0:
            
            # 1. Ask FPGA for the dynamically captured length
            spi_command(0xC4)
            time.sleep_us(50)
            
            # Pipeline Flush: Read 3 bytes, grab the 3rd (which is the true length)
            length_response = spi_read(3)
            capture_length = length_response[2]
            
            if 0 < capture_length <= 64:
                spi_command(0xC2)
                time.sleep_us(50)
                
                # Pipeline Flush: Read (length * 2) + 2 dummy bytes
                raw_bram = spi_read((capture_length * 2) + 2)
                bram_data = raw_bram[2:]
            else:
                bram_data = []
            
            spi_command(0xC3)
            
            print()
            print("PROTOCOL DETECTED : SPI")
            print()
            print("START")
            print()
            
            if 0 < capture_length <= 64:
                print(f"BYTES : {capture_length}")
                print()
                
                mosi_list = []
                miso_list = []
                for j in range(0, len(bram_data), 2):
                    mosi_list.append(bram_data[j])
                    miso_list.append(bram_data[j+1])
                    
                mosi_str = " ".join(["%02X" % x for x in mosi_list])
                miso_str = " ".join(["%02X" % x for x in miso_list])
                
                spi_message = ""
                for x in mosi_list:
                    if 32 <= x <= 126:
                        spi_message += chr(x)
                    else:
                        spi_message += "."

                print("MOSI  : " + mosi_str)
                print("MISO  : " + miso_str)

                
            else:
                print("(Invalid length or no data toggles detected during CS active window)")
                
            print()
            print("STOP")
            print()
            
            spi_command(0xC1)
            
            i += 1
            continue

        i += 1

    time.sleep_ms(0)
    
