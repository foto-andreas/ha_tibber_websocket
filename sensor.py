import asyncio
import datetime
import logging
import websockets
import smllib

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from smllib import SmlStreamReader

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up sensor from a config entry."""
    host: str = entry.data["host"]
    password: str = entry.data["password"]
    await _async_setup_entities(hass, async_add_entities, host, password)


async def _async_setup_entities(hass: HomeAssistant, add_entities, host: str, password: str) -> None:
    sensor = WebSocketSensor("Tibber WebSocket Sensor 2", host)
    add_entities([sensor])

    websocket_url = f"ws://admin:{password}@{host}/ws"

    _LOGGER.info(f"URL: {websocket_url}")

    async def listen():
        while True:
            try:
                async with websockets.connect(websocket_url) as ws:
                    async for message in ws:
                        _LOGGER.debug("Empfangen: %s", message)
                        sensor.set_value(message)
            except Exception as exc:
                _LOGGER.warning(f"failed: {type(exc)} - {exc}")
                await asyncio.sleep(5)

    hass.loop.create_task(listen())


class WebSocketSensor(SensorEntity):
    def __init__(self, name: str, host: str):
        self._unique_id = f"tibber.websocket.sensor.{host}"
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
        return ""

    def set_value(self, value: str):
        try:
            current = datetime.datetime.utcnow()

            stream = SmlStreamReader()
            stream.add(value[38:])
            sml_frame = stream.get_frame()
            if sml_frame is None:
                raise ValueError('Bytes missing.')

            self._extra_state_attributes = {}

            if self._state is not None:
                self._extra_state_attributes['gap'] = (current - self._state).total_seconds()
            self._state = current

            obis_values = sml_frame.get_obis()
            for obis in obis_values:
                if obis.scaler is None:
                    self._extra_state_attributes[obis.obis] = obis.value
                else:
                    self._extra_state_attributes[obis.obis] = obis.value * 10 ** obis.scaler
                    if obis.obis == "0100100700ff":
                        self._extra_state_attributes['power'] = obis.value * 10 ** obis.scaler

            self.async_write_ha_state()

        except Exception as exc:
            _LOGGER.warning(f"failed: {type(exc)} - {exc}")
