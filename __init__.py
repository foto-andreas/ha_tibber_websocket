from homeassistant.core import HomeAssistant

DOMAIN = "tibber_websocket"

async def async_setup(hass: HomeAssistant, config: dict):
    # Nichts Spezielles nötig
    return True
