"""Configuration for IIoT synthetic data generation."""

NUM_DEVICES = 113
NUM_CYCLES = 47_000
FAILURE_RATE = 0.088  # 8.8% of cycles will have failures

# Failure mode distribution (must sum to 1.0)
FAILURE_MODES = {
    "seal_leak": 0.40,
    "temp_drift": 0.30,
    "pressure_anomaly": 0.20,
    "sensor_fault": 0.10,
}

# Analog channel definitions (6 channels matching XML sample)
CHANNELS = [
    {"id": 0, "name": "Chamber Pressure", "unit": "kPa", "questra_property": "CP0"},
    {"id": 1, "name": "Jacket Pressure", "unit": "kPa", "questra_property": "JP1"},
    {"id": 2, "name": "Chamber Temp Probe 1", "unit": "C", "questra_property": "CT2"},
    {"id": 3, "name": "Chamber Temp Probe 2", "unit": "C", "questra_property": "CT3"},
    {"id": 5, "name": "Drain Temperature", "unit": "C", "questra_property": "DT5"},
    {"id": 7, "name": "Jacket Temperature", "unit": "C", "questra_property": "JT7"},
]

# Cycle phase durations (seconds) — standard gravity-displacement steam sterilizer
PHASE_CONDITIONING_DURATION = (240, 360)  # 4-6 min
PHASE_STERILIZE_DURATION = (240, 1080)    # 4-18 min depending on cycle type
PHASE_EXHAUST_DURATION = (90, 150)        # 1.5-2.5 min
PHASE_DRYING_DURATION = (240, 360)        # 4-6 min

READING_INTERVAL_SEC = 5  # 5-second intervals between analog readings

# Sterilization setpoints
STERILIZE_TEMP_C = 134.0       # Standard flash sterilization
STERILIZE_PRESSURE_KPA = 210.0  # ~30 PSI gauge
AMBIENT_TEMP_C = 22.0
AMBIENT_PRESSURE_KPA = 101.3

# Device families
DEVICE_FAMILIES = ["LNE", "VSE", "EVO"]
DEVICE_TYPES = [
    "AMSCO Century V116",
    "AMSCO Century V120",
    "AMSCO Evolution",
    "AMSCO Eagle 3000",
]

# Cycle types
CYCLE_TYPES = [
    "Gravity",
    "Pre-Vacuum",
    "Flash",
    "Liquid",
    "Leak Test",
    "Bowie-Dick",
]

# Date range for synthetic data (6 months)
DATE_START = "2025-07-01"
DATE_END = "2025-12-31"

# Output paths
OUTPUT_DIR = "../data"
XML_DIR = "../data/xml"
