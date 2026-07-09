#include <Wire.h>

#define I2C_ADDR 0x48

void setup()
{
    Serial.begin(9600);
    Wire.begin(D2, D1);
}

void loop()
{
    while (Serial.available())
    {
        char c = Serial.read();

        if (c == '\r' || c == '\n')
        {
            Serial.println();

            continue;
        }
        Wire.beginTransmission(I2C_ADDR);
        Wire.write((uint8_t)c);
        Wire.endTransmission();
    }
}
