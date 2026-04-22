#ifndef DRAW_H
#define DRAW_H

#include <Arduino_GFX_Library.h>
#include "images_compressed.h"

Arduino_ST7789 *gfx = new Arduino_ST7789(
    new Arduino_ESP32SPI(-1, 5, 18, 23),
    4, 0, false, 240, 320);

enum FrameIndex
{
  EYE_CLOSE_MOUTH_CLOSE,
  EYE_OPEN_MOUTH_OPEN,
  EYE_CLOSE_MOUTH_OPEN,
  EYE_OPEN_MOUTH_CLOSE,
  WORRIED
};

// RLE Decompression buffer (153,600 bytes for 320x240 RGB565)
// Allocated in PSRAM to save internal RAM if available
uint16_t *decompressBuffer = NULL;

void initDecompressBuffer()
{
  // Try to allocate in PSRAM first (if available on ESP32)
  if (psramFound())
  {
    decompressBuffer = (uint16_t *)ps_malloc(320 * 240 * 2);
  }
  else
  {
    decompressBuffer = (uint16_t *)malloc(320 * 240 * 2);
  }
}

// Decompression function
void rleDecompress(const RLEData *compressed, uint32_t compressedSize, uint16_t *output, uint32_t outputSize)
{
  uint32_t outIdx = 0;
  for (uint32_t i = 0; i < compressedSize && outIdx < outputSize; i++)
  {
    uint16_t runLength = pgm_read_word(&compressed[i].length);
    uint16_t value = pgm_read_word(&compressed[i].value);

    for (uint16_t j = 0; j < runLength && outIdx < outputSize; j++)
    {
      output[outIdx++] = value;
    }
  }
}

struct FrameData
{
  const RLEData *rleData;
  uint32_t rleSize;
};

const FrameData frames[] = {
    {Eye_Close_Mouth_Close_565_RLE, Eye_Close_Mouth_Close_565_RLE_SIZE},
    {Eye_Open_Mouth_Open_565_RLE, Eye_Open_Mouth_Open_565_RLE_SIZE},
    {Eye_Close_Mouth_Open_565_RLE, Eye_Close_Mouth_Open_565_RLE_SIZE},
    {Eye_Open_Mouth_Close_565_RLE, Eye_Open_Mouth_Close_565_RLE_SIZE},
    {Worried_565_RLE, Worried_565_RLE_SIZE}};

void drawFrame(int index)
{
  if (decompressBuffer == NULL)
  {
    initDecompressBuffer();
  }

  // Decompress the frame
  rleDecompress(frames[index].rleData, frames[index].rleSize, decompressBuffer, 320 * 240);

  // Draw to display
  gfx->draw16bitRGBBitmap(0, 0, decompressBuffer, 320, 240);
}

// Global animation state
// Matches AnimationMode enum from nekobot_protocol.h
#define ANIM_IDLE 0   // Normal operation with idle animations
#define ANIM_ALERT 1  // Gas alert mode (worried face)
#define ANIM_PAUSE 2  // Freeze current frame
#define ANIM_CUSTOM 3 // Direct expression control

int animationMode = 0;

int idleSubstate = 0;
unsigned long lastChange = 0;

// Idle substates:
// 0 = normal
// 1 = blink
// 2 = mouth move

void idleAnimation()
{
  unsigned long now = millis();

  switch (idleSubstate)
  {

  case 0:
    drawFrame(EYE_OPEN_MOUTH_CLOSE);

    if (now - lastChange > random(2000, 5000))
    {
      int r = random(0, 3);

      if (r == 0)
      {
        idleSubstate = 1;
      }
      else
      {
        idleSubstate = 2;
      }

      lastChange = now;
    }
    break;

  case 1:
    drawFrame(EYE_CLOSE_MOUTH_CLOSE);
    delay(120);

    drawFrame(EYE_OPEN_MOUTH_CLOSE);

    idleSubstate = 0;
    lastChange = millis();
    break;

  case 2:
    drawFrame(EYE_OPEN_MOUTH_OPEN);
    delay(200);

    drawFrame(EYE_OPEN_MOUTH_CLOSE);

    idleSubstate = 0;
    lastChange = millis();
    break;
  }
}

void updateAnimation()
{
  switch (animationMode)
  {
  case 0:
    idleAnimation();
    break;

  case 1:
    drawFrame(WORRIED);
    break;
  }
}

#endif