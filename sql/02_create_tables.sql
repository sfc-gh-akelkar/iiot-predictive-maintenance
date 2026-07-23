-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 2: Create Tables
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;
USE DATABASE IIOT_PREDICTIVE_MAINT_DB;
USE SCHEMA RAW;

-- ============================================================================
-- Raw XML landing table (VARIANT)
-- ============================================================================
CREATE OR REPLACE TABLE CYCLE_XML_RAW (
    FILENAME VARCHAR,
    RAW_XML VARIANT,
    LOADED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Raw cycle XML files loaded as VARIANT for subsequent shredding';

-- ============================================================================
-- Device master (from device.csv)
-- ============================================================================
CREATE OR REPLACE TABLE DEVICE (
    DEVICE_ID VARCHAR PRIMARY KEY,
    SERIAL_NUMBER VARCHAR NOT NULL,
    LOCAL_NAME VARCHAR,
    FAMILY VARCHAR,
    DEVICE_TYPE VARCHAR,
    QUESTRA_ASSET_NUMBER VARCHAR,
    FIRMWARE_REV VARCHAR,
    FIRMWARE_BUILD VARCHAR,
    INSTALL_DATE DATE,
    LOCATION VARCHAR,
    STATUS VARCHAR
)
COMMENT = 'Device master data - sterilizer equipment registry';

-- ============================================================================
-- Cycle summary (shredded from XML CycleFields + DeviceInfo)
-- ============================================================================
CREATE OR REPLACE TABLE CYCLE (
    CYCLE_ID VARCHAR PRIMARY KEY,
    DEVICE_ID VARCHAR,
    SERIAL_NUMBER VARCHAR,
    CYCLE_TIMESTAMP TIMESTAMP_NTZ,
    CYCLE_COUNT NUMBER,
    CYCLE_TYPE VARCHAR,
    STERILIZE_TEMP NUMBER(6,1),
    STER_TIME VARCHAR,
    DRY_TIME VARCHAR,
    SUMMARY_TOTAL_CYCLE VARCHAR,
    SUMMARY_CYCLE_STATUS NUMBER,
    MIN_TEMP NUMBER(6,1),
    MAX_TEMP NUMBER(6,1),
    LEAK_RATE NUMBER(8,3),
    LOAD_NUMBER VARCHAR,
    PROGRAM_PART_NO VARCHAR,
    PROGRAM_REVISION VARCHAR,
    FAMILY VARCHAR,
    DEVICE_TYPE_NAME VARCHAR,
    FIRMWARE_REV VARCHAR,
    FIRMWARE_BUILD VARCHAR
)
COMMENT = 'Cycle summary data shredded from XML CycleFields section';

-- ============================================================================
-- Analog time-series (shredded from XML Analog/Readings)
-- ============================================================================
CREATE OR REPLACE TABLE CYCLE_ANALOG (
    CYCLE_ID VARCHAR NOT NULL,
    CHANNEL_ID NUMBER NOT NULL,
    CHANNEL_NAME VARCHAR,
    CHANNEL_UNIT VARCHAR,
    TIME_INDEX NUMBER NOT NULL,
    READING_TIMESTAMP TIMESTAMP_NTZ,
    VALUE NUMBER(10,2)
)
CLUSTER BY (CYCLE_ID)
COMMENT = 'Analog time-series readings: 6 channels x ~230 readings per cycle = ~65M rows at 10% scale';

-- ============================================================================
-- Alarm history (from alarm.csv)
-- ============================================================================
CREATE OR REPLACE TABLE ALARM (
    ALARM_ID VARCHAR PRIMARY KEY,
    DEVICE_ID VARCHAR,
    CYCLE_ID VARCHAR,
    ALARM_TIMESTAMP TIMESTAMP_NTZ,
    ALARM_CODE VARCHAR,
    ALARM_DESCRIPTION VARCHAR,
    SEVERITY VARCHAR,
    ACKNOWLEDGED VARCHAR,
    ACKNOWLEDGED_BY VARCHAR,
    RESOLUTION VARCHAR,
    NOTES VARCHAR
)
COMMENT = 'Alarm events linked to failed cycles';

-- ============================================================================
-- Service history (from service.csv)
-- ============================================================================
CREATE OR REPLACE TABLE SERVICE (
    SERVICE_ID VARCHAR PRIMARY KEY,
    DEVICE_ID VARCHAR,
    SERIAL_NUMBER VARCHAR,
    SERVICE_DATE DATE,
    SERVICE_TYPE VARCHAR,
    DESCRIPTION VARCHAR,
    TECHNICIAN VARCHAR,
    DURATION_HOURS NUMBER(5,1),
    PARTS_COST NUMBER(10,2),
    LABOR_COST NUMBER(10,2)
)
COMMENT = 'Service history for devices';
