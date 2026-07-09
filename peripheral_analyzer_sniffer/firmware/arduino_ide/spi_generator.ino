#include <SPI.h>

#define CS_PIN D8

String messageBuffer = "";

void setup()
{
    Serial.begin(9600);

    pinMode(CS_PIN, OUTPUT);
    digitalWrite(CS_PIN, HIGH);

    SPI.begin();
}

void loop()
{
    while (Serial.available())
    {
        char c = Serial.read();

        if (c == '\r' || c == '\n')
        {
            if (messageBuffer.length() > 0)
            {
                digitalWrite(CS_PIN, LOW);

                for (int i = 0; i < messageBuffer.length(); i++)
                {
                    SPI.transfer((uint8_t)messageBuffer[i]);
                }

                digitalWrite(CS_PIN, HIGH);

                messageBuffer = "";
            }
        }
        else
        {
            messageBuffer += c;
        }
    }
}
