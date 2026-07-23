-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 6: Feature Engineering (Dynamic Table - MEASURED)
-- ============================================================================
-- Run on IIOT_FEATURE_WH (MEDIUM, 4 cr/hr) for cost measurement.
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;
USE DATABASE IIOT_PREDICTIVE_MAINT_DB;
USE SCHEMA FEATURES;
USE WAREHOUSE IIOT_FEATURE_WH;

SET feature_start = CURRENT_TIMESTAMP();

-- ============================================================================
-- Per-cycle analog features (aggregated from ~230 readings x 6 channels)
-- ============================================================================
CREATE OR REPLACE DYNAMIC TABLE CYCLE_FEATURES
    TARGET_LAG = '1 hour'
    WAREHOUSE = IIOT_FEATURE_WH
AS
SELECT
    c.CYCLE_ID,
    c.DEVICE_ID,
    c.SERIAL_NUMBER,
    c.CYCLE_TIMESTAMP,
    c.CYCLE_COUNT,
    c.CYCLE_TYPE,
    c.SUMMARY_CYCLE_STATUS,
    c.LEAK_RATE,
    c.MIN_TEMP,
    c.MAX_TEMP,
    c.MAX_TEMP - c.MIN_TEMP AS TEMP_RANGE,
    c.FAMILY,
    c.FIRMWARE_REV,

    -- Chamber Pressure (channel 0) features
    AVG(CASE WHEN a.CHANNEL_ID = 0 THEN a.VALUE END) AS AVG_CHAMBER_PRESSURE,
    MAX(CASE WHEN a.CHANNEL_ID = 0 THEN a.VALUE END) AS MAX_CHAMBER_PRESSURE,
    MIN(CASE WHEN a.CHANNEL_ID = 0 THEN a.VALUE END) AS MIN_CHAMBER_PRESSURE,
    STDDEV(CASE WHEN a.CHANNEL_ID = 0 THEN a.VALUE END) AS STDDEV_CHAMBER_PRESSURE,

    -- Jacket Pressure (channel 1) features
    AVG(CASE WHEN a.CHANNEL_ID = 1 THEN a.VALUE END) AS AVG_JACKET_PRESSURE,
    MAX(CASE WHEN a.CHANNEL_ID = 1 THEN a.VALUE END) AS MAX_JACKET_PRESSURE,
    STDDEV(CASE WHEN a.CHANNEL_ID = 1 THEN a.VALUE END) AS STDDEV_JACKET_PRESSURE,

    -- Chamber Temp Probe 1 (channel 2) features
    AVG(CASE WHEN a.CHANNEL_ID = 2 THEN a.VALUE END) AS AVG_CHAMBER_TEMP,
    MAX(CASE WHEN a.CHANNEL_ID = 2 THEN a.VALUE END) AS MAX_CHAMBER_TEMP,
    MIN(CASE WHEN a.CHANNEL_ID = 2 THEN a.VALUE END) AS MIN_CHAMBER_TEMP,
    STDDEV(CASE WHEN a.CHANNEL_ID = 2 THEN a.VALUE END) AS STDDEV_CHAMBER_TEMP,

    -- Chamber Temp Probe 2 (channel 3) - cross-check with probe 1
    AVG(CASE WHEN a.CHANNEL_ID = 3 THEN a.VALUE END) AS AVG_CHAMBER_TEMP_2,
    ABS(AVG(CASE WHEN a.CHANNEL_ID = 2 THEN a.VALUE END) -
        AVG(CASE WHEN a.CHANNEL_ID = 3 THEN a.VALUE END)) AS TEMP_PROBE_DIVERGENCE,

    -- Drain Temperature (channel 5)
    AVG(CASE WHEN a.CHANNEL_ID = 5 THEN a.VALUE END) AS AVG_DRAIN_TEMP,
    MAX(CASE WHEN a.CHANNEL_ID = 5 THEN a.VALUE END) AS MAX_DRAIN_TEMP,

    -- Jacket Temperature (channel 7)
    AVG(CASE WHEN a.CHANNEL_ID = 7 THEN a.VALUE END) AS AVG_JACKET_TEMP,
    MAX(CASE WHEN a.CHANNEL_ID = 7 THEN a.VALUE END) AS MAX_JACKET_TEMP,

    -- Pressure differential (jacket - chamber)
    AVG(CASE WHEN a.CHANNEL_ID = 1 THEN a.VALUE END) -
        AVG(CASE WHEN a.CHANNEL_ID = 0 THEN a.VALUE END) AS AVG_PRESSURE_DIFFERENTIAL,

    -- Number of readings (proxy for cycle duration)
    COUNT(DISTINCT a.TIME_INDEX) / 6 AS NUM_READINGS,

    -- Readings count per channel (detect sensor dropouts)
    COUNT(CASE WHEN a.CHANNEL_ID = 0 AND a.VALUE > 0 THEN 1 END) AS PRESSURE_NONZERO_COUNT,
    COUNT(CASE WHEN a.CHANNEL_ID = 2 AND a.VALUE > 0 THEN 1 END) AS TEMP_NONZERO_COUNT

FROM RAW.CYCLE c
LEFT JOIN RAW.CYCLE_ANALOG a ON c.CYCLE_ID = a.CYCLE_ID
GROUP BY
    c.CYCLE_ID, c.DEVICE_ID, c.SERIAL_NUMBER, c.CYCLE_TIMESTAMP,
    c.CYCLE_COUNT, c.CYCLE_TYPE, c.SUMMARY_CYCLE_STATUS, c.LEAK_RATE,
    c.MIN_TEMP, c.MAX_TEMP, c.FAMILY, c.FIRMWARE_REV;

-- ============================================================================
-- Per-device rolling features
-- ============================================================================
CREATE OR REPLACE DYNAMIC TABLE DEVICE_ROLLING_FEATURES
    TARGET_LAG = '1 hour'
    WAREHOUSE = IIOT_FEATURE_WH
AS
SELECT
    cf.DEVICE_ID,
    cf.CYCLE_ID,
    cf.CYCLE_TIMESTAMP,

    -- Rolling failure rate (last 30 cycles per device)
    AVG(CASE WHEN cf.SUMMARY_CYCLE_STATUS != 0 THEN 1 ELSE 0 END)
        OVER (PARTITION BY cf.DEVICE_ID ORDER BY cf.CYCLE_TIMESTAMP
              ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) AS FAILURE_RATE_LAST_30,

    -- Rolling avg leak rate (trend detection)
    AVG(cf.LEAK_RATE)
        OVER (PARTITION BY cf.DEVICE_ID ORDER BY cf.CYCLE_TIMESTAMP
              ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) AS AVG_LEAK_RATE_LAST_10,

    -- Rolling max temp trend
    AVG(cf.MAX_CHAMBER_TEMP)
        OVER (PARTITION BY cf.DEVICE_ID ORDER BY cf.CYCLE_TIMESTAMP
              ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) AS AVG_MAX_TEMP_LAST_10,

    -- Cycle count since last failure
    cf.CYCLE_COUNT - COALESCE(
        MAX(CASE WHEN cf.SUMMARY_CYCLE_STATUS != 0 THEN cf.CYCLE_COUNT END)
            OVER (PARTITION BY cf.DEVICE_ID ORDER BY cf.CYCLE_TIMESTAMP
                  ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
        0
    ) AS CYCLES_SINCE_LAST_FAILURE,

    -- Rolling pressure variance (degradation signal)
    AVG(cf.STDDEV_CHAMBER_PRESSURE)
        OVER (PARTITION BY cf.DEVICE_ID ORDER BY cf.CYCLE_TIMESTAMP
              ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) AS AVG_PRESSURE_VARIANCE_LAST_10

FROM FEATURES.CYCLE_FEATURES cf;

-- ============================================================================
-- Measure feature refresh cost
-- ============================================================================
SELECT
    $feature_start AS start_time,
    CURRENT_TIMESTAMP() AS end_time,
    DATEDIFF('second', $feature_start, CURRENT_TIMESTAMP()) AS elapsed_seconds;

-- Check metering
SELECT *
FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_METERING_HISTORY(
    DATE_RANGE_START => $feature_start::TIMESTAMP_LTZ,
    DATE_RANGE_END => CURRENT_TIMESTAMP()::TIMESTAMP_LTZ,
    WAREHOUSE_NAME => 'IIOT_FEATURE_WH'
));
