#include <Arduino.h>
#include <Wire.h>
#include <MS5837.h>


namespace
{
MS5837 depth_sensor;
}


void setup()
{
    Serial.begin(115200);

    delay(1500);

    Serial.println(
        "FULLDEPTH MS5837 SMOKE TEST"
    );


    Wire.begin();
    Wire.setClock(100000);


    if (!depth_sensor.init(Wire))
    {
        Serial.println(
            "ERROR: MS5837 not detected"
        );

        while (true)
        {
            delay(1000);
        }
    }


    depth_sensor.setModel(
        MS5837::MS5837_30BA
    );


    Serial.println(
        "MS5837 READY"
    );
}


void loop()
{
    depth_sensor.read();


    Serial.print("pressure_pa: ");
    Serial.println(
        depth_sensor.pressure(
            MS5837::Pa
        ),
        2
    );


    Serial.print("temperature_c: ");
    Serial.println(
        depth_sensor.temperature(),
        2
    );


    Serial.println("---");

    delay(500);
}
