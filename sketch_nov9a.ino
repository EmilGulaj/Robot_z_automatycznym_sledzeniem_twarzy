#include <Servo.h>

Servo servoPan;
Servo servoTilt1;
Servo servoTilt2;
Servo servoShoot;

const int blue_diode = 4;
const int yellow_diode = 5;
const int red_diode = 6;
const int green_diode = 7;

const int pinPan   = 9;
const int pinTilt1 = 10;
const int pinTilt2 = 11;
const int pinShoot = 12;

int panPos   = 90;
int tiltPos  = 90;
int shootPos = 166;

String inputLine = "";

void setBlue() {
  digitalWrite(blue_diode, HIGH);
  digitalWrite(yellow_diode, LOW);
  digitalWrite(red_diode, LOW);
  digitalWrite(green_diode, LOW);
}

void setYellow() {
  digitalWrite(blue_diode, LOW);
  digitalWrite(yellow_diode, HIGH);
  digitalWrite(red_diode, LOW);
  digitalWrite(green_diode, LOW);
}

void setRed() {
  digitalWrite(blue_diode, LOW);
  digitalWrite(yellow_diode, LOW);
  digitalWrite(red_diode, HIGH);
  digitalWrite(green_diode, LOW);
}

void setGreen() {
  digitalWrite(blue_diode, LOW);
  digitalWrite(yellow_diode, LOW);
  digitalWrite(red_diode, LOW);
  digitalWrite(green_diode, HIGH);
}

void setup() {

  Serial.begin(115200);

  servoPan.attach(pinPan);
  servoTilt1.attach(pinTilt1);
  servoTilt2.attach(pinTilt2);
  servoShoot.attach(pinShoot);

  pinMode(blue_diode, OUTPUT);
  pinMode(yellow_diode, OUTPUT);
  pinMode(red_diode, OUTPUT);
  pinMode(green_diode, OUTPUT);

  servoPan.write(panPos);
  servoTilt1.write(tiltPos);
  servoTilt2.write(180 - tiltPos);
  servoShoot.write(shootPos);

  delay(500);

  Serial.println("READY");
}

int clampAngle(int a, int minA = 0, int maxA = 180) {

  if (a < minA) return minA;
  if (a > maxA) return maxA;

  return a;
}

void processCommand(String cmd) {

  cmd.trim();

  if (cmd.length() < 3) return;

  char id = cmd.charAt(0);

  if (cmd.charAt(1) != ':') return;

  int val = cmd.substring(2).toInt();

  if (id == 'P') {

    panPos = clampAngle(val, 0, 180);

    servoPan.write(panPos);

    Serial.print("P:");
    Serial.println(panPos);
  }

  else if (id == 'T') {

    tiltPos = clampAngle(val, 60, 140);

    servoTilt1.write(tiltPos);
    servoTilt2.write(180 - tiltPos);

    Serial.print("T:");
    Serial.println(tiltPos);
  }

  else if (id == 'S') {

    shootPos = clampAngle(val, 55, 166);

    servoShoot.write(shootPos);

    if (shootPos == 55) {
      setRed();
    }
    else {
      setYellow();
    }

    Serial.print("S:");
    Serial.println(shootPos);
  }

  else if (id == 'L') {

    if (val == 0) {
      setBlue();
    }

    else if (val == 1) {
      setYellow();
    }

    else if (val == 2) {
      setRed();
    }

    else if (val == 3) {
      setGreen();
    }
  }
}

void loop() {

  while (Serial.available()) {

    char c = (char)Serial.read();

    if (c == '\n') {

      processCommand(inputLine);

      inputLine = "";
    }

    else if (c != '\r') {

      inputLine += c;
    }
  }
}