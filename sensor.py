import asyncio
import datetime
import json
import logging
import websockets
import smllib

from homeassistant.components.sensor import SensorEntity

from smllib import SmlStreamReader
from smllib.const import UNITS
from smllib.errors import CrcError, SmlLibException
from smllib.sml import SmlListEntry, ObisCode

_LOGGER = logging.getLogger(__name__)

from .const import HOST, PASSWORD

WEBSOCKET_URL = f"ws://admin:{PASSWORD}@{HOST}/ws"

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    sensor = WebSocketSensor("Tibber WebSocket Sensor")
    add_entities([sensor])

    # Hintergrund-Task starten
    async def listen():
        while True:
            try:
                async with websockets.connect(WEBSOCKET_URL) as ws:
                    async for message in ws:
                        _LOGGER.debug("Empfangen: %s", message)
                        sensor.set_value(message)
            except Exception as exc:
                _LOGGER.warning(f"failed: {type(exc)} - {exc}")

    hass.loop.create_task(listen())

class WebSocketSensor(SensorEntity):
    def __init__(self, name):
        self._unique_id = "tibber.websocket.sensor"
        self._name = name
        self._state = None
        self._extra_state_attributes = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._extra_state_attributes

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def unit_of_measurement(self):
        return ""  # Beispiel

    def set_value(self, value):

        try: 

            current = datetime.datetime.utcnow()

            stream = SmlStreamReader()
            stream.add(value[38:])
            sml_frame = stream.get_frame()
            if sml_frame is None:
                raise ValueError('Bytes missing.')

            self._extra_state_attributes = {}
            
            if self._state != None:
                self._extra_state_attributes['gap'] = (current - self._state).total_seconds()
            self._state = current

            obis_values = sml_frame.get_obis()
            for obis in obis_values:
                if obis.scaler == None:
                    self._extra_state_attributes[obis.obis] = obis.value
                else:
                    self._extra_state_attributes[obis.obis] = obis.value * 10 ** obis.scaler
                    if obis.obis == "0100100700ff":
                        self._extra_state_attributes['power'] = obis.value * 10 ** obis.scaler

            self.async_write_ha_state()

        except Exception as exc:
            _LOGGER.warning(f"failed: {type(exc)} - {exc}")
