-- ============================================================================
-- IIoT Predictive Maintenance PoC
-- Step 3: Create External Stage + File Formats
-- ============================================================================

USE ROLE SF_INTELLIGENCE_DEMO;
USE DATABASE IIOT_PREDICTIVE_MAINT_DB;
USE SCHEMA RAW;

-- Internal stage for IIoT data
CREATE OR REPLACE STAGE IIOT_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Internal stage for IIoT cycle XMLs and CSVs';

-- File format for XML ingestion
CREATE OR REPLACE FILE FORMAT XML_FORMAT
    TYPE = XML
    STRIP_OUTER_ELEMENT = FALSE
    COMMENT = 'XML format for ProConnect cycle files';

-- File format for CSV ingestion
CREATE OR REPLACE FILE FORMAT CSV_FORMAT
    TYPE = CSV
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL', 'null')
    COMMENT = 'CSV format for alarm/service/device files';

-- Verify stage access
LIST @IIOT_S3_STAGE;
