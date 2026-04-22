#ifndef GAS_H
#define GAS_H

#include <Arduino.h>
#include "draw.h"

#define GAS_SENSOR_PIN 34
#define BUZZER_PIN 25

volatile bool gasThresholdReached = false;
extern int animationMode;

void initGasSensor() {
  pinMode(GAS_SENSOR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);
}

bool readGasSensor() {
  return digitalRead(GAS_SENSOR_PIN) == LOW;
}

void updateGasAlert() {
  if (readGasSensor()) {
    digitalWrite(BUZZER_PIN, HIGH);
    animationMode = 1;
    gasThresholdReached = true;
  } 
  else {
    digitalWrite(BUZZER_PIN, LOW);
    animationMode = 0;
    gasThresholdReached = false;
  }
}

void setBuzzer(bool state) {
  digitalWrite(BUZZER_PIN, state ? HIGH : LOW);
}

bool isGasDetected() {
  return gasThresholdReached;
}

#endif
