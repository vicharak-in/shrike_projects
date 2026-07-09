String lineBuffer = "";

void setup()
{
    Serial.begin(9600);
}

void loop()
{
    while (Serial.available())
    {
        char c = Serial.read();

        if (c == '\r' || c == '\n')
        {
            if (lineBuffer.length() > 0)
            {
                Serial.println(lineBuffer);
                lineBuffer = "";
            }
        }
        else
        {
            lineBuffer += c;
        }
    }
}
