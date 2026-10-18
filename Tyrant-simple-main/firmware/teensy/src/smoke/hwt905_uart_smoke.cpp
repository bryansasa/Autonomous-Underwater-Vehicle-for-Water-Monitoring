#include <Arduino.h>
#include <math.h>


namespace
{

constexpr uint32_t USB_BAUD =
    115200;

constexpr uint32_t HWT905_BAUD =
    9600;


// Serial monitor display only.
//
// 500 ms = 2 Hz.
//
// This does NOT change the actual HWT905 sampling rate.

constexpr uint32_t DISPLAY_PERIOD_MS =
    500;


constexpr float GRAVITY_MPS2 =
    9.80665f;

constexpr float DEG_TO_RAD_F =
    0.017453292519943295f;

constexpr float ACCEL_SCALE =
    (16.0f * GRAVITY_MPS2) /
    32768.0f;

constexpr float GYRO_SCALE =
    (2000.0f * DEG_TO_RAD_F) /
    32768.0f;

constexpr float ANGLE_SCALE =
    180.0f /
    32768.0f;


struct LatestValues
{
    float accel_x;
    float accel_y;
    float accel_z;

    float gyro_x;
    float gyro_y;
    float gyro_z;

    float roll_deg;
    float pitch_deg;
    float yaw_deg;

    int16_t mag_x;
    int16_t mag_y;
    int16_t mag_z;

    bool accel_valid;
    bool gyro_valid;
    bool angle_valid;
    bool mag_valid;
};


LatestValues latest {};


uint8_t frame[11] {};

size_t frame_index =
    0;


uint32_t good_frames =
    0;

uint32_t bad_frames =
    0;

uint32_t last_display_ms =
    0;


int16_t readS16(
    uint8_t low,
    uint8_t high
)
{
    return
        static_cast<int16_t>(
            static_cast<uint16_t>(low) |
            (
                static_cast<uint16_t>(high)
                << 8
            )
        );
}


bool checksumValid(
    const uint8_t *data
)
{
    uint8_t sum =
        0;


    for (
        size_t index = 0;
        index < 10;
        ++index
    )
    {
        sum +=
            data[index];
    }


    return
        sum == data[10];
}


void decodeFrame(
    const uint8_t *data
)
{
    const int16_t x =
        readS16(
            data[2],
            data[3]
        );

    const int16_t y =
        readS16(
            data[4],
            data[5]
        );

    const int16_t z =
        readS16(
            data[6],
            data[7]
        );


    switch (
        data[1]
    )
    {
        // Accelerometer
        case 0x51:
        {
            latest.accel_x =
                x * ACCEL_SCALE;

            latest.accel_y =
                y * ACCEL_SCALE;

            latest.accel_z =
                z * ACCEL_SCALE;

            latest.accel_valid =
                true;

            break;
        }


        // Gyroscope
        case 0x52:
        {
            latest.gyro_x =
                x * GYRO_SCALE;

            latest.gyro_y =
                y * GYRO_SCALE;

            latest.gyro_z =
                z * GYRO_SCALE;

            latest.gyro_valid =
                true;

            break;
        }


        // HWT internal Euler angles.
        //
        // Only for smoke-test comparison.
        // The reduced estimator does not consume the HWT internal Euler angles.

        case 0x53:
        {
            latest.roll_deg =
                x * ANGLE_SCALE;

            latest.pitch_deg =
                y * ANGLE_SCALE;

            latest.yaw_deg =
                z * ANGLE_SCALE;

            latest.angle_valid =
                true;

            break;
        }


        // Magnetometer raw LSB

        case 0x54:
        {
            latest.mag_x =
                x;

            latest.mag_y =
                y;

            latest.mag_z =
                z;

            latest.mag_valid =
                true;

            break;
        }


        default:
        {
            break;
        }
    }
}


void processByte(
    uint8_t value
)
{
    if (
        frame_index == 0
    )
    {
        if (
            value == 0x55
        )
        {
            frame[0] =
                value;

            frame_index =
                1;
        }

        return;
    }


    frame[frame_index++] =
        value;


    if (
        frame_index < 11
    )
    {
        return;
    }


    if (
        checksumValid(
            frame
        )
    )
    {
        ++good_frames;

        decodeFrame(
            frame
        );
    }
    else
    {
        ++bad_frames;
    }


    frame_index =
        0;
}


void printLatestValues()
{
    Serial.println(
        "--------------------------------"
    );


    if (
        latest.accel_valid
    )
    {
        Serial.print(
            "ACCEL [m/s2]  X="
        );

        Serial.print(
            latest.accel_x,
            3
        );

        Serial.print(
            "  Y="
        );

        Serial.print(
            latest.accel_y,
            3
        );

        Serial.print(
            "  Z="
        );

        Serial.println(
            latest.accel_z,
            3
        );
    }


    if (
        latest.gyro_valid
    )
    {
        Serial.print(
            "GYRO  [rad/s] X="
        );

        Serial.print(
            latest.gyro_x,
            4
        );

        Serial.print(
            "  Y="
        );

        Serial.print(
            latest.gyro_y,
            4
        );

        Serial.print(
            "  Z="
        );

        Serial.println(
            latest.gyro_z,
            4
        );
    }


    if (
        latest.angle_valid
    )
    {
        Serial.print(
            "ANGLE [deg]    R="
        );

        Serial.print(
            latest.roll_deg,
            2
        );

        Serial.print(
            "  P="
        );

        Serial.print(
            latest.pitch_deg,
            2
        );

        Serial.print(
            "  Y="
        );

        Serial.println(
            latest.yaw_deg,
            2
        );
    }


    if (
        latest.mag_valid
    )
    {
        Serial.print(
            "MAG   [raw]    X="
        );

        Serial.print(
            latest.mag_x
        );

        Serial.print(
            "  Y="
        );

        Serial.print(
            latest.mag_y
        );

        Serial.print(
            "  Z="
        );

        Serial.println(
            latest.mag_z
        );
    }


    Serial.print(
        "FRAMES good="
    );

    Serial.print(
        good_frames
    );

    Serial.print(
        " bad="
    );

    Serial.println(
        bad_frames
    );
}

}


void setup()
{
    Serial.begin(
        USB_BAUD
    );


    Serial1.begin(
        HWT905_BAUD
    );


    delay(
        1500
    );


    Serial.println();
    Serial.println(
        "=== TYRANT HWT905 AXIS SMOKE TEST ==="
    );

    Serial.println(
        "UART: Serial1 @ 9600"
    );

    Serial.println(
        "Display rate: 2 Hz"
    );

    Serial.println();
}


void loop()
{
    // Read EVERY byte produced by HWT905.

    while (
        Serial1.available() > 0
    )
    {
        processByte(
            static_cast<uint8_t>(
                Serial1.read()
            )
        );
    }


    // But only DISPLAY latest values at 2 Hz.

    const uint32_t now_ms =
        millis();


    if (
        now_ms -
        last_display_ms >=
        DISPLAY_PERIOD_MS
    )
    {
        last_display_ms =
            now_ms;


        printLatestValues();
    }
}