# NeoPixel Home Assistant integration script
# This script exposes the NeoPixel HAT as a controllable light via MQTT
# Home Assistant can discover and control it via MQTT Light platform.

import time
import json
import paho.mqtt.client as mqtt
from rpi_ws281x import Adafruit_NeoPixel, Color

# LED strip configuration
LED_COUNT      = 32
LED_PIN        = 18
LED_FREQ_HZ    = 800000
LED_DMA        = 10
LED_BRIGHTNESS = 255
LED_INVERT     = False

# MQTT configuration
MQTT_BROKER = 'homeassistant.lab.so'  # Change to your broker address
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = 'homeassistant/light/neopixel/set'
MQTT_TOPIC_STATE = 'homeassistant/light/neopixel/state'
MQTT_CLIENT_ID = 'neopixel_pi'

current_brightness = 255
last_color = (255, 255, 255)
light_on = False

# Initialize NeoPixel strip
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
strip.begin()

# Utility function to convert hex to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# Set all pixels to a color
def set_strip_color(r, g, b):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(r, g, b))
    strip.show()

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker with result code ", rc)
    client.subscribe(MQTT_TOPIC_COMMAND)

    # Send config for Home Assistant MQTT discovery
    config_payload = {
        "name": "NeoPixel HAT",
        "schema": "json",
        "command_topic": MQTT_TOPIC_COMMAND,
        "state_topic": MQTT_TOPIC_STATE,
        "brightness": True,
        "rgb": True,
        "supported_color_modes": ["rgb"],
        "unique_id": "neopixel_pi_light",
        "device": {
            "identifiers": ["neopixel_pi"],
            "name": "NeoPixel Pi Light",
            "manufacturer": "Raspberry Pi"
        }
    }
    client.publish('homeassistant/light/neopixel/config', json.dumps(config_payload), retain=True)

def on_message(client, userdata, msg):
    global current_brightness, last_color, light_on
    print("MQTT Message received: ", msg.payload)
    payload = json.loads(msg.payload)

    # Start from stored color
    r, g, b = last_color

    if 'state' in payload:
        if payload['state'].upper() == 'ON':
            light_on = True
        elif payload['state'].upper() == 'OFF':
            light_on = False

    if 'color' in payload:
        r = payload['color'].get('r', r)
        g = payload['color'].get('g', g)
        b = payload['color'].get('b', b)
        last_color = (r, g, b)

    if 'brightness' in payload:
        current_brightness = payload['brightness']

    if light_on:
        scaled_r = int(r * current_brightness / 255)
        scaled_g = int(g * current_brightness / 255)
        scaled_b = int(b * current_brightness / 255)
        set_strip_color(scaled_r, scaled_g, scaled_b)
    else:
        set_strip_color(0, 0, 0)

    # Send state update
    state_payload = {
        "state": "ON" if light_on else "OFF",
        "brightness": current_brightness,
        "color": {"r": r, "g": g, "b": b}
    }
    client.publish(MQTT_TOPIC_STATE, json.dumps(state_payload))

# Set up MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
client.username_pw_set("mqtt_user", "mqtt_pass")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
