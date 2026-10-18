#include <Arduino.h>

// TX EZO -> GPIO 16 (RX ESP32)
// RX EZO -> GPIO 17 (TX ESP32)
HardwareSerial ecSerial(1);

void setup() {
    Serial.begin(115200);
    delay(3000); // Beri jeda 3 detik agar tegangan dan clock ESP32 stabil

    ecSerial.begin(9600, SERIAL_8N1, 16, 17);
    delay(1000);

    // 1. Kuras dan bersihkan buffer sisa startup
    for (int i = 0; i < 3; i++) {
        ecSerial.print("\r");
        delay(200);
    }
    while (ecSerial.available()) {
        ecSerial.read();
    }
    delay(500);

    // 2. Kirim perintah kunci ke mode I2C alamat 100 (0x64)
    Serial.println("Mengirim perintah: I2C,100 ...");
    ecSerial.print("I2C,100\r");
    delay(1500);
}

void loop() {
    // Biarkan kosong
}