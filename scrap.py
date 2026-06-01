import time
import requests
import pandas as pd
import mysql.connector
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
import os

# =====================================
# DB CONNECTION
# =====================================

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    autocommit=False
)

cursor = conn.cursor()

print("DB Connected")


# =====================================
# HTML -> CSV
# =====================================

def generate_csv_from_html():

    # =====================================
    # TRUE  = Real Website
    # FALSE = Local Testing HTML
    # =====================================

    USE_REAL_WEBSITE = False

    if USE_REAL_WEBSITE:

        print("Reading from LIVE Website...")

        url = "https://jjm.up.gov.in/NamamiGange/RiverwiseDrainsStatus"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        with open(
            "river_wise_drains_page.html",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(response.text)

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

    else:

        print("Reading from LOCAL HTML...")

        with open(
            "river_wise_drains_page.html",
            "r",
            encoding="utf-8"
        ) as f:

            html = f.read()

        soup = BeautifulSoup(
            html,
            "lxml"
        )

    table = soup.find(
        "table",
        id="tableReportTable"
    )

    if table is None:
        raise Exception("tableReportTable not found")

    rows = table.find_all("tr")

    data = []

    current_river = ""

    for row in rows:

        cols = row.find_all("td")

        if not cols:
            continue

        values = [
            col.get_text(strip=True)
            for col in cols
        ]

        if not values:
            continue

        first_col = values[0].strip().lower()

        # Skip Grand Total
        if first_col == "total":
            continue

        # Skip Total Aami, Total Betwa etc.
        if first_col.startswith("total"):
            continue

        # Main River Row
        if len(values) == 13:

            current_river = values[1]

            data.append({
                "River": values[1],
                "District": values[2],
                "TotalDrains": values[3],
                "TotalDischargeMLD": values[4],
                "TappedDrains": values[5],
                "TappedDischargeMLD": values[6],
                "UntappedDrains": values[7],
                "UntappedDischargeMLD": values[8],
                "PartialTappedDrains": values[9],
                "PartialTappedDischargeMLD": values[10],
                "NotToBeTappedDrains": values[11],
                "NotToBeTappedDischargeMLD": values[12]
            })

        # Rowspan Row
        elif len(values) == 11:

            data.append({
                "River": current_river,
                "District": values[0],
                "TotalDrains": values[1],
                "TotalDischargeMLD": values[2],
                "TappedDrains": values[3],
                "TappedDischargeMLD": values[4],
                "UntappedDrains": values[5],
                "UntappedDischargeMLD": values[6],
                "PartialTappedDrains": values[7],
                "PartialTappedDischargeMLD": values[8],
                "NotToBeTappedDrains": values[9],
                "NotToBeTappedDischargeMLD": values[10]
            })

    df = pd.DataFrame(data)

    # Same River = Same SrNo
    df["SrNo"] = pd.factorize(df["River"])[0] + 1

    cols = ["SrNo"] + [c for c in df.columns if c != "SrNo"]
    df = df[cols]

    print("Rows =", len(df))

    df.to_csv(
        "river_wise_drains.csv",
        index=False
    )

    print("CSV Created Successfully")


# =====================================
# MAIN
# =====================================

def clear_current():

    cursor.execute("USE River_Wise_Drains")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    # Child Tables
    cursor.execute("TRUNCATE TABLE not_to_be_tapped_drains")
    cursor.execute("TRUNCATE TABLE partial_tapped_drains")
    cursor.execute("TRUNCATE TABLE untapped_drains")
    cursor.execute("TRUNCATE TABLE tapped_drains")

    # Parent
    cursor.execute("TRUNCATE TABLE drain_master")

    # Parent of drain_master
    cursor.execute("TRUNCATE TABLE districts")

    # Root Table
    cursor.execute("TRUNCATE TABLE rivers")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    conn.commit()

    cursor.execute("""
        SELECT COUNT(*)
        FROM partial_tapped_drains
    """)

    print(
        "PARTIAL COUNT AFTER CLEAR =",
        cursor.fetchone()[0]
    )

    print("Current DB Cleared")

def clear_audit():

    cursor.execute("USE River_Wise_Drains_Audit")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    cursor.execute("TRUNCATE TABLE not_to_be_tapped_drains")
    cursor.execute("TRUNCATE TABLE partial_tapped_drains")
    cursor.execute("TRUNCATE TABLE untapped_drains")
    cursor.execute("TRUNCATE TABLE tapped_drains")
    cursor.execute("TRUNCATE TABLE drain_master")
    cursor.execute("TRUNCATE TABLE districts")
    cursor.execute("TRUNCATE TABLE rivers")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    conn.commit()

    print("Audit DB Cleared")

def load_csv():

    cursor.execute("USE River_Wise_Drains")

    scrape_time = datetime.now()

    df = pd.read_csv("river_wise_drains.csv")




    river_map = {}
    district_map = {}

    for _, row in df.iterrows():

        river = row["River"]
        if pd.isna(river) or str(river).strip() == "":
            river = None
        district = row["District"]

        # =====================
        # RIVER
        # =====================

        river = str(row["River"]).strip()

        if river == "" :
            river = None

        if river not in river_map:
            cursor.execute("""
                           INSERT INTO rivers
                               (river_name)
                           VALUES (%s)
                           """, (river,))

            river_map[river] = cursor.lastrowid

        river_id = river_map[river]

        # =====================
        # DISTRICT
        # =====================

        district_key = (river_id, district)

        if district_key not in district_map:

            cursor.execute("""
                INSERT INTO districts
                (
                    river_id,
                    district_name)
                VALUES (%s,%s)
            """, (
                river_id,
                district
            ))

            district_map[district_key] = cursor.lastrowid

        district_id = district_map[district_key]

        # =====================
        # DRAIN MASTER
        # =====================

        cursor.execute("""
            INSERT INTO drain_master
            (
                district_id,
                total_drains,
                total_discharge,
                scrape_time
            )
            VALUES (%s,%s,%s,%s)
        """, (
                           district_id,
                           int(float(row["TotalDrains"])),
                           float(row["TotalDischargeMLD"]),
                           scrape_time
        ))

        drain_id = cursor.lastrowid

        # =====================
        # TAPPED
        # =====================

        cursor.execute("""
            INSERT INTO tapped_drains
            (
                drain_id,
                tapped_drains,
                tapped_discharge
            )
            VALUES (%s,%s,%s)
        """, (
            drain_id,
            int(float(row["TappedDrains"])),
            float(row["TappedDischargeMLD"])
        ))

        # =====================
        # UNTAPPED
        # =====================

        cursor.execute("""
            INSERT INTO untapped_drains
            (
                drain_id,
                untapped_drains,
                untapped_discharge
            )
            VALUES (%s,%s,%s)
        """, (
            drain_id,
            int(float(row["UntappedDrains"])),
            float(row["UntappedDischargeMLD"])
        ))

        # =====================
        # PARTIAL
        # =====================

        cursor.execute("""
            INSERT INTO partial_tapped_drains
            (
                drain_id,
                partial_tapped_drains,
                partial_tapped_discharge
            )
            VALUES (%s,%s,%s)
        """, (
            drain_id,
            int(float(row["PartialTappedDrains"])),
            float(row["PartialTappedDischargeMLD"])
        ))

        # =====================
        # NOT TO BE TAPPED
        # =====================

        cursor.execute("""
            INSERT INTO not_to_be_tapped_drains
            (
                drain_id,
                not_to_be_tapped_drains,
                not_to_be_tapped_discharge
            )
            VALUES (%s,%s,%s)
        """, (
            drain_id,
            int(float(row["NotToBeTappedDrains"])),
            float(row["NotToBeTappedDischargeMLD"])
        ))

    conn.commit()

    print(f"Loaded {len(df)} rows")
def backup_current_to_audit():

    clear_audit()
    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.rivers
                   SELECT *
                   FROM River_Wise_Drains.rivers
                   """)

    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.districts
                   SELECT *
                   FROM River_Wise_Drains.districts
                   """)

    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.drain_master
                   SELECT *
                   FROM River_Wise_Drains.drain_master
                   """)

    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.tapped_drains
                   SELECT *
                   FROM River_Wise_Drains.tapped_drains
                   """)

    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.untapped_drains
                   SELECT *
                   FROM River_Wise_Drains.untapped_drains
                   """)

    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.partial_tapped_drains
                   SELECT *
                   FROM River_Wise_Drains.partial_tapped_drains
                   """)

    cursor.execute("""
                   INSERT INTO River_Wise_Drains_Audit.not_to_be_tapped_drains
                   SELECT *
                   FROM River_Wise_Drains.not_to_be_tapped_drains
                   """)

    print("Current copied to Audit")
if __name__ == "__main__":

    while True:

        try:

            conn.ping(reconnect=True)

            print("\n===== STARTED =====")

            generate_csv_from_html()

            # =========================
            # CHECK AUDIT DB
            # =========================

            cursor.execute("""
                SELECT COUNT(*)
                FROM River_Wise_Drains_Audit.rivers
            """)

            audit_count = cursor.fetchone()[0]

            # =========================
            # FIRST RUN
            # =========================

            if audit_count == 0:

                print("FIRST CYCLE")

                clear_current()

                load_csv()

                backup_current_to_audit()

            # =========================
            # NORMAL RUN
            # =========================

            else:

                print("NORMAL CYCLE")

                backup_current_to_audit()

                clear_current()

                load_csv()

            # =========================
            # VERIFY CURRENT DB
            # =========================

            cursor.execute("""
                SELECT river_name
                FROM River_Wise_Drains.rivers
                ORDER BY river_id
                LIMIT 1
            """)

            print(
                "CURRENT FIRST RIVER =",
                cursor.fetchone()
            )

            cursor.execute("""
                SELECT district_name
                FROM River_Wise_Drains.districts
                ORDER BY district_id
                LIMIT 1
            """)

            print(
                "CURRENT FIRST DISTRICT =",
                cursor.fetchone()
            )

            # =========================
            # VERIFY AUDIT DB
            # =========================

            cursor.execute("""
                SELECT river_name
                FROM River_Wise_Drains_Audit.rivers
                ORDER BY river_id
                LIMIT 1
            """)

            print(
                "AUDIT FIRST RIVER =",
                cursor.fetchone()
            )

            cursor.execute("""
                SELECT district_name
                FROM River_Wise_Drains_Audit.districts
                ORDER BY district_id
                LIMIT 1
            """)

            print(
                "AUDIT FIRST DISTRICT =",
                cursor.fetchone()
            )

            # =========================
            # COUNT CHECK
            # =========================

            cursor.execute("""
                SELECT COUNT(*)
                FROM River_Wise_Drains.drain_master
            """)

            print(
                "CURRENT DRAIN COUNT =",
                cursor.fetchone()[0]
            )

            cursor.execute("""
                SELECT COUNT(*)
                FROM River_Wise_Drains_Audit.drain_master
            """)

            print(
                "AUDIT DRAIN COUNT =",
                cursor.fetchone()[0]
            )

            print("\nWaiting 10 seconds...\n")

            time.sleep(10)

        except Exception as e:

            conn.rollback()

            import traceback

            traceback.print_exc()

            print("\nRetrying in 10 seconds...\n")

            time.sleep(10)