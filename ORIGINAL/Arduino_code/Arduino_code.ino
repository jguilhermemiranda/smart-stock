#include <avr/wdt.h>  // Library for resetting the Arduino using the watchdog timer

// ============================================================
// GLOBAL VARIABLES
// ============================================================

String entradaSerial = "";                 // Stores data received through Serial
unsigned long ultimoRecebimento = 0;      // Time when the last message was received from the ESP
const unsigned long timeout = 5000;       // Communication timeout (5 seconds)

// ============================================================
// CNC DRIVER PINS
// ============================================================

const int X_STEP_PIN   = 54;
const int X_DIR_PIN    = 55;
const int X_ENABLE_PIN = 38;

const int Y_STEP_PIN   = 60;
const int Y_DIR_PIN    = 61;
const int Y_ENABLE_PIN = 56;

const int Z_STEP_PIN   = 46;
const int Z_DIR_PIN    = 48;
const int Z_ENABLE_PIN = 62;

// ============================================================
// SENSOR AND ENCODER PINS
// ============================================================

const int endX = 3;          // X-axis limit switch
const int endY = 14;         // Y-axis limit switch
const int decoderY = 11;     // Y-axis sensor/encoder

// ============================================================
// CONTROL VARIABLES
// ============================================================

bool casa = false;           // Indicates whether the machine has completed homing
bool fimY = false;           // Current state of the Y-axis limit switch
bool fimX = false;           // Current state of the X-axis limit switch
bool M = false;              // Operation mode: place or remove object

int G = 0;                   // Main command
long passoX = 0;             // X-axis step counter
long passoY = 0;             // Y-axis step counter
long encoderY = 0;           // Position read from the Y-axis encoder

// ============================================================
// STEP CONFIGURATION
// ============================================================

const long STEPS_PER_RUN = 200;    // Number of steps used during the movement test
const unsigned int stepDelayUs = 1000;  // Delay between step pulses

// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(9600);        // Serial monitor communication with the PC
  Serial1.begin(9600);       // Communication with the ESP-01

  // Configure sensors with internal pull-up resistors
  pinMode(endX, INPUT_PULLUP);
  pinMode(endY, INPUT_PULLUP);
  pinMode(decoderY, INPUT_PULLUP);

  // Configure X-axis driver pins
  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_ENABLE_PIN, OUTPUT);

  // Configure Y-axis driver pins
  pinMode(Y_STEP_PIN, OUTPUT);
  pinMode(Y_DIR_PIN, OUTPUT);
  pinMode(Y_ENABLE_PIN, OUTPUT);

  // Configure Z-axis driver pins
  pinMode(Z_STEP_PIN, OUTPUT);
  pinMode(Z_DIR_PIN, OUTPUT);
  pinMode(Z_ENABLE_PIN, OUTPUT);

  // Enable the motors
  // LOW = enabled on the A4988
  digitalWrite(X_ENABLE_PIN, LOW);
  digitalWrite(Y_ENABLE_PIN, LOW);
  digitalWrite(Z_ENABLE_PIN, LOW);

  // Set the initial movement direction
  digitalWrite(X_DIR_PIN, LOW);
  digitalWrite(Y_DIR_PIN, LOW);
  digitalWrite(Z_DIR_PIN, LOW);

  // Prevent an immediate communication timeout at startup
  ultimoRecebimento = millis();

  Serial.println("System started.");
}

// ============================================================
// MOVE X AND Y BACKWARDS
// ============================================================

void voltar() {

  // Move the Y-axis backwards
  if (passoY > 0) {

    digitalWrite(Y_DIR_PIN, HIGH);

    digitalWrite(Y_STEP_PIN, HIGH);
    delayMicroseconds(500);
    digitalWrite(Y_STEP_PIN, LOW);
    delayMicroseconds(500);

    passoY--;
  }

  // Move the X-axis backwards only when Y is at its home position
  if (passoX > 0 && fimY) {

    digitalWrite(X_DIR_PIN, HIGH);

    digitalWrite(X_STEP_PIN, HIGH);
    delayMicroseconds(500);
    digitalWrite(X_STEP_PIN, LOW);
    delayMicroseconds(500);

    passoX--;
  }
}

// ============================================================
// MOVEMENT TEST
// ============================================================

void teste() {

  while (G == 50) {

    for (long i = 0; i < STEPS_PER_RUN; i++) {

      digitalWrite(X_STEP_PIN, HIGH);
      digitalWrite(Y_STEP_PIN, HIGH);
      digitalWrite(Z_STEP_PIN, HIGH);

      delayMicroseconds(stepDelayUs);

      digitalWrite(X_STEP_PIN, LOW);
      digitalWrite(Y_STEP_PIN, LOW);
      digitalWrite(Z_STEP_PIN, LOW);

      delayMicroseconds(stepDelayUs);
    }

    // Prevent the test from restarting continuously
    G = 0;
  }
}

// ============================================================
// ACTUATE Z-AXIS (GRAB OBJECT)
// ============================================================

void pegar() {

  digitalWrite(Z_STEP_PIN, HIGH);
  delayMicroseconds(500);

  digitalWrite(Z_STEP_PIN, LOW);
  delayMicroseconds(500);
}

// ============================================================
// MOVE Y-AXIS
// ============================================================

void darPassosY(int quantidade) {

  for (int i = 0; i < quantidade; i++) {

    // Do not move beyond the Y-axis limit switch
    if (fimY) {
      break;
    }

    digitalWrite(Y_STEP_PIN, HIGH);
    delayMicroseconds(500);

    digitalWrite(Y_STEP_PIN, LOW);
    delayMicroseconds(500);

    passoY++;
  }
}

// ============================================================
// MOVE X-AXIS
// ============================================================

void darPassosX(int quantidade) {

  // Do not move if the X-axis limit switch is active
  if (fimX) {
    return;
  }

  for (int i = 0; i < quantidade; i++) {

    digitalWrite(X_STEP_PIN, HIGH);
    delayMicroseconds(500);

    digitalWrite(X_STEP_PIN, LOW);
    delayMicroseconds(500);

    passoX++;
  }
}

// ============================================================
// CHECK COMMUNICATION WITH ESP-01
// ============================================================

void sinaldevida() {

  if (Serial1.available()) {

    String mensagem = Serial1.readStringUntil('\n');
    mensagem.trim();

    Serial.print("Received from ESP: ");
    Serial.println(mensagem);

    // Update the last communication timestamp
    ultimoRecebimento = millis();

    // Check whether the ESP sent a G command
    if (mensagem.startsWith("G=")) {

      G = mensagem.substring(2).toInt();

      Serial.print("G updated by ESP: ");
      Serial.println(G);
    }

    // Check whether the ESP sent an M command
    else if (mensagem.startsWith("M=")) {

      M = mensagem.substring(2).toInt();

      Serial.print("M updated by ESP: ");
      Serial.println(M);
    }
  }

  // Check whether communication with the ESP has been lost
  if (millis() - ultimoRecebimento > timeout) {

    Serial.println("ESP-01 OFFLINE. Check the connection.");

    // Reset the timer to avoid printing the message continuously
    ultimoRecebimento = millis();
  }
}

// ============================================================
// DISABLE MOTORS
// ============================================================

void jog() {

  digitalWrite(X_ENABLE_PIN, HIGH);  // Disable X-axis motor

  if (fimY) {
    digitalWrite(Y_ENABLE_PIN, HIGH);  // Disable Y-axis motor if Y is at its limit
  }
}

// ============================================================
// AUTOMATIC HOMING
// ============================================================

void autohome() {

  // Move Y-axis toward the home position
  if (!fimY) {

    digitalWrite(Y_DIR_PIN, HIGH);

    digitalWrite(Y_STEP_PIN, HIGH);
    delayMicroseconds(500);
    digitalWrite(Y_STEP_PIN, LOW);
    delayMicroseconds(500);
  }

  // Once Y reaches home, move X-axis toward its home position
  if (!fimX && fimY) {

    digitalWrite(X_DIR_PIN, HIGH);

    digitalWrite(X_STEP_PIN, HIGH);
    delayMicroseconds(500);
    digitalWrite(X_STEP_PIN, LOW);
    delayMicroseconds(500);
  }

  // Both axes have reached the home position
  if (fimX && fimY) {

    casa = true;

    passoX = 0;
    passoY = 0;

    encoderY = 0;

    Serial.println("Homing completed.");
  }
}

// ============================================================
// CORRECT Y-AXIS POSITION
// ============================================================

void corrigirY() {

  if (passoY < encoderY) {

    darPassosY(1);
  }

  else if (passoY > encoderY) {

    voltar();
  }
}

// ============================================================
// READ COMMANDS FROM COMPUTER
// ============================================================

void lerSerial() {

  if (Serial.available()) {

    entradaSerial = Serial.readStringUntil('\n');
    entradaSerial.trim();

    // Receive G command
    if (entradaSerial.startsWith("G=")) {

      G = entradaSerial.substring(2).toInt();

      Serial.print("G updated through Serial: ");
      Serial.println(G);
    }

    // Receive M command
    else if (entradaSerial.startsWith("M=")) {

      M = entradaSerial.substring(2).toInt();

      Serial.print("M updated through Serial: ");
      Serial.println(M);
    }

    // Start movement test
    else if (entradaSerial == "testar") {

      G = 50;
    }

    // Force Arduino reset
    else if (entradaSerial == "reiniciar") {

      wdt_enable(WDTO_15MS);

      // Wait for the watchdog to reset the Arduino
      while (true) {
      }
    }
  }
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  // Read limit switch states
  // INPUT_PULLUP means LOW = switch activated
  fimY = (digitalRead(endY) == LOW);
  fimX = (digitalRead(endX) == LOW);

  // Check communication with ESP-01
  sinaldevida();

  // Read commands from the computer
  lerSerial();

  // Simulate encoder pulses
  if (digitalRead(decoderY) == LOW) {

    encoderY += 10;
  }

  // Perform homing if it has not been completed
  // G = 7002 disables normal homing
  if (!casa && G != 7002) {

    autohome();
  }

  // Check Y-axis position
  if (passoY != encoderY) {

    corrigirY();
  }

  // Disable motors when G = 7002
  if (G == 7002) {

    jog();

    casa = false;
  }

  // Execute commands only after homing
  if (casa) {

    // Movement test
    if (G == 50) {

      teste();
    }

    // Mode 0 - object placement
    if (M == 0) {

      switch (G) {

        case 1:

          darPassosY(50);

          delay(1000);

          darPassosX(50);

          delay(1000);

          G = 0;

          break;
      }
    }

    // Mode 1 - object removal
    if (M == 1) {

      switch (G) {

        case 1:

          darPassosY(30);

          G = 0;

          break;
      }
    }
  }
}