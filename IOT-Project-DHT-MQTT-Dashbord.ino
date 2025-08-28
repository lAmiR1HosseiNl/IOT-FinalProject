#include "DHT.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define DHTPIN 13
#define DHTTYPE DHT22

const char* ssid = "TestNetwork";
const char* password = "TestNetwork1234";
const char* mqttServer = "broker.emqx.io";

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);
StaticJsonDocument<200> doc;
void setupWifi(){
  delay(10);
  WiFi.begin(ssid, password);
  Serial.print(F("Connecting to Wifi"));
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
}
void connectMQTT() {
  if (!client.connected()) {
    Serial.print("Try To Connect MQTT... ");

    if (client.connect("ESP32ClientARMM")) {
      Serial.println("Connected!");
    } else {
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      Serial.println(" Will retry in next loop iteration.");
    }
  }
}
void setup() {
  Serial.begin(9600);
  Serial.println(F("Show DHT Temp And Humidity On Monitor:"));
  setupWifi();
  client.setServer(mqttServer, 1883);
  dht.begin();
}

void loop() {
  client.loop();
  delay(2000);
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  float temperatureFarenhait = dht.readTemperature(true);

  if (isnan(humidity) || isnan(temperature) || isnan(temperatureFarenhait)) {
    Serial.println(F("Failed To Read From Sensor"));
    return;
  }

  float heatIndexCelsius = dht.computeHeatIndex(temperature, humidity, false);

  doc["humidity"] = humidity;
  doc["temperature"] = temperature;
  doc["temperatureFarenhait"] = temperatureFarenhait;
  doc["heatIndexCelsius"] = heatIndexCelsius;
  doc["timeStamp"] =  millis();
  //Serial.print(F("Humidity: "));
  //Serial.print(humidity);
  //Serial.print(F("%  Temperature: "));
  //erial.print(temperature);
  //Serial.print(F("°C "));
  //Serial.print(temperatureFarenhait);
  //Serial.print(F("°F  Heat index: "));
  //Serial.print(heatIndexCelsius);
  //Serial.print(F("°C \r\n"));
  //Serial.print("===");
  //Serial.print("\n\r Connected To WiFi.");
  //Serial.print("\n\r IP Address:");
  //Serial.print(WiFi.localIP());
  //Serial.print("\n\r === \r\n");
  if (!client.connected()){
    connectMQTT();
  }    
  if (client.connected()){
    char jsonBuffer[256];
    serializeJson(doc, jsonBuffer);
    client.publish("IOTProject4032ARMM", jsonBuffer);
    Serial.println("JSON published: ");
    Serial.println(jsonBuffer);
  }
}
