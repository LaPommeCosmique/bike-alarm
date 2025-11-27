#include "WifiClient.h"
#include "MqttClient.h"
#include <Wire.h>
#include <ArduinoJson.h>

#define SENSOR_PIN D2

// ---------------- WIFI + MQTT CONFIG ----------------
char *ssid_wifi = "iPad (2)";
char *pass_wifi = "Mgh$J65k9po";

const char *mqtt_broker_ip = "172.20.10.2";
const int mqtt_broker_port = 1883;
const char *client_id = "subscriber_sensors";

// MQTT topics
char *imu_topic = "imu_topic";
char *lock_topic = "lock_topic";

WifiClient wifi_client(ssid_wifi, pass_wifi);
MqttClient mqtt_client(mqtt_broker_ip, mqtt_broker_port);

// ---------------- MPU6050 RAW & ANGLES ----------------
int16_t Acc_rawX, Acc_rawY, Acc_rawZ;
int16_t Gyr_rawX, Gyr_rawY, Gyr_rawZ;

float roll = 0, pitch = 0, yaw = 0;
float accRoll, accPitch;
float gyroRollRate, gyroPitchRate, gyroYawRate;

float tPrev, tNow, elapsedTime;

const float rad_to_deg = 180.0 / 3.141592654;

// JSON
DynamicJsonDocument imu_doc(1024);
DynamicJsonDocument lock_doc(256);

void setup()
{
    Serial.begin(115200);
    delay(200);
    Serial.println("MPU6050 IMU Publisher Starting...");

    pinMode(SENSOR_PIN, INPUT);

    // ---- WiFi + MQTT ----
    wifi_client.connect();
    mqtt_client.connect(client_id);

    // ---- Initialize I2C ----
    Wire.begin(D14, D15); // SDA, SCL
    delay(50);

    // ---- Wake up MPU6050 ----
    Wire.beginTransmission(0x68);
    Wire.write(0x6B);
    Wire.write(0);
    Wire.endTransmission(true);

    tNow = millis();
}

void readMPU6050()
{
    // ---------- ACCEL ----------
    Wire.beginTransmission(0x68);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(0x68, 6, true);

    Acc_rawX = Wire.read() << 8 | Wire.read();
    Acc_rawY = Wire.read() << 8 | Wire.read();
    Acc_rawZ = Wire.read() << 8 | Wire.read();

    float ax = Acc_rawX / 16384.0;
    float ay = Acc_rawY / 16384.0;
    float az = Acc_rawZ / 16384.0;

    accRoll = atan2(ay, az) * rad_to_deg;
    accPitch = atan2(-ax, sqrt(ay * ay + az * az)) * rad_to_deg;

    // ---------- GYRO ----------
    Wire.beginTransmission(0x68);
    Wire.write(0x43);
    Wire.endTransmission(false);
    Wire.requestFrom(0x68, 6, true);

    Gyr_rawX = Wire.read() << 8 | Wire.read();
    Gyr_rawY = Wire.read() << 8 | Wire.read();
    Gyr_rawZ = Wire.read() << 8 | Wire.read();

    gyroRollRate = Gyr_rawX / 131.0;
    gyroPitchRate = Gyr_rawY / 131.0;
    gyroYawRate = Gyr_rawZ / 131.0;
}

void complementaryFilter()
{
    roll = 0.98 * (roll + gyroRollRate * elapsedTime) + 0.02 * accRoll;
    pitch = 0.98 * (pitch + gyroPitchRate * elapsedTime) + 0.02 * accPitch;

    // yaw from gyro only
    yaw += gyroYawRate * elapsedTime;
}

void loop()
{
    mqtt_client.check_connection(client_id);

    // ----- LOCK / CIRCUIT STATUS -----
    int state = digitalRead(SENSOR_PIN);

    // LOW  → circuit closed → true
    // HIGH → circuit open   → false
    bool lock_state = (state == LOW);

    Serial.print("LOCK STATE: ");
    Serial.println(lock_state ? "CLOSED (true)" : "OPEN (false)");

    // ----- Publish lock boolean -----
    lock_doc.clear();
    lock_doc["id"] = client_id;
    lock_doc["lock_state"] = lock_state; // BOOLEAN HERE

    char lock_out[200];
    serializeJson(lock_doc, lock_out);
    mqtt_client.publish_message(lock_topic, lock_out);

    // ----- IMU TIMING -----
    tPrev = tNow;
    tNow = millis();
    elapsedTime = (tNow - tPrev) / 1000.0;

    readMPU6050();
    complementaryFilter();

    // ----- IMU MQTT -----
    imu_doc.clear();
    imu_doc["id"] = client_id;
    imu_doc["roll"] = roll;
    imu_doc["pitch"] = pitch;
    imu_doc["yaw"] = yaw;

    imu_doc["acc_x"] = Acc_rawX;
    imu_doc["acc_y"] = Acc_rawY;
    imu_doc["acc_z"] = Acc_rawZ;

    imu_doc["gyro_x"] = Gyr_rawX;
    imu_doc["gyro_y"] = Gyr_rawY;
    imu_doc["gyro_z"] = Gyr_rawZ;

    char imu_out[500];
    serializeJson(imu_doc, imu_out);
    mqtt_client.publish_message(imu_topic, imu_out);

    delay(1000);
}
