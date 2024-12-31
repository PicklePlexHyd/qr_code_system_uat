from flask import Flask, request, render_template, jsonify
from datetime import datetime, timedelta
from models import session, Membership
from qr_utils import generate_qr
import os

app = Flask(__name__)

BASE_URL = os.getenv("BASE_URL", "https://pickplex-app-9f5753935b75.herokuapp.com")

@app.route('/')
def home():
    return render_template("form.html")  # HTML form for input

@app.route('/generate', methods=['POST'])
def generate_membership():
    try:
        # Collect form data
        name = request.form.get("name")
        membership_type = request.form.get("membership_type")
        start_date_str = request.form.get("start_date")  # Start date from the form

        if not name or not membership_type or not start_date_str:
            return jsonify({"error": "Missing required fields"}), 400

        # Parse the start_date
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = start_date + timedelta(days=90)

        # Set entries and perks based on membership type
        entries_left = None
        perks = []
        if membership_type == "Xpress Pass":
            entries_left = 8
            perks = [
                "Carry forward unused slots for up to 15 more days",
            ]
        elif membership_type == "Season Pass":
            entries_left = 24
            perks = [
                "Bring one friend per month at a discounted rate (20%)",
                "Carry forward unused slots for up to 15 more days",
            ]
        elif membership_type == "Membership":
            perks = [
                "20% discount for individual court bookings",
                "1-2 free guest passes per month",
                "Loyalty points for free sessions or paddle rentals",
                "One free session in the member's birthday month",
            ]

        # Add member to the database
        new_member = Membership(
            name=name,
            membership_type=membership_type,
            validity=end_date,
            entries_left=entries_left,
            qr_code=""
        )
        session.add(new_member)
        session.commit()

        # Generate QR Code with the redirection link
        qr_code_dir = os.path.abspath(os.path.join("static", "qr_codes"))
        qr_code_filename = f"{name.replace(' ', '_')}_{membership_type}.png"
        qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
        os.makedirs(qr_code_dir, exist_ok=True)

        qr_link = f"{BASE_URL}/pass/{new_member.id}"
        generate_qr(qr_link, qr_code_path)

        # Update the member with the QR code path
        new_member.qr_code = qr_code_path
        session.commit()

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
        member = session.query(Membership).filter_by(id=membership_id).first()

        if not member:
            return render_template("error.html", message="Invalid Membership")

        # Determine perks based on membership type
        perks = []
        if member.membership_type == "Xpress Pass":
            perks = ["Book upto 8 slots a month.","Carry forward unused slots for up to 15 more days","24 hrs advance booking for weekend"]
        elif member.membership_type == "Season Pass":
            perks = [
                "24 slots for 90 days.",
                "Bring 1 friend per month at a discounted rate (20%)",
                "Carry forward unused slots for up to 15 more days",
                "24 hrs advance booking for weekend"
            ]
        elif member.membership_type == "Membership":
            perks = [
                "20% discount for individual court bookings",
                "2 free guest passes per month",
                "Free Team Listing for Tournaments.",
                "Access to Membership Exclusive Events (Social Mixers, Sundowners, etc.)",
                "Loyalty points for free sessions or paddle rentals",
                "One free session in the member's birthday month",
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
    app.run(host="0.0.0.0", port=5001)