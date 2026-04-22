// NekoBot
// Your cute desk buddy

#include "draw.h"
#include "gas.h"
#include "wifi_server.h"

// WiFi credentials (set via provisioning or hardcoded)
const char *WIFI_SSID = "YOUR_SSID";
const char *WIFI_PASS = "YOUR_PASSWORD";

void initWiFi()
{
  Serial.println("[NekoBot] Starting WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20)
  {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("");
    Serial.println("[NekoBot] WiFi Connected!");
    Serial.print("[NekoBot] IP address: ");
    Serial.println(WiFi.localIP());
  }
  else
  {
    Serial.println("[NekoBot] WiFi Connection Failed!");
  }
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n[NekoBot] Starting up...");

  gfx->begin(40000000);

  gfx->setRotation(1);

  randomSeed(esp_random());

  initDecompressBuffer();

  drawFrame(EYE_OPEN_MOUTH_CLOSE);

  initGasSensor();

  // Initialize WiFi
  initWiFi();

  // Start TCP server for remote control
  initWiFiServer();

  Serial.println("[NekoBot] Ready!");
}

void loop()
{
  updateGasAlert();
  updateAnimation();

  // Handle TCP client connections and commands
  handleClientConnection();

  delay(10); // Small delay to prevent watchdog timeout
}