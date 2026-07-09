from rp2040_slave import RP2040_Slave

slave = RP2040_Slave(
    i2c_id=1,
    sda=18,
    scl=19,
    i2c_address=0x48
)

print("I2C Slave Ready @ 0x48")

while True:

    state = slave.handle_event()

    if state == slave.I2CStateMachine.I2C_START:
        print("START")

    elif state == slave.I2CStateMachine.I2C_RECEIVE:

        while slave.Available():
            b = slave.Read_Data_Received()
            print("RX:", hex(b))

    elif state == slave.I2CStateMachine.I2C_REQUEST:

        while slave.is_Master_Req_Read():
            slave.Slave_Write_Data(0x55)

    elif state == slave.I2CStateMachine.I2C_FINISH:
        print("STOP")
