"""Inject failure modes into normal cycle analog data.

Four failure modes:
1. Seal leak: LeakRate exceeds threshold, pressure decay during sterilize phase
2. Temperature drift: Sterilize phase doesn't reach/hold setpoint
3. Pressure anomaly: High variance pressure during sterilize phase
4. Sensor fault: One channel reads constant or drops to zero mid-cycle
"""

import numpy as np


def inject_seal_leak(readings: list, summary: dict, phases: dict,
                     rng: np.random.Generator) -> tuple:
    """Seal leak: pressure decays during sterilize phase, leak rate elevated."""
    ster_start, ster_end = phases["sterilize"]
    decay_rate = rng.uniform(0.3, 1.5)  # kPa per reading

    for i in range(ster_start, len(readings)):
        progress = i - ster_start
        # Pressure channels (0 and 1) decay
        readings[i]["channels"][0] -= decay_rate * progress * 0.1
        readings[i]["channels"][0] = round(max(0, readings[i]["channels"][0]), 1)
        readings[i]["channels"][1] -= decay_rate * progress * 0.08
        readings[i]["channels"][1] = round(max(0, readings[i]["channels"][1]), 1)

    summary["leak_rate"] = round(rng.uniform(1.3, 4.5), 3)  # Above 1.3 threshold
    summary["cycle_status"] = 1  # Fail
    return readings, summary


def inject_temp_drift(readings: list, summary: dict, phases: dict,
                      rng: np.random.Generator) -> tuple:
    """Temperature drift: sterilize phase never reaches or holds setpoint."""
    ster_start, ster_end = phases["sterilize"]
    drift_type = rng.choice(["undershoot", "decay"])

    if drift_type == "undershoot":
        # Never reaches setpoint — stays 3-8°C below
        offset = rng.uniform(3.0, 8.0)
        for i in range(ster_start, ster_end):
            readings[i]["channels"][2] -= offset
            readings[i]["channels"][2] = round(readings[i]["channels"][2], 1)
            readings[i]["channels"][3] -= offset
            readings[i]["channels"][3] = round(readings[i]["channels"][3], 1)
    else:
        # Decays during sterilize phase
        for i in range(ster_start, ster_end):
            progress = (i - ster_start) / max(1, ster_end - ster_start)
            drop = progress * rng.uniform(5.0, 12.0)
            readings[i]["channels"][2] -= drop
            readings[i]["channels"][2] = round(readings[i]["channels"][2], 1)
            readings[i]["channels"][3] -= drop
            readings[i]["channels"][3] = round(readings[i]["channels"][3], 1)

    summary["cycle_status"] = 2  # Fail - temp
    summary["min_temp"] = min(r["channels"][2] for r in readings)
    return readings, summary


def inject_pressure_anomaly(readings: list, summary: dict, phases: dict,
                            rng: np.random.Generator) -> tuple:
    """Pressure anomaly: high variance spikes during sterilize phase."""
    ster_start, ster_end = phases["sterilize"]

    num_spikes = rng.integers(3, 8)
    spike_positions = rng.integers(ster_start, ster_end, size=num_spikes)

    for pos in spike_positions:
        spike_mag = rng.uniform(30, 80)  # kPa spike
        direction = rng.choice([-1, 1])
        # Affect a window of 3-5 readings around the spike
        window = rng.integers(3, 6)
        for j in range(max(0, pos - window), min(len(readings), pos + window)):
            dist = abs(j - pos)
            factor = 1.0 - (dist / window)
            readings[j]["channels"][0] += direction * spike_mag * factor
            readings[j]["channels"][0] = round(max(0, readings[j]["channels"][0]), 1)

    summary["cycle_status"] = 3  # Fail - pressure
    return readings, summary


def inject_sensor_fault(readings: list, summary: dict, phases: dict,
                        rng: np.random.Generator) -> tuple:
    """Sensor fault: one channel flatlines or drops to zero mid-cycle."""
    fault_channel = rng.choice([2, 3, 5, 7])  # Temperature channels
    fault_start = rng.integers(len(readings) // 4, len(readings) // 2)
    fault_type = rng.choice(["flatline", "dropout"])

    if fault_type == "flatline":
        flat_value = readings[fault_start]["channels"][fault_channel]
        for i in range(fault_start, len(readings)):
            readings[i]["channels"][fault_channel] = flat_value
    else:
        for i in range(fault_start, len(readings)):
            readings[i]["channels"][fault_channel] = 0.0

    summary["cycle_status"] = 4  # Fail - sensor
    return readings, summary


INJECTION_FUNCTIONS = {
    "seal_leak": inject_seal_leak,
    "temp_drift": inject_temp_drift,
    "pressure_anomaly": inject_pressure_anomaly,
    "sensor_fault": inject_sensor_fault,
}


def apply_failure(readings: list, summary: dict, phases: dict,
                  failure_mode: str, rng: np.random.Generator) -> tuple:
    """Apply a failure mode to cycle data."""
    func = INJECTION_FUNCTIONS[failure_mode]
    return func(readings, summary, phases, rng)
