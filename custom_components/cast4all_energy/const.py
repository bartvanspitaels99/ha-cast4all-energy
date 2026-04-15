"""Constants for Cast4All Energy integration."""

DOMAIN = "cast4all_energy"

# API Configuration
BASE_URL = "https://izen.cast4all.energy/flexMon/v1"
TOKEN_URL = "https://auth.izen.cast4all.energy/realms/izen/protocol/openid-connect/token"
CLIENT_ID = "go_flowbuddy"

# Config keys
CONF_INSTALLATION_ID = "installation_id"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Measurement keys
KEY_PV1_POWER = "pv1_power"
KEY_PV2_POWER = "pv2_power"
KEY_PV1_ENERGY = "pv1_energy"
KEY_PV2_ENERGY = "pv2_energy"
KEY_GRID_POWER = "grid_power"
KEY_GRID_CONSUMPTION = "grid_consumption"
KEY_GRID_INJECTION = "grid_injection"
KEY_SOLAR_POWER_TOTAL = "solar_power_total"
KEY_TOTAL_CONSUMPTION = "total_consumption"

# Measurement type matching patterns
MEASUREMENT_PATTERNS = {
    KEY_PV1_POWER: {"meter": "PV 1", "type": "EMS PV power"},
    KEY_PV2_POWER: {"meter": "PV 2", "type": "EMS PV power"},
    KEY_PV1_ENERGY: {"meter": "PV 1", "type": "Reverse Active Energy"},
    KEY_PV2_ENERGY: {"meter": "PV 2", "type": "Reverse Active Energy"},
    KEY_GRID_POWER: {"meter": "Grid", "type": "EMS GRID power"},
    KEY_GRID_CONSUMPTION: {"meter": "Grid", "type": "EMS GRID consumption"},
    KEY_GRID_INJECTION: {"meter": "Grid", "type": "EMS GRID injection"},
}
