// ============================================================
// nekobot_protocol.h
//
// Communication protocol between DeskBuddy client and NekoBot ESP32
// Uses JSON over TCP on port 9090
// ============================================================

#ifndef NEKOBOT_PROTOCOL_H
#define NEKOBOT_PROTOCOL_H

#include <Arduino.h>

// ---- Protocol Definitions ----
#define NEKOBOT_PORT 9090
#define NEKOBOT_BUFFER_SIZE 512

// ---- Message Types ----
enum MessageType
{
    MSG_PING = 0,           // Heartbeat
    MSG_STATUS = 1,         // Query status
    MSG_SET_ANIMATION = 2,  // Set animation mode
    MSG_GET_GAS_LEVEL = 3,  // Query gas sensor value
    MSG_SET_EXPRESSION = 4, // Set facial expression
    MSG_CONTROL = 5,        // General control command
    MSG_ALERT = 6,          // Send notification alert (NEW)
    MSG_RESPONSE = 100      // Response to query
};

// ---- Alert Categories ----
enum AlertCategory
{
    ALERT_DEV = 0,     // Compilation errors, build failures
    ALERT_SYSTEM = 1,  // CPU temp, RAM usage, disk issues
    ALERT_WELLNESS = 2 // Drink water, stand up, stretch
};

// ---- Alert Urgency ----
enum AlertUrgency
{
    URGENCY_LOW = 1,    // Blue (#2979FF) - Info, reminders
    URGENCY_MEDIUM = 2, // Orange (#FF8C00) - Warnings
    URGENCY_HIGH = 3    // Red (#FF3333) - Critical alerts
};

// ---- Expression Ids ----
enum ExpressionId
{
    EXPR_NORMAL = 0,     // Eyes open, mouth closed
    EXPR_HAPPY = 1,      // Eyes open, mouth open
    EXPR_TALKING = 2,    // Eyes closed, mouth open
    EXPR_SLEEPING = 3,   // Eyes closed, mouth closed
    EXPR_WORRIED = 4,    // Alert face
    EXPR_RANDOM_IDLE = 5 // Auto-animate idle
};

// ---- Animation Modes ----
enum AnimationMode
{
    ANIM_IDLE = 0,  // Normal operation with idle animations
    ANIM_ALERT = 1, // Gas alert mode (worried face)
    ANIM_PAUSE = 2, // Freeze current frame
    ANIM_CUSTOM = 3 // Direct expression control
};

// ---- JSON Protocol Examples ----
/*
 * CLIENT REQUEST:
 * {"cmd":"ping"}
 *
 * SERVER RESPONSE:
 * {"type":"pong","status":"ok"}
 *
 * CLIENT SET EXPRESSION:
 * {"cmd":"expr","id":1}    (Sets happy expression)
 *
 * SERVER STATUS:
 * {"type":"status","expr":0,"anim":0,"gas_level":512,"buzzer":0}
 *
 * CLIENT GET GAS:
 * {"cmd":"gas"}
 *
 * SERVER RESPONSE:
 * {"type":"gas","value":512}
 *
 * CLIENT SET ANIMATION:
 * {"cmd":"anim","mode":1}  (Sets alert animation)
 *
 * CLIENT CONTROL:
 * {"cmd":"buzzer","state":1}  (Activate buzzer)
 * {"cmd":"buzzer","state":0}  (Deactivate buzzer)
 *
 * CLIENT SEND ALERT (NEW):
 * {
 *   "cmd": "alert",
 *   "schema_ver": 1,
 *   "category": "dev|system|wellness",
 *   "urgency": 1|2|3,
 *   "title": "Error Title",
 *   "body": "Error details...",
 *   "color_hex": "#FF3333",
 *   "timestamp": 1700000000
 * }
 *
 * DEV ALERT EXAMPLE (Compilation Error):
 * {
 *   "cmd": "alert",
 *   "schema_ver": 1,
 *   "category": "dev",
 *   "urgency": 3,
 *   "title": "Compilation Error",
 *   "body": "error C2065: 'undeclaredVar' at main.cpp:42",
 *   "color_hex": "#FF3333",
 *   "timestamp": 1700000000
 * }
 *
 * SYSTEM ALERT EXAMPLE (High CPU):
 * {
 *   "cmd": "alert",
 *   "schema_ver": 1,
 *   "category": "system",
 *   "urgency": 2,
 *   "title": "High CPU Temperature",
 *   "body": "CPU at 88°C - consider closing heavy apps",
 *   "color_hex": "#FF8C00",
 *   "timestamp": 1700000000
 * }
 *
 * WELLNESS ALERT EXAMPLE (Drink Water):
 * {
 *   "cmd": "alert",
 *   "schema_ver": 1,
 *   "category": "wellness",
 *   "urgency": 1,
 *   "title": "Drink Water!",
 *   "body": "You've been working for 45 minutes",
 *   "color_hex": "#2979FF",
 *   "timestamp": 1700000000
 * }
 */

#endif
