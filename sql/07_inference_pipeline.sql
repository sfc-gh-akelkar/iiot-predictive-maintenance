-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 7: Inference Pipeline Setup
-- ============================================================================
-- Batch scoring infrastructure. Model training happens in notebook.
-- Run on IIOT_INFERENCE_WH (XSMALL, 1 cr/hr) for cost measurement.
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;
USE DATABASE IIOT_PREDICTIVE_MAINT_DB;
USE SCHEMA ML;
USE WAREHOUSE IIOT_INFERENCE_WH;

-- ============================================================================
-- Predictions output table
-- ============================================================================
CREATE OR REPLACE TABLE PREDICTIONS (
    PREDICTION_ID VARCHAR DEFAULT UUID_STRING(),
    CYCLE_ID VARCHAR NOT NULL,
    DEVICE_ID VARCHAR,
    PREDICTION_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PREDICTED_STATUS NUMBER,          -- 0=pass, 1-4=failure modes
    PREDICTED_STATUS_PROBA NUMBER(5,4),
    PREDICTED_RUL_CYCLES NUMBER,      -- Remaining useful life (cycles to next failure)
    MODEL_VERSION VARCHAR,
    BATCH_ID VARCHAR
);

-- ============================================================================
-- Batch scoring procedure (called daily in production)
-- ============================================================================
CREATE OR REPLACE PROCEDURE SCORE_DAILY_CYCLES(batch_date DATE)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
    -- In production, this would call the registered model via:
    -- SELECT model!PREDICT(...) FROM features WHERE cycle_date = :batch_date
    -- For benchmarking, we simulate with a placeholder that exercises the same data path

    LET batch_id := UUID_STRING();

    INSERT INTO PREDICTIONS (CYCLE_ID, DEVICE_ID, PREDICTED_STATUS, PREDICTED_STATUS_PROBA, PREDICTED_RUL_CYCLES, MODEL_VERSION, BATCH_ID)
    SELECT
        cf.CYCLE_ID,
        cf.DEVICE_ID,
        -- Placeholder scoring logic (will be replaced with actual model)
        CASE
            WHEN cf.LEAK_RATE > 1.3 THEN 1
            WHEN cf.MAX_CHAMBER_TEMP < 130 THEN 2
            WHEN cf.STDDEV_CHAMBER_PRESSURE > 30 THEN 3
            ELSE 0
        END AS predicted_status,
        UNIFORM(0.5, 0.99, RANDOM()) AS predicted_status_proba,
        GREATEST(1, 100 - (cf.LEAK_RATE * 20)::INT) AS predicted_rul_cycles,
        'v1.0-benchmark' AS model_version,
        :batch_id AS batch_id
    FROM FEATURES.CYCLE_FEATURES cf
    WHERE cf.CYCLE_TIMESTAMP::DATE = :batch_date;

    RETURN 'Scored ' || (SELECT COUNT(*) FROM PREDICTIONS WHERE BATCH_ID = :batch_id) || ' cycles for batch ' || :batch_id;
END;
$$;

-- ============================================================================
-- Simulate 7 days of scoring for cost measurement
-- ============================================================================
SET inference_start = CURRENT_TIMESTAMP();

CALL SCORE_DAILY_CYCLES('2025-07-01'::DATE);
CALL SCORE_DAILY_CYCLES('2025-07-02'::DATE);
CALL SCORE_DAILY_CYCLES('2025-07-03'::DATE);
CALL SCORE_DAILY_CYCLES('2025-07-04'::DATE);
CALL SCORE_DAILY_CYCLES('2025-07-05'::DATE);
CALL SCORE_DAILY_CYCLES('2025-07-06'::DATE);
CALL SCORE_DAILY_CYCLES('2025-07-07'::DATE);

-- Check results
SELECT
    BATCH_ID,
    COUNT(*) AS rows_scored,
    AVG(PREDICTED_STATUS_PROBA) AS avg_confidence,
    SUM(CASE WHEN PREDICTED_STATUS != 0 THEN 1 ELSE 0 END) AS predicted_failures
FROM PREDICTIONS
GROUP BY BATCH_ID
ORDER BY BATCH_ID;

-- Measure
SELECT
    $inference_start AS start_time,
    CURRENT_TIMESTAMP() AS end_time,
    DATEDIFF('second', $inference_start, CURRENT_TIMESTAMP()) AS elapsed_seconds;

SELECT *
FROM TABLE(INFORMATION_SCHEMA.WAREHOUSE_METERING_HISTORY(
    DATE_RANGE_START => $inference_start::TIMESTAMP_LTZ,
    DATE_RANGE_END => CURRENT_TIMESTAMP()::TIMESTAMP_LTZ,
    WAREHOUSE_NAME => 'IIOT_INFERENCE_WH'
));
