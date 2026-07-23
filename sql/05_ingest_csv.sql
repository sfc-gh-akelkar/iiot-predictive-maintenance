-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 5: Ingest CSV Files
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;
USE DATABASE IIOT_PREDICTIVE_MAINT_DB;
USE SCHEMA RAW;
USE WAREHOUSE IIOT_INGEST_WH;

-- ============================================================================
-- Load device.csv
-- ============================================================================
COPY INTO DEVICE
FROM @IIOT_STAGE/device.csv
FILE_FORMAT = CSV_FORMAT
ON_ERROR = 'CONTINUE';

-- ============================================================================
-- Load alarm.csv
-- ============================================================================
COPY INTO ALARM
FROM @IIOT_STAGE/alarm.csv
FILE_FORMAT = CSV_FORMAT
ON_ERROR = 'CONTINUE';

-- ============================================================================
-- Load service.csv
-- ============================================================================
COPY INTO SERVICE
FROM @IIOT_STAGE/service.csv
FILE_FORMAT = CSV_FORMAT
ON_ERROR = 'CONTINUE';

-- ============================================================================
-- Update CYCLE.DEVICE_ID from device table join on serial number
-- ============================================================================
UPDATE CYCLE c
SET c.DEVICE_ID = d.DEVICE_ID
FROM DEVICE d
WHERE c.SERIAL_NUMBER = d.SERIAL_NUMBER;

-- ============================================================================
-- Verify
-- ============================================================================
SELECT 'DEVICE' AS tbl, COUNT(*) AS rows FROM DEVICE
UNION ALL SELECT 'ALARM', COUNT(*) FROM ALARM
UNION ALL SELECT 'SERVICE', COUNT(*) FROM SERVICE
UNION ALL SELECT 'CYCLE', COUNT(*) FROM CYCLE
UNION ALL SELECT 'CYCLE_ANALOG', COUNT(*) FROM CYCLE_ANALOG;
