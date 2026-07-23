-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 1: Setup Database, Schemas, and Warehouses
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;

-- Database
CREATE DATABASE IF NOT EXISTS IIOT_PREDICTIVE_MAINT_DB
    COMMENT = 'IIoT Predictive Maintenance cost estimation PoC';

-- Schemas
CREATE SCHEMA IF NOT EXISTS IIOT_PREDICTIVE_MAINT_DB.RAW
    COMMENT = 'Raw ingested data from cycle XMLs and CSVs';
CREATE SCHEMA IF NOT EXISTS IIOT_PREDICTIVE_MAINT_DB.FEATURES
    COMMENT = 'Feature engineering layer for ML';
CREATE SCHEMA IF NOT EXISTS IIOT_PREDICTIVE_MAINT_DB.ML
    COMMENT = 'ML models, predictions, and scoring';

-- Warehouses for benchmarking (separate for clean metering)
CREATE WAREHOUSE IF NOT EXISTS IIOT_INGEST_WH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Ingestion workloads - MEDIUM (4 cr/hr)';

CREATE WAREHOUSE IF NOT EXISTS IIOT_FEATURE_WH
    WAREHOUSE_SIZE = 'MEDIUM'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Feature engineering - MEDIUM (4 cr/hr)';

-- ML training runs on IIOT_FEATURE_WH (standard MEDIUM, 4 cr/hr)
-- SP-optimized not needed at this data scale (47K rows x 26 features)

CREATE WAREHOUSE IF NOT EXISTS IIOT_INFERENCE_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Inference/scoring - XSMALL (1 cr/hr)';
