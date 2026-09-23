#include <avr/wdt.h>

// Existing Mega/A4988 wiring. Do not change without hardware validation.
const uint8_t X_STEP_PIN = 54, X_DIR_PIN = 55, X_ENABLE_PIN = 38;
const uint8_t Y_STEP_PIN = 60, Y_DIR_PIN = 61, Y_ENABLE_PIN = 56;
const uint8_t Z_STEP_PIN = 46, Z_DIR_PIN = 48, Z_ENABLE_PIN = 62;
const uint8_t END_X_PIN = 3, END_Y_PIN = 14, DECODER_Y_PIN = 11;
const unsigned long COMM_TIMEOUT_MS = 5000;
const unsigned int STEP_DELAY_US = 1000;
const size_t INPUT_BUFFER_SIZE = 64;

enum MachineState { STATE_IDLE, STATE_BUSY, STATE_ERROR };
enum MotionKind { MOTION_NONE, MOTION_HOME, MOTION_MOVE };
MachineState machineState = STATE_IDLE;
MotionKind motionKind = MOTION_NONE;
uint8_t activeAxis = 0;
long positionSteps[3] = {0, 0, 0};
long targetSteps[3] = {0, 0, 0};
bool initialLimitState[2] = {false, false};
bool communicationSeen = false;
bool homed = false;
unsigned long lastPingAt = 0;
char inputBuffer[INPUT_BUFFER_SIZE];
size_t inputLength = 0;

const char* stateName() {
  if (machineState == STATE_BUSY) return "BUSY";
  if (machineState == STATE_ERROR) return "ERROR";
  return "IDLE";
}

bool limitActive(uint8_t axis) {
  if (axis == 0) return digitalRead(END_X_PIN) == LOW;
  if (axis == 1) return digitalRead(END_Y_PIN) == LOW;
  return false;
}

void sendResponse(const char* response) { Serial1.println(response); }

void sendStatus() {
  Serial1.print("STATUS X="); Serial1.print(positionSteps[0]);
  Serial1.print(" Y="); Serial1.print(positionSteps[1]);
  Serial1.print(" Z="); Serial1.print(positionSteps[2]);
  Serial1.print(" HOMED=");
  Serial1.print(homed ? 1 : 0);
  Serial1.print(" STATE="); Serial1.println(stateName());
}

bool parseLong(const char* text, long& value) {
  if (*text == '\0') return false;
  bool negative = false;
  if (*text == '-') { negative = true; ++text; }
  if (*text == '\0') return false;
  long parsed = 0;
  while (*text != '\0') {
    if (*text < '0' || *text > '9') return false;
    const long digit = *text - '0';
    if (parsed > (2147483647L - digit) / 10L) return false;
    parsed = parsed * 10L + digit;
    ++text;
  }
  value = negative ? -parsed : parsed;
  return true;
}

bool parseAxisValue(const char* command, char axisName, long& value) {
  char key[3] = {axisName, '=', '\0'};
  const char* start = strstr(command, key);
  if (start == NULL) return false;
  start += 2;
  char number[16];
  size_t length = 0;
  while (start[length] != '\0' && start[length] != ' ' && length < sizeof(number) - 1) {
    number[length] = start[length]; ++length;
  }
  number[length] = '\0';
  return parseLong(number, value);
}

void setError(const char* error) {
  machineState = STATE_ERROR;
  motionKind = MOTION_NONE;
  sendResponse(error);
}

void pulseAxis(uint8_t axis, bool positive) {
  const uint8_t stepPins[3] = {X_STEP_PIN, Y_STEP_PIN, Z_STEP_PIN};
  const uint8_t dirPins[3] = {X_DIR_PIN, Y_DIR_PIN, Z_DIR_PIN};
  digitalWrite(dirPins[axis], positive ? LOW : HIGH);
  digitalWrite(stepPins[axis], HIGH); delayMicroseconds(STEP_DELAY_US / 2);
  digitalWrite(stepPins[axis], LOW); delayMicroseconds(STEP_DELAY_US / 2);
  positionSteps[axis] += positive ? 1 : -1;
}

void finishMotion() {
  machineState = STATE_IDLE; motionKind = MOTION_NONE; activeAxis = 0; sendResponse("OK");
}

void startHome() {
  machineState = STATE_BUSY; motionKind = MOTION_HOME; activeAxis = 1;
  homed = false;
}

void startMove(const long requested[3]) {
  for (uint8_t axis = 0; axis < 3; ++axis) targetSteps[axis] = requested[axis];
  initialLimitState[0] = limitActive(0); initialLimitState[1] = limitActive(1);
  machineState = STATE_BUSY; motionKind = MOTION_MOVE; activeAxis = 0;
}

void serviceHome() {
  if (activeAxis == 1) {
    if (limitActive(1)) { positionSteps[1] = 0; activeAxis = 0; }
    else { pulseAxis(1, false); return; }
  }
  if (activeAxis == 0) {
    if (limitActive(0)) { positionSteps[0] = 0; homed = true; finishMotion(); }
    else pulseAxis(0, false);
  }
}

void serviceMove() {
  while (activeAxis < 3 && positionSteps[activeAxis] == targetSteps[activeAxis]) ++activeAxis;
  if (activeAxis >= 3) { finishMotion(); return; }
  if (activeAxis < 2 && limitActive(activeAxis) &&
      (!initialLimitState[activeAxis] || targetSteps[activeAxis] < positionSteps[activeAxis])) {
    setError("ERR UNEXPECTED_LIMIT"); return;
  }
  pulseAxis(activeAxis, targetSteps[activeAxis] > positionSteps[activeAxis]);
}

void serviceMotion() {
  if (machineState != STATE_BUSY) return;
  if (motionKind == MOTION_HOME) serviceHome(); else serviceMove();
}

void handleCommand(char* command) {
  if (strcmp(command, "PING") == 0) {
    communicationSeen = true; lastPingAt = millis(); sendResponse("PONG"); return;
  }
  if (strcmp(command, "STATUS?") == 0) { sendStatus(); return; }
  if (strcmp(command, "HOME") == 0) {
    if (machineState == STATE_BUSY) { sendResponse("ERR BUSY"); return; }
    if (!communicationSeen || millis() - lastPingAt > COMM_TIMEOUT_MS) { sendResponse("ERR COMMUNICATION"); return; }
    startHome(); return;
  }
  if (strncmp(command, "MOVE ", 5) == 0) {
    if (machineState == STATE_BUSY) { sendResponse("ERR BUSY"); return; }
    if (machineState == STATE_ERROR) { sendResponse("ERR COMMUNICATION"); return; }
    if (!communicationSeen || millis() - lastPingAt > COMM_TIMEOUT_MS) { sendResponse("ERR COMMUNICATION"); return; }
    if (!homed) { sendResponse("ERR OUT_OF_RANGE"); return; }
    long requested[3];
    if (!parseAxisValue(command, 'X', requested[0]) || !parseAxisValue(command, 'Y', requested[1]) || !parseAxisValue(command, 'Z', requested[2])) {
      sendResponse("ERR INVALID_COMMAND"); return;
    }
    if (requested[0] < 0 || requested[1] < 0 || requested[2] < 0) {
      sendResponse("ERR OUT_OF_RANGE"); return;
    }
    if (requested[2] != positionSteps[2]) {
      sendResponse("ERR OUT_OF_RANGE"); return;
    }
    startMove(requested); return;
  }
  if (strncmp(command, "JOG ", 4) == 0) {
    if (machineState == STATE_BUSY) { sendResponse("ERR BUSY"); return; }
    sendResponse("ERR INVALID_COMMAND"); return;
  }
  sendResponse("ERR INVALID_COMMAND");
}

void readCommands() {
  while (Serial1.available()) {
    const char character = static_cast<char>(Serial1.read());
    if (character == '\n' || character == '\r') {
      if (inputLength == 0) continue;
      inputBuffer[inputLength] = '\0'; handleCommand(inputBuffer); inputLength = 0;
    } else if (inputLength < INPUT_BUFFER_SIZE - 1) inputBuffer[inputLength++] = character;
    else { inputLength = 0; sendResponse("ERR INVALID_COMMAND"); }
  }
}

void setup() {
  wdt_enable(WDTO_2S);
  Serial.begin(9600); Serial1.begin(9600);
  pinMode(END_X_PIN, INPUT_PULLUP); pinMode(END_Y_PIN, INPUT_PULLUP); pinMode(DECODER_Y_PIN, INPUT_PULLUP);
  const uint8_t outputPins[] = {X_STEP_PIN, X_DIR_PIN, X_ENABLE_PIN, Y_STEP_PIN, Y_DIR_PIN, Y_ENABLE_PIN, Z_STEP_PIN, Z_DIR_PIN, Z_ENABLE_PIN};
  for (uint8_t index = 0; index < sizeof(outputPins); ++index) pinMode(outputPins[index], OUTPUT);
  digitalWrite(X_ENABLE_PIN, LOW); digitalWrite(Y_ENABLE_PIN, LOW); digitalWrite(Z_ENABLE_PIN, LOW);
  digitalWrite(X_STEP_PIN, LOW); digitalWrite(Y_STEP_PIN, LOW); digitalWrite(Z_STEP_PIN, LOW);
  Serial.println("SmartStock Arduino protocol ready.");
}

void loop() {
  wdt_reset();
  readCommands();
  serviceMotion();
  if (communicationSeen && millis() - lastPingAt > COMM_TIMEOUT_MS && machineState == STATE_BUSY) setError("ERR COMMUNICATION");
}
