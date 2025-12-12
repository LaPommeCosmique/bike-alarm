#include "MqttClient.h"
#include "WifiClient.h"
#include <ArduinoJson.h>
#include <Wire.h>

char *ssid_wifi = "iPad (2)";
char *pass_wifi = "Mgh$J65k9po";

const char *mqtt_broker_ip = "172.20.10.3";
const int mqtt_broker_port = 1883;
const char *client_id = "subscriber_sensors";
const int num_subscribe_topics = 3;
String subscribe_topics[num_subscribe_topics] = {"lock_status_led_topic","buzzer_topic", "topic"};
uint8_t leds[3]={D15,D14,D13}; // green , yellow , red
WifiClient wifi_client(ssid_wifi , pass_wifi);
MqttClient mqtt_client(mqtt_broker_ip , mqtt_broker_port , subscribe_topics , num_subscribe_topics);

DynamicJsonDocument msg_doc (1024);
float prev_temp = 0;
int led2_state = LOW;
long led2_interval = 1000000;
unsigned long prev_millis = 0;
String lock_status = "on";

void setup ()
{
    Serial.begin (115200);
    wifi_client.connect ();
    mqtt_client.connect(client_id);
    for (int i = 0; i < (sizeof(leds) / sizeof(leds [0])); i++)
    pinMode(leds[i], OUTPUT);
}

void loop ()
{
    mqtt_client.check_connection(client_id);
    String msg = mqtt_client.get_msg ();
    String topic = mqtt_client.get_topic ();
    unsigned long current_millis = millis ();
    deserializeJson(msg_doc , msg);
    // if (topic != "")
    // {
    //     Serial.println(topic);
    // }
    if (topic == subscribe_topics [0])
    {
        lock_status = msg_doc["status"].as<String>();
        if(lock_status == "off"){
            led2_interval = 1000000;
            digitalWrite(leds [1], LOW);
            digitalWrite(leds [0], LOW);
        }
        else if (lock_status == "on")
            digitalWrite(leds [1], HIGH);

    }
    else if (topic == subscribe_topics [1])
    {
        String buzzer = msg_doc["buzzer"];
        if (lock_status == "off")
            led2_interval = 1000000;
        else if (buzzer == "tamper" && lock_status == "on")
            led2_interval = 2000;
        else if (buzzer == "compromised" && lock_status == "on")
            led2_interval = 500;
        else {
            led2_interval = 1000000;
            digitalWrite(leds [0], LOW);
        }
    }
    else if (topic == subscribe_topics [2])
    {
    }
    else
    { // ignore
    }
    if (current_millis - prev_millis >= led2_interval)
        {
            prev_millis = current_millis;
            if (led2_state == LOW)
            led2_state = HIGH;
        else
            led2_state = LOW;
            digitalWrite(leds [0], led2_state);
        }
    mqtt_client.reset_msg ();
}
