# IIoT Predictive Maintenance — Snowflake Cost Estimation PoC

End-to-end predictive maintenance pipeline for sterilization equipment, running entirely in Snowflake. Demonstrates XML telemetry ingestion, feature engineering, ML training, and inference — with empirical credit consumption measurements at each phase.

## What This Proves

A medical device manufacturer's IIoT workload (currently Python + LangChain on local infrastructure) can be consolidated into Snowflake at **75-88% lower cost** than self-managed VMs, with zero operational overhead and full governance.

## Measured Results

| Phase | Duration | Credits | Cost |
|-------|----------|---------|------|
| XML ingestion (47K files → 69.6M rows) | 317 sec | 0.35 | $1.05 |
| Feature engineering (69.6M → 47K features) | 4.7 sec | 0.005 | $0.02 |
| Model training (XGBoost, 47K × 26 features) | ~30 sec | 0.03 | $0.10 |
| Batch inference (47K predictions) | 2.2 sec | 0.001 | $0.003 |

**Monthly projections:**
- Pilot (300 devices): $32-48/month
- Full scale (10,000 devices): $400-530/month

## Data Profile

- **Source:** ProConnect sterilizer cycle XML (6 analog sensor channels at 5-second intervals)
- **Scale:** 47,000 cycles (10% of production), 113 devices, 69.6M time-series rows
- **Failure modes:** Seal leak, temperature drift, pressure anomaly, sensor fault (8.8% failure rate)

## Repository Structure

```
├── generator/                  # Synthetic data generation
│   ├── generate_cycle_xml.py   # Main generator (multiprocessing, 47K XMLs)
│   ├── analog_curves.py        # Sterilization curve physics
│   ├── failure_injection.py    # Failure mode injection
│   ├── config.py               # Parameters and channel definitions
│   └── upload_to_stage.py      # PUT files to Snowflake stage
│
├── sql/                        # Snowflake DDL and pipeline (run in order)
│   ├── 01_setup_schema.sql     # Database, schemas, warehouses
│   ├── 02_create_tables.sql    # All table DDL
│   ├── 03_create_stage.sql     # Internal stage + file formats
│   ├── 04_ingest_xml.sql       # COPY INTO + FLATTEN (measured)
│   ├── 05_ingest_csv.sql       # CSV loads for alarm/service/device
│   ├── 06_feature_engineering.sql  # Dynamic Table for ML features
│   └── 07_inference_pipeline.sql   # Batch scoring setup
│
├── notebooks/
│   └── 02_train_model.ipynb    # XGBoost training + Model Registry
│
└── docs/
    └── cost_estimate.md        # Full cost analysis with projections
```

## Quick Start

### 1. Generate synthetic data
```bash
cd generator/
pip install -r requirements.txt
python generate_cycle_xml.py --num-cycles 47000 --workers 10
```

### 2. Upload to Snowflake
```bash
python upload_to_stage.py
```

### 3. Run SQL pipeline
Execute scripts 01-07 in order in Snowsight or via SnowSQL.

### 4. Train model
Run `notebooks/02_train_model.ipynb` (requires `snowflake-ml-python`).

## Snowflake Objects Created

- **Database:** `IIOT_PREDICTIVE_MAINT_DB`
- **Schemas:** `RAW`, `FEATURES`, `ML`
- **Warehouses:** `IIOT_INGEST_WH` (MEDIUM), `IIOT_FEATURE_WH` (MEDIUM), `IIOT_INFERENCE_WH` (XSMALL)
- **Key tables:** `CYCLE_ANALOG` (69.6M rows), `CYCLE` (47K), `CYCLE_FEATURES` (47K)

## Key Snowflake Capabilities Demonstrated

- XML ingestion via `COPY INTO` + `LATERAL FLATTEN` for time-series shredding
- Dynamic Tables for incremental feature engineering
- Snowpark ML for XGBoost training (standard warehouse — no SP-optimized needed)
- Model Registry for versioned model governance
- Per-second billing with auto-suspend (zero idle cost)

## License

Internal use only — Snowflake SE demo asset.
