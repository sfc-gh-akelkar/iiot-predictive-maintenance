"""Upload generated XML files to Snowflake internal stage using PUT.

Usage:
    cd generator/
    python upload_to_stage.py
"""

import os
import time

import snowflake.connector

DATA_DIR = os.path.abspath("../data")
XML_DIR = os.path.join(DATA_DIR, "xml")

CONNECTION_PARAMS = {
    "connection_name": "akelkar-demo-account",
}


def main():
    print("Connecting to Snowflake...")
    conn = snowflake.connector.connect(**CONNECTION_PARAMS)
    cur = conn.cursor()

    cur.execute("USE ROLE SF_INTELLIGENCE_DEMO")
    cur.execute("USE DATABASE IIOT_PREDICTIVE_MAINT_DB")
    cur.execute("USE SCHEMA RAW")
    cur.execute("USE WAREHOUSE IIOT_INGEST_WH")

    # PUT all .xml.gz files in one go using wildcard
    xml_pattern = os.path.join(XML_DIR, "*.xml.gz")
    print(f"Uploading XMLs from: {xml_pattern}")
    print(f"File count: {len(os.listdir(XML_DIR))}")

    start = time.time()
    cur.execute(f"""
        PUT 'file://{xml_pattern}'
        @IIOT_STAGE/xml/
        PARALLEL = 10
        AUTO_COMPRESS = FALSE
        OVERWRITE = TRUE
    """)

    elapsed = time.time() - start
    results = cur.fetchall()
    print(f"\nPUT completed in {elapsed:.1f}s")
    print(f"Files uploaded: {len(results)}")
    if results:
        # Check for any failures
        statuses = [r[6] for r in results]  # status column
        uploaded = sum(1 for s in statuses if s == "UPLOADED")
        skipped = sum(1 for s in statuses if s == "SKIPPED")
        print(f"  Uploaded: {uploaded}, Skipped: {skipped}")

    # Verify
    cur.execute("LIST @IIOT_STAGE/xml/ PATTERN = '.*\\.xml\\.gz'")
    staged_files = cur.fetchall()
    print(f"\nFiles on stage: {len(staged_files)}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
