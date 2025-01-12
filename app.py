from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
from models import session as db_session, Membership
from qr_utils import generate_qr
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
BASE_URL = os.getenv("BASE_URL", "https://pickplex-app-9f5753935b75.herokuapp.com")

# Dummy admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

@app.route('/')
def home():
    return redirect(url_for("login"))

# Admin login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

# Admin dashboard to choose functionality
@app.route('/admin/dashboard')
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

# Membership generation route (admin only)
@app.route('/generate', methods=['GET', 'POST'])
def generate_membership():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == 'GET':
        return render_template("form.html")

    if request.method == 'POST':
        try:
            name = request.form.get("name")
            membership_type = request.form.get("membership_type")
            start_date_str = request.form.get("start_date")

            if not name or not membership_type or not start_date_str:
                return jsonify({"error": "Missing required fields"}), 400

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=90)

            entries_left = 8 if membership_type == "Xpress Pass" else 24 if membership_type == "Season Pass" else None

            new_member = Membership(
                name=name,
                membership_type=membership_type,
                validity=end_date,
                entries_left=entries_left,
                qr_code=""
            )
            db_session.add(new_member)
            db_session.commit()

            qr_code_dir = os.path.abspath(os.path.join("static", "qr_codes"))
            qr_code_filename = f"{name.replace(' ', '_')}_{membership_type}.png"
            qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
            os.makedirs(qr_code_dir, exist_ok=True)

            qr_link = f"{BASE_URL}/pass/{new_member.id}"
            generate_qr(qr_link, qr_code_path)

            new_member.qr_code = qr_code_path
            db_session.commit()

            return render_template(
                "success.html",
                qr_code_url=f"/static/qr_codes/{qr_code_filename}",
                qr_status="QR code generated successfully!"
            )
        except Exception as e:
            print(f"Error generating membership: {e}")
            return "Internal Server Error", 500

# Admin route to scan and expire entries
@app.route('/admin/scan', methods=['GET', 'POST'])
def admin_scan():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':
        member_name = request.form.get("member_name")
        print(f"Received Member Name: {member_name}")
        try:
            # Case-insensitive query
            member = db_session.query(Membership).filter(Membership.name.ilike(member_name)).first()
            print(f"Queried Member: {member}")

            if not member:
                print("No member found with the provided name.")
                return render_template("error.html", message="Invalid Member Name")

            # Handle Xpress Pass and Season Pass logic
            if member.membership_type in ["Xpress Pass", "Season Pass"]:
                if member.entries_left > 0:
                    member.entries_left -= 1
                    db_session.commit()
                    print(f"Updated Entries Left: {member.entries_left}")
                    return render_template(
                        "scan_success.html",
                        member=member,
                        message="Entry successfully expired!"
                    )
                else:
                    print("No entries left for the member.")
                    return render_template("error.html", message="No entries left!")
            return render_template("scan_success.html", member=member, message="Membership scanned successfully!")
        except Exception as e:
            print(f"Error during scan: {e}")
            return render_template("error.html", message="Error during scan!")

    return render_template("admin_scan.html")



# Public route to display membership pass
@app.route('/pass/<int:membership_id>')
def show_pass(membership_id):
    try:
        member = db_session.query(Membership).filter_by(id=membership_id).first()
        if not member:
            return render_template("error.html", message="Invalid Membership")

        perks = []
        if member.membership_type == "Xpress Pass":
            perks = ["Book up to 8 slots a month.", "Carry forward unused slots for up to 15 more days."]
        elif member.membership_type == "Season Pass":
            perks = [
                "24 slots for 90 days.",
                "Bring 1 friend per month at a discounted rate (20%).",
                "Carry forward unused slots for up to 15 more days."
            ]
        elif member.membership_type == "Membership":
            perks = [
                "20% discount for individual court bookings.",
                "2 free guest passes per month.",
                "Loyalty points for free sessions or paddle rentals.",
                "One free session in the member's birthday month."
            ]

        start_date = member.validity - timedelta(days=90)
        return render_template("pass.html", member=member, perks=perks, start_date=start_date)
    except Exception as e:
        print(f"Error displaying pass: {e}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
