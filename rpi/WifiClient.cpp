#include <ESP8266WiFi.h>  // WiFi library for ESP8266
#include "WifiClient.h"
#include <Arduino.h>      // needed for Serial and String

WifiClient::WifiClient(char *ssid, char *pass)
{
  _ssid = ssid;
  _pass = pass;
}

void WifiClient::connect()
{
  Serial.print("Connecting to WPA SSID [" + String(_ssid) + "]..." + "\n");
  WiFi.begin(_ssid, _pass);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address is: ");
  Serial.println(WiFi.localIP());
}

int WifiClient::getStatus()
{
  return WiFi.status();
}
