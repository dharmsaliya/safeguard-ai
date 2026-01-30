// SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
// SPDX-License-Identifier: MPL-2.0

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>
#include <Arduino_LSM6DSOX.h> 

LSM6DSOXClass myIMU(Wire1, 0x6A);

float x_accel, y_accel, z_accel;
float x_gyro, y_gyro, z_gyro;

// FIX: Library requires 'int' for temperature, not 'float'
int temp_deg = 0; 

unsigned long previousMillis = 0;
const long interval = 10; // 100Hz

void setup() {
  Bridge.begin();
  Modulino.begin(Wire1);
  delay(100); 

  if (!myIMU.begin()) {
    while (1); 
  }
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    if (myIMU.accelerationAvailable() && myIMU.gyroscopeAvailable()) {
      
      myIMU.readAcceleration(x_accel, y_accel, z_accel);
      myIMU.readGyroscope(x_gyro, y_gyro, z_gyro);
      
      // Read Temperature (Only if available)
      if (myIMU.temperatureAvailable()) {
        myIMU.readTemperature(temp_deg);
      }

      // Send 7 values. We cast temp_deg to (float) so Python receives "36.0"
      Bridge.notify("record_sensor_movement", x_accel, y_accel, z_accel, x_gyro, y_gyro, z_gyro, (float)temp_deg);
    }
  }
}