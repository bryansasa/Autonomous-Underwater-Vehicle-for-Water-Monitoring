#include "sensors/drivers/hwt905_driver.h"

extern "C"
{
    #include <wit_c_sdk.h>
    #include <REG.h>
}


namespace
{
    constexpr float GRAVITY_MPS2 =
        9.80665f;

    constexpr float DEG_TO_RAD_F =
        0.017453292519943295f;


    // HWT905 standard serial encoding:
    //
    // acceleration raw:
    // raw / 32768 * 16 g
    //
    // gyro raw:
    // raw / 32768 * 2000 deg/s

    constexpr float ACCEL_SCALE =
        (16.0f * GRAVITY_MPS2) /
        32768.0f;

    constexpr float GYRO_SCALE =
        (2000.0f * DEG_TO_RAD_F) /
        32768.0f;
}


namespace TyrantSensors
{
    Hwt905Driver *
        Hwt905Driver::active_instance_ =
            nullptr;


    Hwt905Driver::Hwt905Driver(
        HardwareSerial &serial,
        uint32_t baud,
        const ImuMounting &mounting
    )
        :
        serial_(serial),
        baud_(baud),
        mounting_(mounting),

        initialized_(false),

        accel_updated_(false),
        gyro_updated_(false),

        sample_available_(false),

        mag_x_lsb_(0),
        mag_y_lsb_(0),
        mag_z_lsb_(0),

        mag_sequence_(0),

        mag_valid_(false),
        mag_updated_(false),

        latest_sample_ {},

        sequence_(0),

        bytes_received_(0),
        register_updates_(0),
        samples_produced_(0),
        samples_dropped_(0),

        last_micros_32_(0),
        micros_epoch_(0)
    {
    }


    bool Hwt905Driver::begin()
    {
        if (
            !imuMountingValid(
                mounting_
            )
        )
        {
            return false;
        }
        // Official WIT C SDK uses global internal state,
        // therefore Tyrant currently supports one active
        // WIT sensor instance through this adapter.

        if (
            active_instance_ != nullptr &&
            active_instance_ != this
        )
        {
            return false;
        }


        active_instance_ = this;


        serial_.begin(
            baud_
        );


        // Clean any previous WIT SDK state.
        WitDeInit();


        if (
            WitInit(
                WIT_PROTOCOL_NORMAL,
                0x50
            ) != WIT_HAL_OK
        )
        {
            active_instance_ = nullptr;

            return false;
        }


        if (
            WitSerialWriteRegister(
                serialWriteCallback
            ) != WIT_HAL_OK
        )
        {
            WitDeInit();

            active_instance_ = nullptr;

            return false;
        }


        if (
            WitRegisterCallBack(
                registerUpdateCallback
            ) != WIT_HAL_OK
        )
        {
            WitDeInit();

            active_instance_ = nullptr;

            return false;
        }


        if (
            WitDelayMsRegister(
                delayCallback
            ) != WIT_HAL_OK
        )
        {
            WitDeInit();

            active_instance_ = nullptr;

            return false;
        }


        accel_updated_ = false;
        gyro_updated_ = false;

        sample_available_ = false;
        mag_x_lsb_ = 0;
        mag_y_lsb_ = 0;
        mag_z_lsb_ = 0;
        
        mag_sequence_ = 0;
        mag_valid_ = false;
        mag_updated_ = false;

        latest_sample_ = {};

        sequence_ = 0;
        bytes_received_ = 0;
        register_updates_ = 0;
        samples_produced_ = 0;
        samples_dropped_ = 0;

        last_micros_32_ =
            micros();

        micros_epoch_ = 0;


        initialized_ = true;


        return true;
    }


    void Hwt905Driver::update()
    {
        if (!initialized_)
        {
            return;
        }


        // ====================================================
        // UART → OFFICIAL WIT SDK
        // ====================================================

        while (
            serial_.available() > 0
        )
        {
            const int value =
                serial_.read();


            if (value < 0)
            {
                break;
            }


            bytes_received_++;


            // This is now where parsing happens.
            //
            // Tyrant itself does not parse 0x55 frames.
            WitSerialDataIn(
                static_cast<uint8_t>(
                    value
                )
            );
        }


        // ====================================================
        // BUILD ONE COHERENT IMU SAMPLE
        //
        // Wait until both acceleration and gyro have
        // received a fresh update.
        // ====================================================


    }


    bool Hwt905Driver::takeSample(
        ImuSample &sample
    )
    {
        if (!sample_available_)
        {
            return false;
        }


        sample =
            latest_sample_;


        sample_available_ =
            false;


        return true;
    }


    bool Hwt905Driver::initialized() const
    {
        return initialized_;
    }

    TyrantSensors::ImuSourceStats
    Hwt905Driver::getStats() const
    {
        return {
            bytes_received_,
            register_updates_,
            samples_produced_,
            samples_dropped_
        };
    }


    void Hwt905Driver::serialWriteCallback(
        uint8_t *data,
        uint32_t length
    )
    {
        if (active_instance_ == nullptr)
        {
            return;
        }


        active_instance_->
            serial_.write(
                data,
                length
            );
    }


    void Hwt905Driver::registerUpdateCallback(
        uint32_t reg,
        uint32_t count
    )
    {
        if (active_instance_ == nullptr)
        {
            return;
        }


        active_instance_->
            handleRegisterUpdate(
                reg,
                count
            );
    }


    void Hwt905Driver::delayCallback(
        uint16_t ms
    )
    {
        delay(ms);
    }


    void Hwt905Driver::handleRegisterUpdate(
        uint32_t reg,
        uint32_t count
    )
    {
        register_updates_++;


        for (
            uint32_t i = 0;
            i < count;
            i++
        )
        {
            const uint32_t updated_reg =
                reg + i;


            // WIT callback reaches AZ when the whole
            // acceleration triplet has been updated.
            if (updated_reg == AZ)
            {
                accel_updated_ = true;
            }


            // Same principle for GX/GY/GZ.
            if (updated_reg == GZ)
            {
                gyro_updated_ = true;
            }
            if (updated_reg == HZ)
            {
                mag_x_lsb_ =
                    sReg[HX];
                mag_y_lsb_ =
                    sReg[HY];
                mag_z_lsb_ =
                    sReg[HZ];
                mag_sequence_++;
                mag_valid_ =
                    true;
                mag_updated_ =
                    true;
            }
        }
        if (
            accel_updated_ &&
            gyro_updated_
        )
        {
            buildSample();

            accel_updated_ = false;
            gyro_updated_ = false;
        }
    }


    void Hwt905Driver::buildSample()
    {
        if (sample_available_)
        {
            samples_dropped_++;
        }

        sequence_++;


        latest_sample_.sequence =
            sequence_;


        latest_sample_.timestamp_us =
            monotonicMicros();


        // ====================================================
        // ACCELERATION
        // raw → m/s²
        // ====================================================
        // ----------------------------------------------------
        // SENSOR AXES -> BODY AXES
        //
        // Current mapping is identity.
        //
        // This is provisional until the physical HWT905
        // mounting orientation is verified.
        //
        // Estimator use requires these outputs to satisfy
        // the Tyrant FRD body-frame contract.
        // ----------------------------------------------------
        
        const float sensor_accel_x =
            static_cast<float>(
                sReg[AX]
            ) * ACCEL_SCALE;

        const float sensor_accel_y =
            static_cast<float>(
                sReg[AY]
            ) * ACCEL_SCALE;

        const float sensor_accel_z =
            static_cast<float>(
                sReg[AZ]
            ) * ACCEL_SCALE;


        applyImuMounting(
            mounting_,

            sensor_accel_x,
            sensor_accel_y,
            sensor_accel_z,

            latest_sample_.accel_x,
            latest_sample_.accel_y,
            latest_sample_.accel_z
        );
        // ====================================================
        // ANGULAR RATE
        // raw → rad/s
        // ====================================================

        const float sensor_gyro_x =
            static_cast<float>(
                sReg[GX]
            ) * GYRO_SCALE;

        const float sensor_gyro_y =
            static_cast<float>(
                sReg[GY]
            ) * GYRO_SCALE;

        const float sensor_gyro_z =
            static_cast<float>(
                sReg[GZ]
            ) * GYRO_SCALE;


        applyImuMounting(
            mounting_,

            sensor_gyro_x,
            sensor_gyro_y,
            sensor_gyro_z,

            latest_sample_.gyro_x,
            latest_sample_.gyro_y,
            latest_sample_.gyro_z
        );
        // ====================================================
        // MAGNETOMETER
        // raw LSB -> BODY axes
        //
        // Physical scaling/calibration is intentionally not
        // applied here.
        // ====================================================      
        applyImuMounting(
            mounting_,

            mag_x_lsb_,
            mag_y_lsb_,
            mag_z_lsb_,

            latest_sample_.mag_x_lsb,
            latest_sample_.mag_y_lsb,
            latest_sample_.mag_z_lsb
        );

        latest_sample_.mag_sequence =
            mag_sequence_;
            
        latest_sample_.mag_valid =
            mag_valid_;

        latest_sample_.mag_updated =
            mag_updated_;
        
        // mag_updated_ is an event flag.
        //
        // Once a newly received magnetometer measurement has been
        // attached to one coherent IMU sample, subsequent accel/gyro
        // samples must not report the same magnetic measurement as
        // "new" again.
        //
        // mag_sequence_ remains the canonical measurement identity.

        mag_updated_ = false;
        latest_sample_.valid = true;
        sample_available_ = true;
        samples_produced_++;
    }


    uint64_t Hwt905Driver::monotonicMicros()
    {
        const uint32_t now =
            micros();


        // Handle 32-bit micros() rollover.
        if (
            now <
            last_micros_32_
        )
        {
            micros_epoch_ +=
                (1ULL << 32);
        }


        last_micros_32_ =
            now;


        return (
            micros_epoch_ |
            static_cast<uint64_t>(
                now
            )
        );
    }
}
