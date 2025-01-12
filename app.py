from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
from models import session as db_session, Membership
from qr_utils import generate_qr
import os


app = Flask(__name__)
app.secret_key = "supersecretkey"  # Replace with a strong secret key
BASE_URL = os.getenv("BASE_URL", "https://pickplex-app-9f5753935b75.herokuapp.com") #

# Dummy admin credentials (can be stored in a secure database or environment variable)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

@app.route('/')
def home():
    return redirect(url_for("login"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("generate_membership"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route('/generate', methods=['GET', 'POST'])
def generate_membership():
    if "admin" not in session:
        return redirect(url_for("login"))  # Redirect if admin is not logged in

    if request.method == 'GET':
        # Render the form without clearing the session
        return render_template("form.html")

    if request.method == 'POST':
        try:
            # Collect form data
            name = request.form.get("name")
            membership_type = request.form.get("membership_type")
            start_date_str = request.form.get("start_date")  # Start date from the form

            if not name or not membership_type or not start_date_str:
                return jsonify({"error": "Missing required fields"}), 400

            # Parse the start date and calculate validity
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=90)

            # Set entries based on membership type
            entries_left = 8 if membership_type == "Xpress Pass" else 24 if membership_type == "Season Pass" else None

            # Add the new member to the database
            new_member = Membership(
                name=name,
                membership_type=membership_type,
                validity=end_date,
                entries_left=entries_left,
                qr_code=""
            )
            db_session.add(new_member)
            db_session.commit()

            print(f"Generated Member ID: {new_member.id}")

            # Generate QR code
            qr_code_dir = os.path.abspath(os.path.join("static", "qr_codes"))
            qr_code_filename = f"{name.replace(' ', '_')}_{membership_type}.png"
            qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
            os.makedirs(qr_code_dir, exist_ok=True)

            qr_link = f"{BASE_URL}/pass/{new_member.id}"
            print(f"QR Link: {qr_link}")
            generate_qr(qr_link, qr_code_path)

            # Update the member with the QR code path
            new_member.qr_code = qr_code_path
            db_session.commit()

            # Clear session after operation
            session.pop("admin", None)

            return render_template(
                "success.html",
                qr_code_url=f"/static/qr_codes/{qr_code_filename}",
                qr_status="QR code generated successfully!"
            )
        except Exception as e:
            print(f"Error generating membership: {e}")
            return "Internal Server Error", 500




@app.route('/pass/<int:membership_id>')
def show_pass(membership_id):
    try:
        # Retrieve the member details
        print(f"Fetching membership with ID: {membership_id}")
        member = db_session.query(Membership).filter_by(id=membership_id).first()
        if not member:
            print(f"No member found with ID: {membership_id}")
            return render_template("error.html", message="Invalid Membership")

        # Determine perks based on membership type
        perks = []
        if member.membership_type == "Xpress Pass":
            perks = ["Book up to 8 slots a month.", "Carry forward unused slots for up to 15 more days.", "24 hrs advance booking for weekend."]
        elif member.membership_type == "Season Pass":
            perks = [
                "24 slots for 90 days.",
                "Bring 1 friend per month at a discounted rate (20%).",
                "Carry forward unused slots for up to 15 more days.",
                "24 hrs advance booking for weekend.",
            ]
        elif member.membership_type == "Membership":
            perks = [
                "20% discount for individual court bookings.",
                "2 free guest passes per month.",
                "Free Team Listing for Tournaments.",
                "Access to Membership Exclusive Events (Social Mixers, Sundowners, etc.).",
                "Loyalty points for free sessions or paddle rentals.",
                "One free session in the member's birthday month.",
            ]

        # Calculate start date from validity (90 days back)
        start_date = member.validity - timedelta(days=90)

        # Render the pass template
        return render_template(
            "pass.html",
            member=member,
            perks=perks,
            start_date=start_date
        )
    except Exception as e:
        print(f"Error displaying pass: {e}")
        return "Internal Server Error", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
