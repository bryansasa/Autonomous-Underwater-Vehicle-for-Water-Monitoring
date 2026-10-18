#pragma once

#include <Arduino.h>

#include "sensors/sensor_types.h"
#include "sensors/imu_source.h"
#include "sensors/imu_mounting.h"

namespace TyrantSensors
{
    class Hwt905Driver : public ImuSource    {
    public:

        Hwt905Driver(
            HardwareSerial &serial,
            uint32_t baud,
            const ImuMounting &mounting
        );


            bool begin() override;

            void update() override;

            bool takeSample(
                ImuSample &sample
            ) override;


        bool initialized() const;

    ImuSourceStats getStats() const override;

    private:
        HardwareSerial &serial_;

        uint32_t baud_;
        const ImuMounting mounting_;

        bool initialized_;

        bool accel_updated_;
        bool gyro_updated_;
        bool sample_available_;

        int16_t mag_x_lsb_;
        int16_t mag_y_lsb_;
        int16_t mag_z_lsb_;
        uint32_t mag_sequence_;

        bool mag_valid_;
        bool mag_updated_;

        ImuSample latest_sample_;


        uint32_t sequence_;

        uint32_t bytes_received_;
        uint32_t register_updates_;
        uint32_t samples_produced_;
        uint32_t samples_dropped_;


        // Used to extend Arduino micros() into a 64-bit
        // monotonic timestamp.
        uint32_t last_micros_32_;

        uint64_t micros_epoch_;


        static Hwt905Driver *active_instance_;


        static void serialWriteCallback(
            uint8_t *data,
            uint32_t length
        );


        static void registerUpdateCallback(
            uint32_t reg,
            uint32_t count
        );


        static void delayCallback(
            uint16_t ms
        );


        void handleRegisterUpdate(
            uint32_t reg,
            uint32_t count
        );

    
        void buildSample();

        uint64_t monotonicMicros();
    };
}
