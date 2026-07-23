"""Generate realistic sterilization cycle analog curves.

Each cycle has 4 phases:
1. Conditioning: Temp ramps up, pressure rises
2. Sterilize: Plateau at setpoint
3. Exhaust: Pressure drops rapidly
4. Drying: Vacuum, temp stabilizes lower
"""

import numpy as np
from config import (
    CHANNELS,
    STERILIZE_TEMP_C,
    STERILIZE_PRESSURE_KPA,
    AMBIENT_TEMP_C,
    AMBIENT_PRESSURE_KPA,
    PHASE_CONDITIONING_DURATION,
    PHASE_STERILIZE_DURATION,
    PHASE_EXHAUST_DURATION,
    PHASE_DRYING_DURATION,
    READING_INTERVAL_SEC,
)


def generate_normal_cycle(rng: np.random.Generator, cycle_type: str = "Gravity") -> dict:
    """Generate a complete set of analog readings for a normal (passing) cycle.

    Returns dict with:
        - readings: list of dicts {time_index, timestamp_offset_sec, channels: {id: value}}
        - phases: dict of phase start/end indices
        - summary: dict of cycle-level metrics
    """
    # Determine phase durations based on cycle type
    sterilize_mult = {"Gravity": 1.0, "Pre-Vacuum": 0.8, "Flash": 0.3,
                      "Liquid": 1.5, "Leak Test": 0.5, "Bowie-Dick": 0.6}
    mult = sterilize_mult.get(cycle_type, 1.0)

    cond_dur = rng.integers(*PHASE_CONDITIONING_DURATION)
    ster_dur = int(rng.integers(*PHASE_STERILIZE_DURATION) * mult)
    exh_dur = rng.integers(*PHASE_EXHAUST_DURATION)
    dry_dur = rng.integers(*PHASE_DRYING_DURATION)

    total_dur = cond_dur + ster_dur + exh_dur + dry_dur
    num_readings = total_dur // READING_INTERVAL_SEC

    readings = []
    noise_temp = rng.normal(0, 0.3, num_readings)
    noise_press = rng.normal(0, 1.0, num_readings)

    # Track phase boundaries
    cond_end = cond_dur // READING_INTERVAL_SEC
    ster_end = cond_end + ster_dur // READING_INTERVAL_SEC
    exh_end = ster_end + exh_dur // READING_INTERVAL_SEC

    min_temp = 999.0
    max_temp = -999.0
    max_pressure = 0.0

    for i in range(num_readings):
        t_sec = i * READING_INTERVAL_SEC

        if i < cond_end:
            # Conditioning: sigmoid ramp
            progress = i / cond_end
            sigmoid = 1 / (1 + np.exp(-10 * (progress - 0.5)))
            chamber_temp = AMBIENT_TEMP_C + (STERILIZE_TEMP_C - AMBIENT_TEMP_C) * sigmoid
            chamber_press = AMBIENT_PRESSURE_KPA + (STERILIZE_PRESSURE_KPA - AMBIENT_PRESSURE_KPA) * sigmoid
        elif i < ster_end:
            # Sterilize: plateau with small noise
            chamber_temp = STERILIZE_TEMP_C
            chamber_press = STERILIZE_PRESSURE_KPA
        elif i < exh_end:
            # Exhaust: rapid pressure drop, gradual temp decline
            progress = (i - ster_end) / (exh_end - ster_end)
            chamber_press = STERILIZE_PRESSURE_KPA - (STERILIZE_PRESSURE_KPA - AMBIENT_PRESSURE_KPA) * progress
            chamber_temp = STERILIZE_TEMP_C - (STERILIZE_TEMP_C - 80.0) * progress * 0.5
        else:
            # Drying: low pressure (vacuum), temp settling
            progress = (i - exh_end) / max(1, num_readings - exh_end)
            chamber_press = AMBIENT_PRESSURE_KPA * 0.3 + rng.normal(0, 2)
            chamber_temp = 80.0 + (STERILIZE_TEMP_C - 80.0) * 0.3 * (1 - progress)

        # Apply noise
        chamber_temp += noise_temp[i]
        chamber_press += noise_press[i]

        # Derived channels
        jacket_temp = chamber_temp + rng.normal(2.0, 0.5)  # Jacket slightly hotter
        jacket_press = chamber_press + rng.normal(5.0, 1.0)  # Jacket slightly higher pressure
        drain_temp = chamber_temp - rng.uniform(10, 25)  # Drain cooler
        chamber_temp_2 = chamber_temp + rng.normal(0, 0.2)  # Second probe ~same

        channels = {
            0: round(max(0, chamber_press), 1),
            1: round(max(0, jacket_press), 1),
            2: round(chamber_temp, 1),
            3: round(chamber_temp_2, 1),
            5: round(max(0, drain_temp), 1),
            7: round(jacket_temp, 1),
        }

        min_temp = min(min_temp, chamber_temp)
        max_temp = max(max_temp, chamber_temp)
        max_pressure = max(max_pressure, chamber_press)

        readings.append({
            "time_index": t_sec * 1000 + 1770000005000,  # Matching XML format
            "offset_sec": t_sec,
            "channels": channels,
        })

    # Normal leak rate: < 1.0 mm Hg/min
    leak_rate = round(rng.uniform(0.1, 0.8), 3)

    summary = {
        "min_temp": round(min_temp, 1),
        "max_temp": round(max_temp, 1),
        "max_pressure": round(max_pressure, 1),
        "leak_rate": leak_rate,
        "total_duration_sec": total_dur,
        "ster_time_sec": ster_dur,
        "dry_time_sec": dry_dur,
        "cycle_status": 0,  # 0 = pass
        "num_readings": num_readings,
    }

    phases = {
        "conditioning": (0, cond_end),
        "sterilize": (cond_end, ster_end),
        "exhaust": (ster_end, exh_end),
        "drying": (exh_end, num_readings),
    }

    return {"readings": readings, "phases": phases, "summary": summary}
