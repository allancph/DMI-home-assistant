from datetime import timedelta
import logging
import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
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

def setup_platform(hass, config, add_entities, discovery_info=None):
    name = config[CONF_NAME]
    api_key = config[CONF_API_KEY]
    latitude = config[CONF_LATITUDE]
    longitude = config[CONF_LONGITUDE]

    sensors = [
        DmiWaterLevelSensor(name, api_key, latitude, longitude),
        DmiWindSpeedSensor(name, api_key, latitude, longitude),
        DmiWindDirSensor(name, api_key, latitude, longitude),
    ]
    add_entities(sensors, True)

class DmiBaseSensor(Entity):
    def __init__(self, name, api_key, latitude, longitude):
        self._api_key = api_key
        self._latitude = latitude
        self._longitude = longitude
        self._state = None
        self._attributes = {}
        self._name = name

    @property
    def should_poll(self):
        return True

    @property
    def extra_state_attributes(self):
        return self._attributes

class DmiWaterLevelSensor(DmiBaseSensor):
    @property
    def name(self):
        return f"{self._name} Water Level"

    @property
    def unique_id(self):
        return f"dmi_waterlevel_{self._latitude}_{self._longitude}"

    @property
    def unit_of_measurement(self):
        return "cm"

    def update(self):
        url = (
            "https://dmigw.govcloud.dk/v1/forecastedr/collections/dkss_idw/position"
            f"?coords=POINT({self._longitude} {self._latitude})"
            "&crs=crs84"
            "&parameter-name=sea-mean-deviation"
            f"&api-key={self._api_key}&f=GeoJSON"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if features:
                prop = features[0]["properties"]
                self._state = prop.get("sea-mean-deviation")
                self._attributes["step"] = prop.get("step")
            else:
                self._state = None
        except Exception as e:
            _LOGGER.error(f"Error updating DMI Water Level: {e}")
            self._state = None

class DmiWindSpeedSensor(DmiBaseSensor):
    @property
    def name(self):
        return f"{self._name} Wind Speed"

    @property
    def unique_id(self):
        return f"dmi_windspeed_{self._latitude}_{self._longitude}"

    @property
    def unit_of_measurement(self):
        return "m/s"

    def update(self):
        url = (
            "https://dmigw.govcloud.dk/v1/forecastedr/collections/wam_dw/position"
            f"?coords=POINT({self._longitude} {self._latitude})"
            "&crs=crs84"
            "&parameter-name=wind-speed,wind-dir"
            f"&api-key={self._api_key}&f=GeoJSON"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if features:
                prop = features[0]["properties"]
                self._state = prop.get("wind-speed")
                self._attributes["step"] = prop.get("step")
            else:
                self._state = None
        except Exception as e:
            _LOGGER.error(f"Error updating DMI Wind Speed: {e}")
            self._state = None

class DmiWindDirSensor(DmiBaseSensor):
    @property
    def name(self):
        return f"{self._name} Wind Direction"

    @property
    def unique_id(self):
        return f"dmi_winddir_{self._latitude}_{self._longitude}"

    @property
    def unit_of_measurement(self):
        return "°"

    def update(self):
        url = (
            "https://dmigw.govcloud.dk/v1/forecastedr/collections/wam_dw/position"
            f"?coords=POINT({self._longitude} {self._latitude})"
            "&crs=crs84"
            "&parameter-name=wind-speed,wind-dir"
            f"&api-key={self._api_key}&f=GeoJSON"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if features:
                prop = features[0]["properties"]
                self._state = prop.get("wind-dir")
                self._attributes["step"] = prop.get("step")
            else:
                self._state = None
        except Exception as e:
            _LOGGER.error(f"Error updating DMI Wind Direction: {e}")
            self._state = None