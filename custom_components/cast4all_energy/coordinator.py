"""DataUpdateCoordinator for Cast4All Energy."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Cast4AllApiClient, Cast4AllAuthError, Cast4AllApiError, Cast4AllConnectionError
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
    KEY_PV1_POWER,
    KEY_PV2_POWER,
    KEY_PV1_ENERGY,
    KEY_PV2_ENERGY,
    KEY_GRID_POWER,
    KEY_GRID_CONSUMPTION,
    KEY_GRID_INJECTION,
    KEY_SOLAR_POWER_TOTAL,
    KEY_TOTAL_CONSUMPTION,
    MEASUREMENT_PATTERNS,
)

_LOGGER = logging.getLogger(__name__)


class Cast4AllDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to poll Cast4All FlexMon API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: Cast4AllApiClient,
        installation_id: str,
    ) -> None:
        self.api = api
        self.installation_id = installation_id
        self._measurement_map: dict[str, str] = {}  # key -> measurement external_id

        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_setup(self) -> None:
        """Discover measurements during first refresh."""
        await self._discover_measurements()

    async def _discover_measurements(self) -> None:
        """Map measurement IDs to our internal keys."""
        try:
            measurements = await self.api.get_measurements(self.installation_id)
        except Cast4AllAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (Cast4AllApiError, Cast4AllConnectionError) as err:
            raise UpdateFailed(f"Failed to discover measurements: {err}") from err

        for measurement in measurements:
            meter_name = measurement.get("meter", {}).get("name", "")
            mtype_name = measurement.get("measurementType", {}).get("name", "")
            ext_id = measurement.get("externalId", "")

            for key, pattern in MEASUREMENT_PATTERNS.items():
                if pattern["meter"] in meter_name and pattern["type"] in mtype_name:
                    self._measurement_map[key] = ext_id
                    _LOGGER.debug(
                        "Mapped %s -> %s (meter=%s, type=%s)",
                        key, ext_id, meter_name, mtype_name,
                    )
                    break

        _LOGGER.info(
            "Discovered %d/%d measurements",
            len(self._measurement_map),
            len(MEASUREMENT_PATTERNS),
        )

        if not self._measurement_map:
            raise UpdateFailed("No measurements found for this installation")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Cast4All API."""
        try:
            if not self._measurement_map:
                await self._discover_measurements()

            measurements = await self.api.get_measurements(self.installation_id)
        except Cast4AllAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (Cast4AllApiError, Cast4AllConnectionError) as err:
            raise UpdateFailed(f"Failed to fetch data: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching Cast4All data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        # Build lookup by external ID
        by_id: dict[str, dict] = {}
        for m in measurements:
            ext_id = m.get("externalId", "")
            if ext_id:
                by_id[ext_id] = m

        # Extract values
        data: dict[str, Any] = {}
        for key, ext_id in self._measurement_map.items():
            measurement = by_id.get(ext_id)
            if not measurement:
                data[key] = None
                continue

            # Prefer real-time value for power sensors
            if key in (KEY_PV1_POWER, KEY_PV2_POWER, KEY_GRID_POWER):
                val = measurement.get("lastPolledRealtimeValue")
                if val is None:
                    val = measurement.get("lastPolledValue")
            else:
                val = measurement.get("lastPolledValue")

            if val is not None:
                data[key] = float(val)
            else:
                data[key] = None

        # Compute derived values
        pv1 = data.get(KEY_PV1_POWER) or 0.0
        pv2 = data.get(KEY_PV2_POWER) or 0.0
        grid = data.get(KEY_GRID_POWER)

        data[KEY_SOLAR_POWER_TOTAL] = pv1 + pv2

        if grid is not None:
            # Grid power is positive when importing, solar power is production
            # Total consumption = what the house uses = solar production + grid import
            # If grid is negative (exporting), consumption = solar - export
            data[KEY_TOTAL_CONSUMPTION] = (pv1 + pv2) + grid
        else:
            data[KEY_TOTAL_CONSUMPTION] = None

        # Convert cumulative energy from Wh to kWh
        for key in (KEY_PV1_ENERGY, KEY_PV2_ENERGY, KEY_GRID_CONSUMPTION, KEY_GRID_INJECTION):
            if data.get(key) is not None:
                data[key] = data[key] / 1000.0  # Wh -> kWh

        _LOGGER.debug(
            "Data: solar=%.0fW grid=%.0fW consumption=%.0fW",
            data.get(KEY_SOLAR_POWER_TOTAL, 0),
            data.get(KEY_GRID_POWER, 0),
            data.get(KEY_TOTAL_CONSUMPTION, 0),
        )

        return data
