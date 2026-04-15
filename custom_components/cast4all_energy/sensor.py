"""Sensor platform for Cast4All Energy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    KEY_PV1_POWER,
    KEY_PV2_POWER,
    KEY_PV1_ENERGY,
    KEY_PV2_ENERGY,
    KEY_GRID_POWER,
    KEY_GRID_CONSUMPTION,
    KEY_GRID_INJECTION,
    KEY_SOLAR_POWER_TOTAL,
    KEY_TOTAL_CONSUMPTION,
)
from .coordinator import Cast4AllDataCoordinator


@dataclass(frozen=True, kw_only=True)
class Cast4AllSensorEntityDescription(SensorEntityDescription):
    """Describes a Cast4All sensor entity."""

    value_fn: Callable[[dict[str, Any]], float | None]


SENSOR_DESCRIPTIONS: tuple[Cast4AllSensorEntityDescription, ...] = (
    Cast4AllSensorEntityDescription(
        key=KEY_PV1_POWER,
        translation_key="pv1_power",
        name="PV 1 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get(KEY_PV1_POWER),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_PV2_POWER,
        translation_key="pv2_power",
        name="PV 2 Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get(KEY_PV2_POWER),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_SOLAR_POWER_TOTAL,
        translation_key="solar_power_total",
        name="Solar Power Total",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get(KEY_SOLAR_POWER_TOTAL),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_GRID_POWER,
        translation_key="grid_power",
        name="Grid Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get(KEY_GRID_POWER),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_TOTAL_CONSUMPTION,
        translation_key="total_consumption",
        name="Total Consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get(KEY_TOTAL_CONSUMPTION),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_PV1_ENERGY,
        translation_key="pv1_energy",
        name="PV 1 Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_PV1_ENERGY),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_PV2_ENERGY,
        translation_key="pv2_energy",
        name="PV 2 Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_PV2_ENERGY),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_GRID_CONSUMPTION,
        translation_key="grid_consumption",
        name="Grid Consumption",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_GRID_CONSUMPTION),
    ),
    Cast4AllSensorEntityDescription(
        key=KEY_GRID_INJECTION,
        translation_key="grid_injection",
        name="Grid Injection",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_GRID_INJECTION),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cast4All sensors from a config entry."""
    coordinator: Cast4AllDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        Cast4AllSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class Cast4AllSensor(CoordinatorEntity[Cast4AllDataCoordinator], SensorEntity):
    """Representation of a Cast4All sensor."""

    entity_description: Cast4AllSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Cast4AllDataCoordinator,
        description: Cast4AllSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.installation_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.installation_id)},
            name="Cast4All Energy Monitor",
            manufacturer="Cast4All",
            model="FlexMon EMS",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
