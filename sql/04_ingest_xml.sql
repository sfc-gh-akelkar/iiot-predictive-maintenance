-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 4: Ingest XML Files (MEASURED)
-- ============================================================================
-- This script ingests cycle XMLs and shreds them into relational tables.
-- Run on IIOT_INGEST_WH (MEDIUM, 4 cr/hr) for cost measurement.
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;
USE DATABASE IIOT_PREDICTIVE_MAINT_DB;
USE SCHEMA RAW;
USE WAREHOUSE IIOT_INGEST_WH;

-- Record start time for metering
SET benchmark_start = CURRENT_TIMESTAMP();

-- ============================================================================
-- Step 4a: Load raw XML into VARIANT table
-- ============================================================================
COPY INTO CYCLE_XML_RAW (FILENAME, RAW_XML)
FROM (
    SELECT
        METADATA$FILENAME,
        $1
    FROM @IIOT_STAGE/xml/
)
FILE_FORMAT = (TYPE = XML)
PATTERN = '.*\.xml\.gz'
ON_ERROR = 'CONTINUE';

-- Check row count
SELECT COUNT(*) AS raw_xml_rows FROM CYCLE_XML_RAW;

-- ============================================================================
-- Step 4b: Shred XML into CYCLE summary table
-- ============================================================================
INSERT INTO CYCLE
SELECT
    XMLGET(XMLGET(raw_xml, 'DeviceInfo'), '$'):"@CYCLE_ID"::VARCHAR AS cycle_id,
    NULL AS device_id,  -- Will join to device table later
    XMLGET(XMLGET(raw_xml, 'DeviceInfo'), 'SerialNumber'):"$"::VARCHAR AS serial_number,
    -- Timestamp from first analog reading
    TRY_TO_TIMESTAMP(
        XMLGET(
            GET(XMLGET(XMLGET(XMLGET(raw_xml, 'Analog'), 'AnalogReadings'), 'Readings'), 0),
            'Reading'
        ):"@TimeStamp"::VARCHAR
    ) AS cycle_timestamp,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'CycleCount'):"$"::NUMBER AS cycle_count,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'CycleType'):"$"::VARCHAR AS cycle_type,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'SterilizeTemp'):"$"::NUMBER(6,1) AS sterilize_temp,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'SterTime'):"$"::VARCHAR AS ster_time,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'DryTime'):"$"::VARCHAR AS dry_time,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'SummaryTotalCycle'):"$"::VARCHAR AS summary_total_cycle,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'SummaryCycleStatus'):"$"::NUMBER AS summary_cycle_status,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'MinTemp'):"$"::NUMBER(6,1) AS min_temp,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'MaxTemp'):"$"::NUMBER(6,1) AS max_temp,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'LeakRate'):"$"::NUMBER(8,3) AS leak_rate,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'LoadNumber'):"$"::VARCHAR AS load_number,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'ProgramPartNo'):"$"::VARCHAR AS program_part_no,
    XMLGET(XMLGET(raw_xml, 'CycleFields'), 'ProgramRevision'):"$"::VARCHAR AS program_revision,
    XMLGET(XMLGET(raw_xml, 'DeviceInfo'), 'Family'):"$"::VARCHAR AS family,
    XMLGET(XMLGET(raw_xml, 'DeviceInfo'), 'DeviceType'):"$"::VARCHAR AS device_type_name,
    XMLGET(XMLGET(raw_xml, 'ProConnect'), 'Rev'):"$"::VARCHAR AS firmware_rev,
    XMLGET(XMLGET(raw_xml, 'ProConnect'), 'Build'):"$"::VARCHAR AS firmware_build
FROM CYCLE_XML_RAW;

SELECT COUNT(*) AS cycle_rows FROM CYCLE;

-- ============================================================================
-- Step 4c: Shred XML into CYCLE_ANALOG time-series table
-- This is the expensive operation: 47K cycles x 6 channels x ~230 readings
-- ============================================================================
INSERT INTO CYCLE_ANALOG
SELECT
    XMLGET(XMLGET(raw_xml, 'DeviceInfo'), '$'):"@CYCLE_ID"::VARCHAR AS cycle_id,
    rc.value:"@CID"::NUMBER AS channel_id,
    ch.value:"@Desc"::VARCHAR AS channel_name,
    rc.value:"@Unit"::VARCHAR AS channel_unit,
    reading.value:"@TimeIndex"::NUMBER AS time_index,
    TRY_TO_TIMESTAMP(reading.value:"@TimeStamp"::VARCHAR) AS reading_timestamp,
    rc.value:"@Value"::NUMBER(10,2) AS value
FROM CYCLE_XML_RAW,
    LATERAL FLATTEN(input => XMLGET(XMLGET(XMLGET(raw_xml, 'Analog'), 'AnalogReadings'), 'Readings'):"$") AS reading,
    LATERAL FLATTEN(input => XMLGET(reading.value, 'Channels'):"$") AS rc,
    LATERAL FLATTEN(input => XMLGET(XMLGET(XMLGET(raw_xml, 'Analog'), 'AnalogReadings'), 'Channels'):"$") AS ch
WHERE ch.value:"@ID"::NUMBER = rc.value:"@CID"::NUMBER;

SELECT COUNT(*) AS analog_rows FROM CYCLE_ANALOG;

-- ============================================================================
-- Record end time and check metering
-- ============================================================================
SELECT
    $benchmark_start AS start_time,
    CURRENT_TIMESTAMP() AS end_time,
    DATEDIFF('second', $benchmark_start, CURRENT_TIMESTAMP()) AS elapsed_seconds;

-- Query metering (may need 1-2 hour delay for ACCOUNT_USAGE, use table function for real-time)
SELECT *
FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_METERING_HISTORY(
    DATE_RANGE_START => $benchmark_start::TIMESTAMP_LTZ,
    DATE_RANGE_END => CURRENT_TIMESTAMP()::TIMESTAMP_LTZ,
    WAREHOUSE_NAME => 'IIOT_INGEST_WH'
));
