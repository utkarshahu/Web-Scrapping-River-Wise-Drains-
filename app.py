from flask import Flask, jsonify, render_template
import mysql.connector
import subprocess
import sys
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

MAIN_DB_NAME = os.getenv("MAIN_DB_NAME")
AUDIT_DB_NAME = os.getenv("AUDIT_DB_NAME")

app = Flask(__name__)


# ==========================
# MAIN DB
# ==========================

def get_main_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=MAIN_DB_NAME
    )


# ==========================
# AUDIT DB
# ==========================

def get_audit_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=AUDIT_DB_NAME
    )


# ==========================
# HOME
# ==========================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================
# PYTHON TEST
# ==========================

@app.route("/test-python")
def test_python():
    return sys.executable


# ==========================
# MANUAL REFRESH
# ==========================

@app.route("/api/fetch-now", methods=["POST"])
def fetch_now():

    try:

        result = subprocess.run(
            [
                r"C:\Users\utkar\PyCharmMiscProject\.venv\Scripts\python.exe",
                r"A:\River Wise Drains\manual_refresh.py"
            ],
            capture_output=True,
            text=True
        )

        print("RETURN CODE =", result.returncode)
        print("STDOUT =", result.stdout)
        print("STDERR =", result.stderr)

        if result.returncode != 0:
            return jsonify({
                "success": False,
                "message": result.stderr
            }), 500

        return jsonify({
            "success": True,
            "message": "Data Updated Successfully"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500




# ==========================
# CURRENT DATA
# ==========================

@app.route("/api/current")
def current_data():

    conn = get_main_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            r.river_name,
            d.district_name,

            dm.total_drains,
            dm.total_discharge,

            td.tapped_drains,
            td.tapped_discharge,

            ud.untapped_drains,
            ud.untapped_discharge,

            pt.partial_tapped_drains,
            pt.partial_tapped_discharge,

            nt.not_to_be_tapped_drains,
            nt.not_to_be_tapped_discharge,

            dm.scrape_time

        FROM rivers r

        JOIN districts d
            ON r.river_id = d.river_id

        JOIN drain_master dm
            ON d.district_id = dm.district_id

        LEFT JOIN tapped_drains td
            ON dm.drain_id = td.drain_id

        LEFT JOIN untapped_drains ud
            ON dm.drain_id = ud.drain_id

        LEFT JOIN partial_tapped_drains pt
            ON dm.drain_id = pt.drain_id

        LEFT JOIN not_to_be_tapped_drains nt
            ON dm.drain_id = nt.drain_id

        ORDER BY
            r.river_name,
            d.district_name
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ==========================
# AUDIT DATA
# ==========================

@app.route("/api/audit")
def audit_data():

    conn = get_audit_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            r.river_name,
            d.district_name,

            dm.total_drains,
            dm.total_discharge,

            td.tapped_drains,
            td.tapped_discharge,

            ud.untapped_drains,
            ud.untapped_discharge,

            pt.partial_tapped_drains,
            pt.partial_tapped_discharge,

            nt.not_to_be_tapped_drains,
            nt.not_to_be_tapped_discharge,

            dm.scrape_time

        FROM rivers r

        JOIN districts d
            ON r.river_id = d.river_id

        JOIN drain_master dm
            ON d.district_id = dm.district_id

        LEFT JOIN tapped_drains td
            ON dm.drain_id = td.drain_id

        LEFT JOIN untapped_drains ud
            ON dm.drain_id = ud.drain_id

        LEFT JOIN partial_tapped_drains pt
            ON dm.drain_id = pt.drain_id

        LEFT JOIN not_to_be_tapped_drains nt
            ON dm.drain_id = nt.drain_id

        ORDER BY
            r.river_name,
            d.district_name
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ==========================
# RUN APP
# ==========================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )