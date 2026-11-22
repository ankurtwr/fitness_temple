/* ═══════════════════════════════════════════════════════════
   FITNESS TEMPLE — ESP32 RFID Attendance Reader Firmware
   Hardware:
     - ESP32 DevKit V1
     - RC522 13.56MHz RFID Reader (SPI)
     - Green & Red Status LEDs (Active HIGH)
     - Active Buzzer (Active HIGH)

   Libraries required in Arduino IDE:
     - MFRC522 by GithubCommunity (v1.4.10+)
     - ArduinoJson by Benoit Blanchon (v6.21.0+)
     - Built-in: WiFi, HTTPClient, SPI, time.h
   ═══════════════════════════════════════════════════════════ */

#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <time.h>

// ═══════════════════════════════════════════════════════════
//  Configuration — Update with your network credentials
// ═══════════════════════════════════════════════════════════

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Server endpoint — use the LAN IP of your server running Docker/FastAPI
const char* SERVER_URL    = "http://192.168.1.100:8000/scan";

// Device key — must match the key seeded in database (default: testdevice123)
const char* DEVICE_KEY    = "testdevice123";

// NTP Server for timestamp sync (IST: UTC + 5h30m)
const char* NTP_SERVER    = "pool.ntp.org";
const long  GMT_OFFSET_SEC      = 19800; // 5.5 hours * 3600
const int   DAYLIGHT_OFFSET_SEC = 0;     // India does not observe DST

// ═══════════════════════════════════════════════════════════
//  Pin Definitions
// ═══════════════════════════════════════════════════════════

// RC522 SPI Pins (Standard VSPI on ESP32)
#define SS_PIN          5   // SDA / SS
#define RST_PIN         22  // RST
#define SCK_PIN         18  // SCK
#define MOSI_PIN        23  // MOSI
#define MISO_PIN        19  // MISO

// Status Output Pins
#define PIN_LED_GREEN   26
#define PIN_LED_RED     27
#define PIN_BUZZER      25

// ═══════════════════════════════════════════════════════════
//  Constants & Objects
// ═══════════════════════════════════════════════════════════

MFRC522 mfrc522(SS_PIN, RST_PIN);

// Debounce prevention: Ignore same card tapped within 2 seconds
String lastUid = "";
unsigned long lastTapTime = 0;
const unsigned long DEBOUNCE_MS = 2000;

// Offline queue for resilient attendance when WiFi/Server drops
struct OfflineScan {
    char uid[24];
    time_t timestamp;
};

const int MAX_OFFLINE_QUEUE = 50;
OfflineScan offlineQueue[MAX_OFFLINE_QUEUE];
int queueHead = 0;
int queueTail = 0;
int queueCount = 0;

// ═══════════════════════════════════════════════════════════
//  Audio & Visual Feedback Helpers
// ═══════════════════════════════════════════════════════════

void beep(int durationMs, int frequency = 2000) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(durationMs);
    digitalWrite(PIN_BUZZER, LOW);
}

void feedbackMarked() {
    // Attendance Marked: Solid Green LED + 1 crisp beep
    digitalWrite(PIN_LED_GREEN, HIGH);
    beep(150);
    delay(1350);
    digitalWrite(PIN_LED_GREEN, LOW);
}

void feedbackAlreadyMarked() {
    // Already Checked In Today: Green LED 2 pulses + 2 short beeps
    for (int i = 0; i < 2; i++) {
        digitalWrite(PIN_LED_GREEN, HIGH);
        digitalWrite(PIN_BUZZER, HIGH);
        delay(100);
        digitalWrite(PIN_LED_GREEN, LOW);
        digitalWrite(PIN_BUZZER, LOW);
        delay(100);
    }
}

void feedbackLinked() {
    // Card Linked to New Member: Alternate Green/Red blinks + 3 celebratory beeps
    for (int i = 0; i < 3; i++) {
        digitalWrite(PIN_LED_GREEN, HIGH);
        digitalWrite(PIN_LED_RED, LOW);
        digitalWrite(PIN_BUZZER, HIGH);
        delay(100);
        digitalWrite(PIN_LED_GREEN, LOW);
        digitalWrite(PIN_LED_RED, HIGH);
        digitalWrite(PIN_BUZZER, LOW);
        delay(100);
    }
    digitalWrite(PIN_LED_RED, LOW);
}

void feedbackExpired() {
    // Membership Expired: 3 Red pulses + 3 warning beeps
    for (int i = 0; i < 3; i++) {
        digitalWrite(PIN_LED_RED, HIGH);
        digitalWrite(PIN_BUZZER, HIGH);
        delay(200);
        digitalWrite(PIN_LED_RED, LOW);
        digitalWrite(PIN_BUZZER, LOW);
        delay(150);
    }
}

void feedbackInactive() {
    // Deactivated (Lost/Stolen): Solid Red LED for 2s + 1 long warning buzz
    digitalWrite(PIN_LED_RED, HIGH);
    digitalWrite(PIN_BUZZER, HIGH);
    delay(800);
    digitalWrite(PIN_BUZZER, LOW);
    delay(1200);
    digitalWrite(PIN_LED_RED, LOW);
}

void feedbackUnknownOrRejected() {
    // Unknown card or Rejected device key: 5 rapid Red flashes + rapid clicks
    for (int i = 0; i < 5; i++) {
        digitalWrite(PIN_LED_RED, HIGH);
        digitalWrite(PIN_BUZZER, HIGH);
        delay(80);
        digitalWrite(PIN_LED_RED, LOW);
        digitalWrite(PIN_BUZZER, LOW);
        delay(80);
    }
}

void feedbackOfflineQueued() {
    // Stored in offline buffer: Both LEDs pulse twice
    for (int i = 0; i < 2; i++) {
        digitalWrite(PIN_LED_GREEN, HIGH);
        digitalWrite(PIN_LED_RED, HIGH);
        beep(80);
        digitalWrite(PIN_LED_GREEN, LOW);
        digitalWrite(PIN_LED_RED, LOW);
        delay(100);
    }
}

// ═══════════════════════════════════════════════════════════
//  Offline Queue Management
// ═══════════════════════════════════════════════════════════

void enqueueOffline(const String& uid, time_t t) {
    if (queueCount < MAX_OFFLINE_QUEUE) {
        strncpy(offlineQueue[queueTail].uid, uid.c_str(), sizeof(offlineQueue[queueTail].uid) - 1);
        offlineQueue[queueTail].timestamp = t;
        queueTail = (queueTail + 1) % MAX_OFFLINE_QUEUE;
        queueCount++;
        Serial.printf("[OFFLINE] Card %s queued. Queue size: %d\n", uid.c_str(), queueCount);
    } else {
        Serial.println("[OFFLINE] Queue full! Dropping oldest scan.");
        queueHead = (queueHead + 1) % MAX_OFFLINE_QUEUE;
        queueCount--;
        enqueueOffline(uid, t);
    }
}

String getIsoTimestamp(time_t rawtime) {
    if (rawtime <= 100000) return "";
    struct tm* timeinfo = gmtime(&rawtime);
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", timeinfo);
    return String(buf);
}

// ═══════════════════════════════════════════════════════════
//  Server Communication (/scan)
// ═══════════════════════════════════════════════════════════

bool sendScanRequest(const String& uid, const String& isoTimestamp, String& outStatus, String& outName) {
    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }

    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(1800); // Fast timeout to protect responsiveness

    StaticJsonDocument<256> reqDoc;
    reqDoc["uid"] = uid;
    reqDoc["device_key"] = DEVICE_KEY;
    if (isoTimestamp.length() > 0) {
        reqDoc["scanned_at"] = isoTimestamp;
    }

    String requestBody;
    serializeJson(reqDoc, requestBody);

    unsigned long startMs = millis();
    int httpCode = http.POST(requestBody);
    unsigned long elapsedMs = millis() - startMs;

    bool success = false;
    if (httpCode == 200) {
        String payload = http.getString();
        StaticJsonDocument<512> resDoc;
        DeserializationError error = deserializeJson(resDoc, payload);

        if (!error) {
            outStatus = resDoc["status"].as<String>();
            outName = resDoc["name"] | "Member";
            Serial.printf("[SCAN] %s -> status=%s, name=%s (took %lums)\n",
                          uid.c_str(), outStatus.c_str(), outName.c_str(), elapsedMs);
            success = true;
        } else {
            Serial.println("[JSON] Parse error in response");
        }
    } else {
        Serial.printf("[HTTP] POST failed, code: %d (took %lums)\n", httpCode, elapsedMs);
    }

    http.end();
    return success;
}

void flushOfflineQueue() {
    if (queueCount == 0 || WiFi.status() != WL_CONNECTED) return;

    Serial.printf("[OFFLINE] Flushing %d queued scans...\n", queueCount);
    while (queueCount > 0 && WiFi.status() == WL_CONNECTED) {
        String uid = String(offlineQueue[queueHead].uid);
        String isoTime = getIsoTimestamp(offlineQueue[queueHead].timestamp);
        String status, name;

        if (sendScanRequest(uid, isoTime, status, name)) {
            queueHead = (queueHead + 1) % MAX_OFFLINE_QUEUE;
            queueCount--;
            delay(100); // small delay between queued pushes
        } else {
            Serial.println("[OFFLINE] Flush interrupted, will retry later.");
            break;
        }
    }
}

// ═══════════════════════════════════════════════════════════
//  WiFi & Setup
// ═══════════════════════════════════════════════════════════

void setupWiFi() {
    Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi Connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());

        // Synchronize NTP time
        configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);
        Serial.println("NTP time sync initiated.");
    } else {
        Serial.println("\nWiFi connection failed. Will operate in offline queue mode.");
    }
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println("\n═══════════════════════════════════════════");
    Serial.println("  FITNESS TEMPLE — ESP32 RFID ATTENDANCE");
    Serial.println("═══════════════════════════════════════════");

    // Configure IO Pins
    pinMode(PIN_LED_GREEN, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);

    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_RED, LOW);
    digitalWrite(PIN_BUZZER, LOW);

    // Initial power-on chirp
    beep(100);

    // Initialize SPI & RC522
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
    mfrc522.PCD_Init();
    delay(50);
    mfrc522.PCD_DumpVersionToSerial();

    // Connect to WiFi
    setupWiFi();
    Serial.println("Ready to scan cards.");
}

// ═══════════════════════════════════════════════════════════
//  Main Loop
// ═══════════════════════════════════════════════════════════

void loop() {
    // 1. Maintain WiFi connection in background
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastReconnectAttempt = 0;
        if (millis() - lastReconnectAttempt > 10000) {
            lastReconnectAttempt = millis();
            WiFi.reconnect();
        }
    } else {
        // Flush any queued offline scans if WiFi is alive
        if (queueCount > 0) {
            flushOfflineQueue();
        }
    }

    // 2. Check for RFID card present
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        delay(50);
        return;
    }

    // 3. Extract Card UID as uppercase Hex String (e.g., "4A2B8C1D")
    String uid = "";
    for (byte i = 0; i < mfrc522.uid.byteCount; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(mfrc522.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();

    // Halt card communication so it doesn't continuously trigger
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();

    // 4. Debounce check
    unsigned long now = millis();
    if (uid == lastUid && (now - lastTapTime < DEBOUNCE_MS)) {
        Serial.printf("[DEBOUNCE] Ignoring duplicate tap of %s\n", uid.c_str());
        return;
    }
    lastUid = uid;
    lastTapTime = now;

    Serial.printf("\n[TAP] Card UID: %s\n", uid.c_str());

    // 5. Transmit tap or queue offline
    String status = "";
    String memberName = "";

    if (WiFi.status() == WL_CONNECTED) {
        bool ok = sendScanRequest(uid, "", status, memberName);
        if (ok) {
            // Apply corresponding hardware feedback based on server response
            if (status == "marked") {
                feedbackMarked();
            } else if (status == "already_marked") {
                feedbackAlreadyMarked();
            } else if (status == "linked") {
                feedbackLinked();
            } else if (status == "expired") {
                feedbackExpired();
            } else if (status == "inactive") {
                feedbackInactive();
            } else {
                feedbackUnknownOrRejected();
            }
            return;
        }
    }

    // If WiFi disconnected or server unreachable, store in queue & give offline feedback
    time_t nowTime;
    time(&nowTime);
    enqueueOffline(uid, nowTime);
    feedbackOfflineQueued();
}
