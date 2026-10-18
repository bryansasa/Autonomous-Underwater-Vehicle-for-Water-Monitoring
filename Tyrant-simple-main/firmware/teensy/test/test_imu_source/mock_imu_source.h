#pragma once

#include "sensors/imu_source.h"


class MockImuSource : public TyrantSensors::ImuSource
{
public:
    void setMagProducing(
        bool producing
    )
    {
        mag_producing_ = producing;
    }
    void setProducing(
        bool producing
    )
    {
        producing_ = producing;
    }

    bool begin() override
    {
        initialized_ = true;
        producing_ = true;
        sample_available_ = false;
        sample_ = {};
        mag_sequence_ = 0;
        mag_producing_ = true;
        sequence_ = 0;
        
        accel_x_ = 0.0f;

        stats_ = {
            0,
            0,
            0,
            0
        };

        return true;
    }

    void setAccelX(
        float value
    )
    {
        accel_x_ = value;
    }

    void update() override
    {
        if (!initialized_)
        {
            return;
        }

        if (!producing_)
        {
            return;
        }

        if (sample_available_)
        {
            stats_.samples_dropped++;
        }
        sequence_++;


        sample_.sequence =
            sequence_;

        sample_.timestamp_us =
            micros();


        sample_.accel_x = accel_x_;        
        sample_.accel_y = 0.0f;
        sample_.accel_z = -9.80665f;


        sample_.gyro_x = 0.0f;
        sample_.gyro_y = 0.0f;
        sample_.gyro_z = 0.0f;

        if (mag_producing_)
        {
            sample_.mag_x_lsb =
                100;

            sample_.mag_y_lsb =
                -200;

            sample_.mag_z_lsb =
                300;


            mag_sequence_++;


            sample_.mag_valid =
                true;

            sample_.mag_updated =
                true;
        }
        else
        {
            sample_.mag_updated =
                false;

            sample_.mag_valid =
                mag_sequence_ > 0;
        }


        sample_.mag_sequence =
            mag_sequence_;

        sample_.valid = true;
        sample_available_ = true;
        stats_.samples_produced++;
    }


    bool takeSample(
        TyrantSensors::ImuSample &sample
    ) override
    {
        if (!sample_available_)
        {
            return false;
        }


        sample =
            sample_;


        sample_available_ =
            false;


        return true;
    }


    TyrantSensors::ImuSourceStats
    getStats() const override
    {
        return stats_;
    }


private:
    bool producing_ = false;
    bool initialized_ = false;
    float accel_x_ = 0.0f;
    bool mag_producing_ = true;
    uint32_t mag_sequence_ = 0;

    bool sample_available_ = false;

    uint32_t sequence_ = 0;


    TyrantSensors::ImuSample sample_ {};


    TyrantSensors::ImuSourceStats stats_ {
        0,
        0,
        0,
        0
    };
};
