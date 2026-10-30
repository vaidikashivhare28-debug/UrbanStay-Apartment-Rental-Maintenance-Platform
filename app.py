from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = "replace_this_with_a_random_secret_key"  # needed for session/login

# ---------------------------------------------
# DATABASE CONNECTION
# Update these values to match your local MySQL setup
# ---------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",   # <-- change this
    "database": "urbanstay"
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None


# ---------------------------------------------
# HOME PAGE (public landing page)
# ---------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------------------------------------
# LOGIN (User Management module)
# ---------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")  # owner / tenant / staff

        conn = get_db_connection()
        if not conn:
            flash("Could not connect to database.")
            return render_template("login.html")

        cursor = conn.cursor(dictionary=True)

        # Table name matches the role selected
        table_map = {"owner": "owner", "tenant": "tenant", "staff": "staff"}
        table = table_map.get(role)

        if not table:
            flash("Invalid role selected.")
            cursor.close()
            conn.close()
            return render_template("login.html")

        cursor.execute(f"SELECT * FROM {table} WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user[f"{role}_id"]
            session["role"] = role
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------
# DASHBOARD (pulls summary numbers for Reports & Analytics)
# ---------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM unit")
    total_units = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM unit WHERE status = 'Occupied'")
    occupied_units = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM maintenance_request WHERE status != 'Resolved'")
    pending_maintenance = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM payment WHERE status = 'Overdue'")
    overdue_payments = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_units=total_units,
        occupied_units=occupied_units,
        pending_maintenance=pending_maintenance,
        overdue_payments=overdue_payments
    )


# ---------------------------------------------
# UNITS - Data Management module (CRUD example)
# ---------------------------------------------
@app.route("/units")
def units():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT unit.unit_id, unit.unit_number, unit.bedrooms,
               unit.rent_amount, unit.status, building.name AS building_name
        FROM unit
        JOIN building ON unit.building_id = building.building_id
    """)
    all_units = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("units.html", units=all_units)


@app.route("/units/add", methods=["GET", "POST"])
def add_unit():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        building_id = request.form.get("building_id")
        unit_number = request.form.get("unit_number")
        bedrooms = request.form.get("bedrooms")
        rent_amount = request.form.get("rent_amount")

        try:
            cursor.execute(
                """INSERT INTO unit (building_id, unit_number, bedrooms, rent_amount, status)
                   VALUES (%s, %s, %s, %s, 'Vacant')""",
                (building_id, unit_number, bedrooms, rent_amount)
            )
            conn.commit()
            flash("Unit added successfully.")
            cursor.close()
            conn.close()
            return redirect(url_for("units"))
        except Error as e:
            flash(f"Error adding unit: {e}")

    cursor.execute("SELECT building_id, name FROM building")
    buildings = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("add_unit.html", buildings=buildings)


@app.route("/units/delete/<int:unit_id>")
def delete_unit(unit_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM unit WHERE unit_id = %s", (unit_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Unit deleted.")
    return redirect(url_for("units"))


# ---------------------------------------------
# TENANTS - Data Management module
# ---------------------------------------------
@app.route("/tenants")
def tenants():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tenant")
    all_tenants = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("tenants.html", tenants=all_tenants)


@app.route("/tenants/add", methods=["GET", "POST"])
def add_tenant():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        try:
            cursor.execute(
                "INSERT INTO tenant (name, email, phone, password) VALUES (%s, %s, %s, %s)",
                (name, email, phone, password)
            )
            conn.commit()
            flash("Tenant added successfully.")
        except Error as e:
            flash(f"Error adding tenant: {e}")
        cursor.close()
        conn.close()
        return redirect(url_for("tenants"))
    cursor.close()
    conn.close()
    return render_template("add_tenant.html")


# ---------------------------------------------
# LEASES - Data Management module
# ---------------------------------------------
@app.route("/leases")
def leases():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT lease.lease_id, tenant.name AS tenant_name, unit.unit_number,
               lease.start_date, lease.end_date, lease.rent_amount, lease.deposit
        FROM lease
        JOIN tenant ON lease.tenant_id = tenant.tenant_id
        JOIN unit ON lease.unit_id = unit.unit_id
    """)
    all_leases = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("leases.html", leases=all_leases)


@app.route("/leases/add", methods=["GET", "POST"])
def add_lease():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        unit_id = request.form.get("unit_id")
        tenant_id = request.form.get("tenant_id")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        rent_amount = request.form.get("rent_amount")
        deposit = request.form.get("deposit")
        try:
            cursor.execute(
                """INSERT INTO lease (unit_id, tenant_id, start_date, end_date, rent_amount, deposit)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (unit_id, tenant_id, start_date, end_date, rent_amount, deposit)
            )
            # Mark the unit as occupied once a lease is created
            cursor.execute("UPDATE unit SET status = 'Occupied' WHERE unit_id = %s", (unit_id,))
            conn.commit()
            flash("Lease created successfully.")
        except Error as e:
            # This will trigger if end_date <= start_date (CHECK constraint) or other DB errors
            flash(f"Error creating lease: {e}")
        cursor.close()
        conn.close()
        return redirect(url_for("leases"))

    cursor.execute("SELECT unit_id, unit_number FROM unit WHERE status = 'Vacant'")
    units_list = cursor.fetchall()
    cursor.execute("SELECT tenant_id, name FROM tenant")
    tenants_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("add_lease.html", units=units_list, tenants=tenants_list)


# ---------------------------------------------
# PAYMENTS - Data Management module
# ---------------------------------------------
@app.route("/payments")
def payments():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT payment.payment_id, tenant.name AS tenant_name, unit.unit_number,
               payment.payment_date, payment.amount, payment.status
        FROM payment
        JOIN lease ON payment.lease_id = lease.lease_id
        JOIN tenant ON lease.tenant_id = tenant.tenant_id
        JOIN unit ON lease.unit_id = unit.unit_id
        ORDER BY payment.payment_date DESC
    """)
    all_payments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("payments.html", payments=all_payments)


@app.route("/payments/add", methods=["GET", "POST"])
def add_payment():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        lease_id = request.form.get("lease_id")
        payment_date = request.form.get("payment_date")
        amount = request.form.get("amount")
        status = request.form.get("status")
        try:
            cursor.execute(
                "INSERT INTO payment (lease_id, payment_date, amount, status) VALUES (%s, %s, %s, %s)",
                (lease_id, payment_date, amount, status)
            )
            conn.commit()
            flash("Payment recorded successfully.")
        except Error as e:
            flash(f"Error recording payment: {e}")
        cursor.close()
        conn.close()
        return redirect(url_for("payments"))

    cursor.execute("""
        SELECT lease.lease_id, tenant.name AS tenant_name, unit.unit_number
        FROM lease
        JOIN tenant ON lease.tenant_id = tenant.tenant_id
        JOIN unit ON lease.unit_id = unit.unit_id
    """)
    leases_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("add_payment.html", leases=leases_list)


# ---------------------------------------------
# MAINTENANCE REQUESTS - Data Management module
# ---------------------------------------------
@app.route("/maintenance")
def maintenance():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT maintenance_request.request_id, tenant.name AS tenant_name, unit.unit_number,
               maintenance_request.issue_type, maintenance_request.status,
               maintenance_request.reported_date, staff.name AS staff_name
        FROM maintenance_request
        JOIN tenant ON maintenance_request.tenant_id = tenant.tenant_id
        JOIN unit ON maintenance_request.unit_id = unit.unit_id
        LEFT JOIN staff ON maintenance_request.staff_id = staff.staff_id
        ORDER BY maintenance_request.reported_date DESC
    """)
    all_requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("maintenance.html", requests=all_requests)


@app.route("/maintenance/add", methods=["GET", "POST"])
def add_maintenance():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        unit_id = request.form.get("unit_id")
        tenant_id = request.form.get("tenant_id")
        issue_type = request.form.get("issue_type")
        reported_date = request.form.get("reported_date")
        try:
            cursor.execute(
                """INSERT INTO maintenance_request (unit_id, tenant_id, issue_type, status, reported_date)
                   VALUES (%s, %s, %s, 'Pending', %s)""",
                (unit_id, tenant_id, issue_type, reported_date)
            )
            conn.commit()
            flash("Maintenance request logged. (Notifications module would alert staff here.)")
        except Error as e:
            flash(f"Error logging request: {e}")
        cursor.close()
        conn.close()
        return redirect(url_for("maintenance"))

    cursor.execute("SELECT unit_id, unit_number FROM unit")
    units_list = cursor.fetchall()
    cursor.execute("SELECT tenant_id, name FROM tenant")
    tenants_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("add_maintenance.html", units=units_list, tenants=tenants_list)


@app.route("/maintenance/update/<int:request_id>", methods=["POST"])
def update_maintenance(request_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    new_status = request.form.get("status")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE maintenance_request SET status = %s WHERE request_id = %s", (new_status, request_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f"Request status updated to {new_status}. (Notifications module would alert tenant here.)")
    return redirect(url_for("maintenance"))


# ---------------------------------------------
# REPORTS & ANALYTICS module
# ---------------------------------------------
@app.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT building.name AS building, unit.unit_number, unit.status
        FROM unit JOIN building ON unit.building_id = building.building_id
    """)
    occupancy = cursor.fetchall()

    cursor.execute("""
        SELECT tenant.name, payment.amount, payment.payment_date, payment.status
        FROM payment
        JOIN lease ON payment.lease_id = lease.lease_id
        JOIN tenant ON lease.tenant_id = tenant.tenant_id
        WHERE payment.status = 'Overdue'
    """)
    overdue = cursor.fetchall()

    cursor.execute("""
        SELECT building.name,
               COUNT(unit.unit_id) AS total_units,
               SUM(CASE WHEN unit.status = 'Occupied' THEN 1 ELSE 0 END) AS occupied_units
        FROM unit JOIN building ON unit.building_id = building.building_id
        GROUP BY building.name
    """)
    occupancy_rate = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("reports.html", occupancy=occupancy, overdue=overdue, occupancy_rate=occupancy_rate)


# ---------------------------------------------
# SETTINGS - Admin/Settings module (Amenities + Staff)
# ---------------------------------------------
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        amenity_name = request.form.get("amenity_name")
        if amenity_name:
            try:
                cursor.execute("INSERT INTO amenity (name) VALUES (%s)", (amenity_name,))
                conn.commit()
                flash("Amenity added.")
            except Error as e:
                flash(f"Error: {e}")

    cursor.execute("SELECT * FROM amenity")
    amenities = cursor.fetchall()
    cursor.execute("SELECT * FROM staff")
    staff_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("settings.html", amenities=amenities, staff=staff_list)


if __name__ == "__main__":
    app.run(debug=True)
