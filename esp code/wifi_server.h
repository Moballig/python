// ============================================================
// wifi_server.h
//
// TCP Server for NekoBot to receive commands from DeskBuddy client
// Listens on port 9090 for JSON-formatted control messages
// ============================================================

#ifndef WIFI_SERVER_H
#define WIFI_SERVER_H

#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include "nekobot_protocol.h"
#include "draw.h"
#include "gas.h"

WiFiServer server(NEKOBOT_PORT);
WiFiClient serverClient;
unsigned long lastClientCheck = 0;

extern int animationMode;
extern int idleSubstate;

struct NekoState
{
    int currentExpression;
    int currentAnimationMode;
    int gasLevel;
    bool buzzerActive;
};

NekoState nekoBotState = {0, 0, 0, false};

void initWiFiServer()
{
    server.begin(NEKOBOT_PORT);
    Serial.println("[WiFi Server] Listening on port " + String(NEKOBOT_PORT));
}

void handleClientConnection()
{
    // Check for new client
    if (server.hasClient())
    {
        if (serverClient && serverClient.connected())
        {
            serverClient.stop();
        }
        serverClient = server.available();
        Serial.println("[WiFi Server] New client connected");
    }

    // Process incoming data
    if (serverClient && serverClient.connected())
    {
        while (serverClient.available())
        {
            String jsonStr = serverClient.readStringUntil('\n');
            if (jsonStr.length() > 0)
            {
                processCommand(jsonStr);
            }
        }
    }
}

void processCommand(String jsonStr)
{
    StaticJsonDocument<NEKOBOT_BUFFER_SIZE> doc;
    DeserializationError error = deserializeJson(doc, jsonStr);

    if (error)
    {
        Serial.println("[WiFi Server] JSON parse error: " + String(error.c_str()));
        sendError("json_parse_error");
        return;
    }

    const char *cmd = doc["cmd"];
    if (!cmd)
    {
        sendError("missing_cmd");
        return;
    }

    String cmdStr(cmd);

    if (cmdStr == "ping")
    {
        sendResponse("pong", "ok");
    }
    else if (cmdStr == "status")
    {
        sendStatus();
    }
    else if (cmdStr == "expr")
    {
        int exprId = doc["id"] | -1;
        if (exprId >= 0 && exprId < 5)
        {
            drawFrame(exprId);
            nekoBotState.currentExpression = exprId;
            animationMode = ANIM_CUSTOM; // Lock to this expression
            sendResponse("expr_set", "ok");
        }
        else
        {
            sendError("invalid_expr_id");
        }
    }
    else if (cmdStr == "gas")
    {
        int gasValue = analogRead(GAS_SENSOR_PIN);
        nekoBotState.gasLevel = gasValue;
        sendGasStatus(gasValue);
    }
    else if (cmdStr == "anim")
    {
        int mode = doc["mode"] | -1;
        if (mode >= 0 && mode <= 3)
        {
            animationMode = mode;
            nekoBotState.currentAnimationMode = mode;

            // Reset animation state when switching modes
            if (mode == ANIM_IDLE)
            {
                idleSubstate = 0;
            }

            sendResponse("anim_set", "ok");
        }
        else
        {
            sendError("invalid_anim_mode");
        }
    }
    else if (cmdStr == "buzzer")
    {
        int state = doc["state"] | -1;
        if (state == 0 || state == 1)
        {
            setBuzzer(state == 1);
            nekoBotState.buzzerActive = (state == 1);
            sendResponse("buzzer_set", "ok");
        }
        else
        {
            sendError("invalid_buzzer_state");
        }
    }
    else if (cmdStr == "reset")
    {
        animationMode = ANIM_IDLE;
        idleSubstate = 0;
        setBuzzer(false);
        nekoBotState.buzzerActive = false;
        sendResponse("reset", "ok");
    }
    else if (cmdStr == "alert")
    {
        const char *title = doc["title"] | "Alert";
        const char *body = doc["body"] | "";
        
        // Stop normal animation
        animationMode = ANIM_PAUSE;
        
        gfx->fillScreen(BLACK);
        
        gfx->setCursor(10, 20);
        gfx->setTextColor(RED);
        gfx->setTextSize(3);
        gfx->println(title);
        
        gfx->setCursor(10, 60);
        gfx->setTextColor(WHITE);
        gfx->setTextSize(2);
        gfx->println(body);
        
        sendResponse("alert_shown", "ok");
    }
    else
    {
        sendError("unknown_command");
    }
}

void sendResponse(const char *type, const char *status)
{
    if (!serverClient || !serverClient.connected())
        return;

    StaticJsonDocument<128> doc;
    doc["type"] = type;
    doc["status"] = status;

    String json;
    serializeJson(doc, json);
    serverClient.println(json);
}

void sendStatus()
{
    if (!serverClient || !serverClient.connected())
        return;

    StaticJsonDocument<256> doc;
    doc["type"] = "status";
    doc["expr"] = nekoBotState.currentExpression;
    doc["anim"] = nekoBotState.currentAnimationMode;
    doc["gas_level"] = analogRead(GAS_SENSOR_PIN);
    doc["buzzer"] = nekoBotState.buzzerActive ? 1 : 0;
    doc["uptime_ms"] = millis();

    String json;
    serializeJson(doc, json);
    serverClient.println(json);
}

void sendGasStatus(int gasValue)
{
    if (!serverClient || !serverClient.connected())
        return;

    StaticJsonDocument<128> doc;
    doc["type"] = "gas";
    doc["value"] = gasValue;
    doc["raw_adc"] = gasValue;

    String json;
    serializeJson(doc, json);
    serverClient.println(json);
}

void sendError(const char *error)
{
    if (!serverClient || !serverClient.connected())
        return;

    StaticJsonDocument<128> doc;
    doc["type"] = "error";
    doc["error"] = error;

    String json;
    serializeJson(doc, json);
    serverClient.println(json);
}

#endif
