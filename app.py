from flask import Flask, request, render_template, jsonify
from datetime import datetime
from models import session, Membership
from qr_utils import generate_qr
import os
from models import session, Membership, ScanHistory

app = Flask(__name__)

# Route for the home page with a form to generate membership
@app.route('/')
def home():
    return render_template("form.html")  # HTML form for input

# Route to handle QR code generation
@app.route('/generate', methods=['POST'])
def generate_membership():
    try:
        name = request.form.get("name")
        membership_type = request.form.get("membership_type")
        validity = request.form.get("validity")
        entries_left = request.form.get("entries_left", None)

        if not name or not membership_type or not validity:
            return jsonify({"error": "Missing required fields"}), 400

        # Add member to the database
        new_member = Membership(
            name=name,
            membership_type=membership_type,
            validity=datetime.strptime(validity, "%Y-%m-%d").date(),
            entries_left=int(entries_left) if entries_left else None,
            qr_code=""
        )
        session.add(new_member)
        session.commit()

        # Generate a QR code containing the redirection link
        qr_code_dir = os.path.abspath(os.path.join("static", "qr_codes"))
        qr_code_filename = f"{name.replace(' ', '_')}_{membership_type}.png"
        qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
        os.makedirs(qr_code_dir, exist_ok=True)

        # The link to redirect to the pass page
        qr_link = f"http://127.0.0.1:5001/pass/{new_member.id}"
        generate_qr(qr_link, qr_code_path)

        # Update member with the generated QR code path
        new_member.qr_code = qr_code_path
        session.commit()

        return render_template(
            "success.html",
            qr_code_url=f"/static/qr_codes/{qr_code_filename}",
            qr_status="QR code generated successfully!"
        )
    except Exception as e:
        print(f"Unhandled Error: {e}")
        return "Internal Server Error", 500


# Route to scan and validate QR codes
@app.route('/scan', methods=['POST'])
def scan_qr():
    try:
        # Decode the QR code data
        qr_code_data = request.json.get("qr_code_data")
        name = qr_code_data.get("name")

        # Retrieve the member details from the database
        member = session.query(Membership).filter_by(name=name).first()

        if not member:
            return render_template("error.html", message="Invalid QR Code")

        # Validate membership expiration
        today = datetime.today().date()
        if today > member.validity:
            return render_template("error.html", message="Membership has expired")

        # Handle passes with limited entries
        if member.membership_type in ["Xpress Pass", "Season Pass"]:
            if member.entries_left is not None and member.entries_left <= 0:
                return render_template("error.html", message="No entries left")
            # Deduct one entry
            member.entries_left -= 1

        # Save scan to history
        scan_entry = ScanHistory(membership_id=member.id)
        session.add(scan_entry)
        session.commit()

        # Render the pass template
        return render_template("pass.html", member=member)

    except Exception as e:
        print(f"Error processing QR scan: {e}")
        return "Internal Server Error", 500
    
@app.route('/pass/<int:membership_id>')
def show_pass(membership_id):
    try:
        # Retrieve the member details
        member = session.query(Membership).filter_by(id=membership_id).first()

        if not member:
            return render_template("error.html", message="Invalid Membership")

        # Render the pass template
        return render_template("pass.html", member=member)
    except Exception as e:
        print(f"Error displaying pass: {e}")
        return "Internal Server Error", 500

    
if __name__ == "__main__":
    from os import environ
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 5001)), debug=True)
