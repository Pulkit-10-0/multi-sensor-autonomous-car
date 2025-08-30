#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoOTA.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// ====== WiFi Credentials ======
const char* ssid     = "Raze 2.4G";
const char* password = "123Wolfy123";

// Web server runs on port 80
WebServer server(80);

// ===== Pin Mapping =====
#define TRIG_PIN 5
#define ECHO_PIN 18
#define IN1 26
#define IN2 27
#define IN3 14
#define IN4 12
#define IR_PIN 34
#define SERVO_PIN 25
#define PIR_PIN 35
#define DHT_PIN 4
#define FLAME_PIN 32
#define SDA_PIN 21
#define SCL_PIN 22

// ===== Sensors =====
long duration;
float distance;
DHT dht(DHT_PIN, DHT11);
Adafruit_MPU6050 mpu;

// ===== Global flag for Autonomous Mode =====
bool autonomousMode = false;

// ===== Distance Function (20 cm cap) =====
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return 20.0;

  distance = duration * 0.034 / 2;
  if (distance > 20.0) distance = 20.0;
  return distance;
}

// ===== Motor Functions =====
void forward() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}
void backward() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}
void left() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}
void right() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}
void stopCar() {
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

// ===== JSON Data Endpoint =====
void handleData() {
  float dist = getDistance();
  int irVal = digitalRead(IR_PIN);
  int flameVal = digitalRead(FLAME_PIN);
  int pirVal = digitalRead(PIR_PIN);
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  sensors_event_t a, g, temp_mpu;
  mpu.getEvent(&a, &g, &temp_mpu);

  String json = "{";
  json += "\"distance\":" + String(dist) + ",";
  json += "\"ir\":\"" + String(irVal == 0 ? "Object Detected" : "Clear") + "\",";
  json += "\"motion\":\"" + String(pirVal == 1 ? "Motion Detected" : "No Motion") + "\",";
  json += "\"temperature\":" + String(temp) + ",";
  json += "\"humidity\":" + String(hum) + ",";
  json += "\"flame\":\"" + String(flameVal == 0 ? "Flame Detected" : "No Flame") + "\",";
  json += "\"accel\":\"X=" + String(a.acceleration.x) + " Y=" + String(a.acceleration.y) + " Z=" + String(a.acceleration.z) + "\",";
  json += "\"gyro\":\"X=" + String(g.gyro.x) + " Y=" + String(g.gyro.y) + " Z=" + String(g.gyro.z) + "\",";
  json += "\"autonomous\":\"" + String(autonomousMode ? "ENABLED" : "DISABLED") + "\"";
  json += "}";
  
  server.send(200, "application/json", json);
}

// ===== Web Page =====
void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'>";
  html += "<title>System Dashboard</title>";
  html += "<style>";
  html += "body { font-family: Arial, sans-serif; background:#f4f6f9; margin:20px; color:#222; }";
  html += "h1 { text-align:center; font-weight:500; margin-bottom:25px; }";
  html += ".dashboard { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px; margin-bottom:20px; }";
  html += ".card { background:white; border-radius:14px; padding:20px; box-shadow:0 3px 8px rgba(0,0,0,0.1); }";
  html += ".label { color:#555; font-weight:600; font-size:1.1em; }";
  html += ".value { font-size:1.3em; font-weight:bold; color:#111; display:block; margin-top:5px; }";
  html += ".controls { text-align:center; margin-top:25px; }";
  html += "button { padding:14px 22px; margin:8px; border:none; border-radius:10px; font-weight:600; cursor:pointer; transition:0.3s; font-size:1em; }";
  html += ".forward { background:#28a745; color:white; }";
  html += ".backward { background:#dc3545; color:white; }";
  html += ".left,.right { background:#007bff; color:white; }";
  html += ".stop { background:#343a40; color:white; }";
  html += ".toggle { background:#ff9800; color:white; }";
  html += ".status { font-weight:bold; margin-top:10px; font-size:1.1em; }";
  html += ".active { color:green; }";
  html += ".inactive { color:red; }";
  html += "</style></head><body>";

  html += "<h1>System Dashboard</h1>";

  // ====== Sensor Data ======
  html += "<div class='dashboard'>";
  html += "<div class='card'><span class='label'>Ultrasonic:</span> <span class='value' id='distance'>--</span></div>";
  html += "<div class='card'><span class='label'>IR Obstacle:</span> <span class='value' id='ir'>--</span></div>";
  html += "<div class='card'><span class='label'>Motion Sensor:</span> <span class='value' id='motion'>--</span></div>";
  html += "<div class='card'><span class='label'>Temperature:</span> <span class='value' id='temperature'>--</span></div>";
  html += "<div class='card'><span class='label'>Humidity:</span> <span class='value' id='humidity'>--</span></div>";
  html += "<div class='card'><span class='label'>Flame Sensor:</span> <span class='value' id='flame'>--</span></div>";
  html += "<div class='card'><span class='label'>Gyro Accel:</span> <span class='value' id='accel'>--</span></div>";
  html += "<div class='card'><span class='label'>Gyro Rotation:</span> <span class='value' id='gyro'>--</span></div>";
  html += "</div>";

  // ====== Controls ======
  html += "<h2 style='text-align:center;'>Controls</h2>";
  html += "<div class='controls'>";
  html += "<a href='/forward'><button class='forward'>Forward</button></a> ";
  html += "<a href='/backward'><button class='backward'>Backward</button></a> ";
  html += "<a href='/left'><button class='left'>Left</button></a> ";
  html += "<a href='/right'><button class='right'>Right</button></a> ";
  html += "<a href='/stop'><button class='stop'>Stop</button></a>";
  html += "</div>";

  // ====== Autonomous Toggle ======
  html += "<div class='controls'>";
  html += "<p class='status' id='autonomous'>--</p>";
  html += "<a href='/enableAuto'><button class='toggle'>Enable Autonomous</button></a>";
  html += "<a href='/disableAuto'><button class='toggle'>Disable Autonomous</button></a>";
  html += "</div>";

  // ====== JavaScript for Live Updates ======
  html += "<script>";
  html += "function updateData(){fetch('/data').then(r=>r.json()).then(d=>{";
  html += "document.getElementById('distance').innerText=d.distance+' cm';";
  html += "document.getElementById('ir').innerText=d.ir;";
  html += "document.getElementById('motion').innerText=d.motion;";
  html += "document.getElementById('temperature').innerText=d.temperature+' °C';";
  html += "document.getElementById('humidity').innerText=d.humidity+' %';";
  html += "document.getElementById('flame').innerText=d.flame;";
  html += "document.getElementById('accel').innerText=d.accel;";
  html += "document.getElementById('gyro').innerText=d.gyro;";
  html += "document.getElementById('autonomous').innerText='Autonomous Mode: '+d.autonomous;";
  html += "document.getElementById('autonomous').className=(d.autonomous==='ENABLED'?'status active':'status inactive');";
  html += "});}";
  html += "setInterval(updateData,1000); updateData();";
  html += "</script>";

  html += "</body></html>";

  server.send(200, "text/html", html);
}

// ===== Control Handlers =====
void handleForward() { forward(); server.sendHeader("Location", "/"); server.send(303); }
void handleBackward() { backward(); server.sendHeader("Location", "/"); server.send(303); }
void handleLeft() { left(); server.sendHeader("Location", "/"); server.send(303); }
void handleRight() { right(); server.sendHeader("Location", "/"); server.send(303); }
void handleStop() { stopCar(); server.sendHeader("Location", "/"); server.send(303); }
void handleEnableAuto() { autonomousMode = true; server.sendHeader("Location", "/"); server.send(303); }
void handleDisableAuto() { autonomousMode = false; server.sendHeader("Location", "/"); server.send(303); }

void setup() {
  Serial.begin(115200);

  // Motor pins
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  // Sensor pins
  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);
  pinMode(IR_PIN, INPUT); pinMode(PIR_PIN, INPUT);
  pinMode(FLAME_PIN, INPUT);

  stopCar();

  // Init sensors
  dht.begin();
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!mpu.begin()) {
    Serial.println("MPU6050 not found!");
    while (1) delay(10);
  }

  // WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // OTA
  ArduinoOTA.begin();

  // Web server routes
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/forward", handleForward);
  server.on("/backward", handleBackward);
  server.on("/left", handleLeft);
  server.on("/right", handleRight);
  server.on("/stop", handleStop);
  server.on("/enableAuto", handleEnableAuto);
  server.on("/disableAuto", handleDisableAuto);
  server.begin();
}

void loop() {
  server.handleClient();
  ArduinoOTA.handle();
}
