from datetime import timedelta
import logging
import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "DMI Forecast"
SCAN_INTERVAL = timedelta(minutes=240)

CONF_API_KEY = "api_key"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_LATITUDE, default=56.1159): cv.latitude,
    vol.Optional(CONF_LONGITUDE, default=12.6026): cv.longitude,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config[CONF_NAME]
    api_key = config[CONF_API_KEY]
    latitude = config[CONF_LATITUDE]
    longitude = config[CONF_LONGITUDE]

    session = aiohttp.ClientSession()

    wind_coordinator = DmiWindDataCoordinator(
        hass, session, api_key, latitude, longitude
    )
    await wind_coordinator.async_refresh()

    water_coordinator = DmiWaterLevelDataCoordinator(
        hass, session, api_key, latitude, longitude
    )
    await water_coordinator.async_refresh()

    sensors = [
        DmiWaterLevelSensor(name, water_coordinator),
        DmiWindSpeedSensor(name, wind_coordinator),
        DmiWindDirSensor(name, wind_coordinator),
    ]
    async_add_entities(sensors, True)

class DmiWaterLevelDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, api_key, latitude, longitude):
        super().__init__(
            hass,
            _LOGGER,
            name="DMI Water Level Data",
            update_interval=SCAN_INTERVAL,
        )
        self._session = session
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude

    async def _async_update_data(self):
        url = (
            "https://dmigw.govcloud.dk/v1/forecastedr/collections/dkss_idw/position"
            f"?coords=POINT({self.longitude} {self.latitude})"
            "&crs=crs84"
            "&parameter-name=sea-mean-deviation"
            f"&api-key={self.api_key}&f=GeoJSON"
        )
        try:
            async with self._session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
                features = data.get("features", [])
                if features:
                    prop = features[0]["properties"]
                    return {
                        "sea-mean-deviation": prop.get("sea-mean-deviation"),
                        "step": prop.get("step"),
                    }
                else:
                    return {}
        except Exception as e:
            raise UpdateFailed(f"Error fetching DMI Water Level data: {e}")

class DmiWindDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, api_key, latitude, longitude):
        super().__init__(
            hass,
            _LOGGER,
            name="DMI Wind Data",
            update_interval=SCAN_INTERVAL,
        )
        self._session = session
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude

    async def _async_update_data(self):
        url = (
            "https://dmigw.govcloud.dk/v1/forecastedr/collections/wam_dw/position"
            f"?coords=POINT({self.longitude} {self.latitude})"
            "&crs=crs84"
            "&parameter-name=wind-speed,wind-dir"
            f"&api-key={self.api_key}&f=GeoJSON"
        )
        try:
            async with self._session.get(url, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
                features = data.get("features", [])
                if features:
                    prop = features[0]["properties"]
                    return {
                        "wind-speed": prop.get("wind-speed"),
                        "wind-dir": prop.get("wind-dir"),
                        "step": prop.get("step"),
                    }
                else:
                    return {}
        except Exception as e:
            raise UpdateFailed(f"Error fetching DMI Wind data: {e}")

class DmiWaterLevelSensor(SensorEntity):
    def __init__(self, name, coordinator):
        self._attr_name = f"{name} Water Level"
        self._attr_unique_id = f"dmi_waterlevel_{coordinator.latitude}_{coordinator.longitude}"
        self._attr_unit_of_measurement = "cm"
        self._coordinator = coordinator

    @property
    def state(self):
        return self._coordinator.data.get("sea-mean-deviation") if self._coordinator.data else None

    @property
    def extra_state_attributes(self):
        return {"step": self._coordinator.data.get("step")} if self._coordinator.data else {}

    async def async_update(self):
        await self._coordinator.async_request_refresh()

class DmiWindSpeedSensor(SensorEntity):
    def __init__(self, name, coordinator):
        self._attr_name = f"{name} Wind Speed"
        self._attr_unique_id = f"dmi_windspeed_{coordinator.latitude}_{coordinator.longitude}"
        self._attr_unit_of_measurement = "m/s"
        self._coordinator = coordinator

    @property
    def state(self):
        return self._coordinator.data.get("wind-speed") if self._coordinator.data else None

    @property
    def extra_state_attributes(self):
        return {"step": self._coordinator.data.get("step")} if self._coordinator.data else {}

    async def async_update(self):
        await self._coordinator.async_request_refresh()

class DmiWindDirSensor(SensorEntity):
    def __init__(self, name, coordinator):
        self._attr_name = f"{name} Wind Direction"
        self._attr_unique_id = f"dmi_winddir_{coordinator.latitude}_{coordinator.longitude}"
        self._attr_unit_of_measurement = "°"
        self._coordinator = coordinator

    @property
    def state(self):
        return self._coordinator.data.get("wind-dir") if self._coordinator.data else None

    @property
    def extra_state_attributes(self):
        return {"step": self._coordinator.data.get("step")} if self._coordinator.data else {}

    async def async_update(self):
        await self._coordinator.async_request_refresh()
