"""Main generator: produces 47K cycle XMLs + supporting CSVs.

Usage:
    cd generator/
    python generate_cycle_xml.py [--num-cycles 47000] [--workers 10]
"""

import argparse
import csv
import gzip
import os
import sys
import uuid
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
from xml.etree.ElementTree import Element, SubElement, tostring

import numpy as np

from analog_curves import generate_normal_cycle
from config import (
    CHANNELS,
    CYCLE_TYPES,
    DATE_END,
    DATE_START,
    DEVICE_FAMILIES,
    DEVICE_TYPES,
    FAILURE_MODES,
    FAILURE_RATE,
    NUM_CYCLES,
    NUM_DEVICES,
    OUTPUT_DIR,
    READING_INTERVAL_SEC,
    XML_DIR,
)
from failure_injection import apply_failure


def generate_devices(num_devices: int, rng: np.random.Generator) -> list[dict]:
    """Generate device master data."""
    devices = []
    for i in range(num_devices):
        serial = f"9{rng.integers(10000000, 99999999)}"
        family = rng.choice(DEVICE_FAMILIES)
        device_type = rng.choice(DEVICE_TYPES)
        firmware_rev = f"{rng.integers(1,5)}.{rng.integers(0,9)}"
        firmware_build = str(rng.integers(3000, 5000))
        questra = f"_ZWQ_{rng.integers(10000, 99999)}_{rng.integers(100000000, 999999999)}"

        devices.append({
            "device_id": f"DEV-{i+1:04d}",
            "serial_number": serial,
            "local_name": str(rng.integers(1, 20)),
            "family": family,
            "device_type": device_type,
            "questra_asset_number": questra,
            "firmware_rev": firmware_rev,
            "firmware_build": firmware_build,
            "install_date": (datetime(2018, 1, 1) + timedelta(days=int(rng.integers(0, 2000)))).strftime("%Y-%m-%d"),
            "location": f"Facility {rng.choice(['A','B','C'])}, Floor {rng.integers(1,4)}",
            "status": "Active",
        })
    return devices


def assign_cycles_to_devices(num_cycles: int, devices: list[dict],
                             rng: np.random.Generator) -> list[dict]:
    """Distribute cycles across devices over the date range."""
    start = datetime.strptime(DATE_START, "%Y-%m-%d")
    end = datetime.strptime(DATE_END, "%Y-%m-%d")
    total_days = (end - start).days

    assignments = []
    for i in range(num_cycles):
        device = devices[i % len(devices)]
        day_offset = rng.integers(0, total_days)
        hour = rng.integers(6, 22)  # Operating hours
        minute = rng.integers(0, 60)
        cycle_time = start + timedelta(days=int(day_offset), hours=int(hour), minutes=int(minute))
        cycle_type = rng.choice(CYCLE_TYPES)

        assignments.append({
            "cycle_id": str(uuid.uuid4()),
            "device": device,
            "timestamp": cycle_time,
            "cycle_type": cycle_type,
            "cycle_count": (i // len(devices)) + rng.integers(50, 300),
        })
    return assignments


def build_cycle_xml(cycle_data: dict, readings: list, summary: dict) -> bytes:
    """Build XML document matching the ProConnect cycle format."""
    device = cycle_data["device"]

    root = Element("Cycle", FileRev="4.1")

    # DeviceInfo
    dev_info = SubElement(root, "DeviceInfo", CYCLE_ID=cycle_data["cycle_id"])
    SubElement(dev_info, "SerialNumber").text = device["serial_number"]
    SubElement(dev_info, "LocalName").text = device["local_name"]
    SubElement(dev_info, "Family").text = device["family"]
    SubElement(dev_info, "DeviceType").text = device["device_type"]
    SubElement(dev_info, "SyncTick")
    SubElement(dev_info, "SyncTime")
    SubElement(dev_info, "ConnectionDuration")

    # ProConnect
    pc = SubElement(root, "ProConnect")
    SubElement(pc, "Rev").text = device["firmware_rev"]
    SubElement(pc, "Build").text = device["firmware_build"]
    SubElement(pc, "InstalledPath")
    inst_drive = SubElement(pc, "InstallDrive", FreeSpaceMB="", SizeMB="")
    SubElement(pc, "MemoryWorkingSet")
    SubElement(pc, "StartedByUserName")
    SubElement(pc, "IsAdminUser")
    SubElement(pc, "StartTime")
    SubElement(pc, "ProConnectMode")
    SubElement(pc, "AdvancedLogging")
    SubElement(pc, "QuestraAssetNumber").text = device["questra_asset_number"]
    SubElement(pc, "UxmlToCsiqConverterFormatVersion").text = "7.569"
    it = SubElement(pc, "InstrumentTracking")
    SubElement(it, "Enabled").text = "false"
    SubElement(it, "FileType").text = "CSIQ"
    SubElement(it, "Path")
    SubElement(it, "FailSafePath")

    # CultureInfo
    ci = SubElement(root, "CultureInfo")
    SubElement(ci, "EnglishName").text = "English (United States)"
    SubElement(ci, "ShortDatePattern").text = "M/d/yyyy"
    SubElement(ci, "NegativeSign").text = "-"
    SubElement(ci, "PostiveSign").text = "+"
    SubElement(ci, "PercentSymbol").text = "%"
    SubElement(ci, "CurrencyDecimalSepatator").text = "."

    # PC (system info - empty for synthetic)
    pc_sys = SubElement(root, "PC")
    for tag in ["OS", "OSVersion", "MemorySizeMB", "AvailableMemoryMB",
                "CurrentLoadPercent", "ProcessorCount", "RunningProcesses", "SystemUpTime"]:
        SubElement(pc_sys, tag)

    # CycleFields
    cf = SubElement(root, "CycleFields")
    SubElement(cf, "CycleCount").text = str(cycle_data["cycle_count"])
    SubElement(cf, "CycleType").text = cycle_data["cycle_type"]
    SubElement(cf, "SterilizeTemp").text = f"{summary['max_temp']:.1f}"
    SubElement(cf, "ControlTemp")
    ster_m, ster_s = divmod(summary["ster_time_sec"], 60)
    SubElement(cf, "SterTime").text = f"00:{ster_m:02d}:{ster_s:02d}"
    dry_m, dry_s = divmod(summary["dry_time_sec"], 60)
    SubElement(cf, "DryTime").text = f"00:{dry_m:02d}:{dry_s:02d}"
    SubElement(cf, "SummaryCondition")
    SubElement(cf, "SummarySterilize")
    total_m, total_s = divmod(summary["total_duration_sec"], 60)
    total_h, total_m = divmod(total_m, 60)
    SubElement(cf, "SummaryTotalCycle").text = f"{total_h:02d}:{total_m:02d}:{total_s:02d}"
    SubElement(cf, "SummaryCycleStatus").text = str(summary["cycle_status"])
    SubElement(cf, "MinTemp").text = f"{summary['min_temp']:.1f}"
    SubElement(cf, "MaxTemp").text = f"{summary['max_temp']:.1f}"
    SubElement(cf, "LoadNumber").text = f"{np.random.randint(100000, 999999)}-{np.random.randint(100000, 999999)}"
    SubElement(cf, "ProgramPartNo").text = str(np.random.randint(10000000, 99999999))
    SubElement(cf, "ProgramRevision").text = f"v{np.random.randint(1,9)}.{np.random.randint(0,99):02d}"
    SubElement(cf, "LeakRate").text = f"{summary['leak_rate']:.3f}"
    SubElement(cf, "LotNumber")

    # Board info (empty for synthetic)
    rm = SubElement(root, "RMBoard")
    SubElement(rm, "Hardware", PartNumber="", Rev="", RevDate="", SerialNumber="")
    SubElement(rm, "Software", CRC="", NeedsUpdated="", Program="", Rev="", RevDate="", RevTime="")
    SubElement(rm, "BootLoader", Program="", Rev="")

    cb = SubElement(root, "ControlBoard")
    SubElement(cb, "HardWare", BootVersion="", MemorySize="")
    SubElement(cb, "Program", CRC="", Program="", Rev="", RevDate="")
    SubElement(cb, "System", Rev="", RevDate="", System="")

    # PrinterLines (minimal for synthetic)
    SubElement(root, "PrinterLines")

    # IODefinition
    SubElement(root, "IODefinition", Interface="ProConnect", Name="Standard IO")
    SubElement(root, "IOEvents")
    SubElement(root, "HMIEvents")

    # Analog section
    analog = SubElement(root, "Analog")
    analog_readings = SubElement(analog, "AnalogReadings")

    # Channel definitions
    channels_elem = SubElement(analog_readings, "Channels")
    for ch in CHANNELS:
        SubElement(channels_elem, "Channel",
                   Desc=ch["name"], ID=str(ch["id"]),
                   Name=str(ch["id"]), QuestraProperty=ch["questra_property"])

    # Readings
    readings_elem = SubElement(analog_readings, "Readings")
    base_time = cycle_data["timestamp"]

    for r in readings:
        ts = base_time + timedelta(seconds=r["offset_sec"])
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S.000-00:00")

        reading_el = SubElement(readings_elem, "Reading",
                                TimeIndex=str(r["time_index"]),
                                TimeStamp=ts_str)
        chs_el = SubElement(reading_el, "Channels")
        for ch in CHANNELS:
            SubElement(chs_el, "RC",
                       CID=str(ch["id"]),
                       Unit=ch["unit"],
                       Value=str(r["channels"][ch["id"]]))

    return tostring(root, encoding="unicode").encode("utf-8")


def generate_single_cycle(args: tuple) -> dict:
    """Worker function for multiprocessing. Generates one cycle XML + metadata."""
    cycle_data, is_failure, failure_mode, seed = args
    rng = np.random.default_rng(seed)

    # Generate analog data
    result = generate_normal_cycle(rng, cycle_data["cycle_type"])
    readings = result["readings"]
    summary = result["summary"]
    phases = result["phases"]

    # Inject failure if applicable
    if is_failure and failure_mode:
        readings, summary = apply_failure(readings, summary, phases, failure_mode, rng)

    # Build XML
    xml_bytes = build_cycle_xml(cycle_data, readings, summary)

    # Write gzipped XML
    filename = f"{cycle_data['cycle_id']}.xml.gz"
    filepath = os.path.join(XML_DIR, filename)
    with gzip.open(filepath, "wb") as f:
        f.write(xml_bytes)

    # Return metadata for CSVs
    device = cycle_data["device"]
    return {
        "cycle_id": cycle_data["cycle_id"],
        "device_id": device["device_id"],
        "serial_number": device["serial_number"],
        "timestamp": cycle_data["timestamp"].isoformat(),
        "cycle_type": cycle_data["cycle_type"],
        "cycle_count": cycle_data["cycle_count"],
        "cycle_status": summary["cycle_status"],
        "leak_rate": summary["leak_rate"],
        "min_temp": summary["min_temp"],
        "max_temp": summary["max_temp"],
        "max_pressure": summary["max_pressure"],
        "ster_time_sec": summary["ster_time_sec"],
        "dry_time_sec": summary["dry_time_sec"],
        "total_duration_sec": summary["total_duration_sec"],
        "num_readings": summary["num_readings"],
        "is_failure": is_failure,
        "failure_mode": failure_mode if is_failure else "",
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic IIoT cycle data")
    parser.add_argument("--num-cycles", type=int, default=NUM_CYCLES)
    parser.add_argument("--num-devices", type=int, default=NUM_DEVICES)
    parser.add_argument("--workers", type=int, default=min(10, cpu_count()))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Generating {args.num_cycles:,} cycles across {args.num_devices} devices "
          f"with {args.workers} workers...")

    rng = np.random.default_rng(args.seed)

    # Ensure output dirs exist
    os.makedirs(XML_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate devices
    print("Generating device master data...")
    devices = generate_devices(args.num_devices, rng)

    # Write device.csv
    device_csv_path = os.path.join(OUTPUT_DIR, "device.csv")
    with open(device_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=devices[0].keys())
        writer.writeheader()
        writer.writerows(devices)
    print(f"  Written {len(devices)} devices to {device_csv_path}")

    # Assign cycles to devices
    print("Assigning cycles to devices...")
    cycle_assignments = assign_cycles_to_devices(args.num_cycles, devices, rng)

    # Determine which cycles fail
    num_failures = int(args.num_cycles * FAILURE_RATE)
    failure_indices = set(rng.choice(args.num_cycles, size=num_failures, replace=False))

    # Assign failure modes
    failure_mode_names = list(FAILURE_MODES.keys())
    failure_mode_probs = list(FAILURE_MODES.values())

    # Build work items
    work_items = []
    for i, cycle_data in enumerate(cycle_assignments):
        is_failure = i in failure_indices
        failure_mode = None
        if is_failure:
            failure_mode = rng.choice(failure_mode_names, p=failure_mode_probs)
        seed = rng.integers(0, 2**31)
        work_items.append((cycle_data, is_failure, failure_mode, seed))

    # Generate in parallel
    print(f"Generating {args.num_cycles:,} XML files...")
    results = []
    with Pool(processes=args.workers) as pool:
        for i, result in enumerate(pool.imap_unordered(generate_single_cycle, work_items, chunksize=100)):
            results.append(result)
            if (i + 1) % 5000 == 0:
                print(f"  Progress: {i+1:,}/{args.num_cycles:,} ({(i+1)/args.num_cycles*100:.1f}%)")

    print(f"  Done. Generated {len(results):,} XML files.")

    # Write cycle_summary.csv
    print("Writing cycle_summary.csv...")
    cycle_csv_path = os.path.join(OUTPUT_DIR, "cycle_summary.csv")
    with open(cycle_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Generate alarm.csv from failed cycles
    print("Generating alarm data...")
    alarms = []
    alarm_codes = {
        "seal_leak": ("LEAK-001", "Chamber seal integrity failure", "Critical"),
        "temp_drift": ("TEMP-002", "Sterilization temperature deviation", "High"),
        "pressure_anomaly": ("PRES-003", "Chamber pressure variance exceeded", "High"),
        "sensor_fault": ("SENS-004", "Temperature sensor malfunction", "Medium"),
    }
    for r in results:
        if r["is_failure"]:
            code_info = alarm_codes.get(r["failure_mode"], ("UNK-000", "Unknown", "Low"))
            alarms.append({
                "alarm_id": str(uuid.uuid4()),
                "device_id": r["device_id"],
                "cycle_id": r["cycle_id"],
                "alarm_timestamp": r["timestamp"],
                "alarm_code": code_info[0],
                "alarm_description": code_info[1],
                "severity": code_info[2],
                "acknowledged": rng.choice(["Yes", "No"], p=[0.8, 0.2]),
                "acknowledged_by": f"Tech-{rng.integers(1, 20):02d}" if rng.random() > 0.2 else "",
                "resolution": rng.choice(["Resolved", "Pending", "Escalated"], p=[0.6, 0.25, 0.15]),
                "notes": "",
            })

    alarm_csv_path = os.path.join(OUTPUT_DIR, "alarm.csv")
    with open(alarm_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=alarms[0].keys() if alarms else [])
        writer.writeheader()
        writer.writerows(alarms)
    print(f"  Written {len(alarms)} alarms to {alarm_csv_path}")

    # Generate service.csv (subset of devices with service history)
    print("Generating service data...")
    services = []
    service_types = ["Preventive Maintenance", "Corrective Repair", "Calibration",
                     "Inspection", "Part Replacement"]
    # ~3 service records per device on average over 6 months
    for device in devices:
        num_services = int(rng.poisson(3))
        for _ in range(num_services):
            start = datetime.strptime(DATE_START, "%Y-%m-%d")
            svc_date = start + timedelta(days=int(rng.integers(0, 180)))
            services.append({
                "service_id": str(uuid.uuid4()),
                "device_id": device["device_id"],
                "serial_number": device["serial_number"],
                "service_date": svc_date.strftime("%Y-%m-%d"),
                "service_type": rng.choice(service_types),
                "description": f"Routine {rng.choice(service_types).lower()} performed",
                "technician": f"Tech-{rng.integers(1, 20):02d}",
                "duration_hours": round(float(rng.uniform(0.5, 8.0)), 1),
                "parts_cost": round(float(rng.uniform(0, 2000)), 2),
                "labor_cost": round(float(rng.uniform(50, 600)), 2),
            })

    service_csv_path = os.path.join(OUTPUT_DIR, "service.csv")
    with open(service_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=services[0].keys() if services else [])
        writer.writeheader()
        writer.writerows(services)
    print(f"  Written {len(services)} service records to {service_csv_path}")

    # Summary
    print("\n=== Generation Complete ===")
    print(f"  Cycles:   {len(results):,}")
    print(f"  Failures: {sum(1 for r in results if r['is_failure']):,} ({FAILURE_RATE*100:.1f}%)")
    print(f"  Devices:  {len(devices)}")
    print(f"  Alarms:   {len(alarms):,}")
    print(f"  Services: {len(services):,}")
    print(f"\nOutput directory: {os.path.abspath(OUTPUT_DIR)}")

    # Calculate approximate data size
    xml_size = sum(os.path.getsize(os.path.join(XML_DIR, f))
                   for f in os.listdir(XML_DIR) if f.endswith(".xml.gz"))
    print(f"  XML total size: {xml_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
