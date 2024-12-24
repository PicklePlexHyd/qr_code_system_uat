from flask import Flask, request, render_template, jsonify
from datetime import datetime
from models import session, Membership
from qr_utils import generate_qr

app = Flask(__name__)

@app.route('/')
def home():
    return "QR Code Membership System"

@app.route('/generate', methods=['POST'])
def generate_membership():
    data = request.json
    name = data.get("name")
    membership_type = data.get("membership_type")
    validity = datetime.strptime(data.get("validity"), "%Y-%m-%d").date()
    entries_left = data.get("entries_left", None)
    
    # Generate QR code
    qr_data = {
        "name": name,
        "membership_type": membership_type,
        "validity": str(validity),
        "entries_left": entries_left
    }
    qr_code_filename = f"{name.replace(' ', '_')}_{membership_type}.png"
    qr_path = generate_qr(str(qr_data), qr_code_filename)
    
    # Save to DB
    new_member = Membership(
        name=name,
        membership_type=membership_type,
        validity=validity,
        entries_left=entries_left,
        qr_code=qr_path
    )
    session.add(new_member)
    session.commit()
    return jsonify({"message": "Membership created", "qr_code": qr_path})

@app.route('/scan', methods=['POST'])
def scan_qr():
    qr_code_data = request.json.get("qr_code_data")
    member = session.query(Membership).filter_by(name=qr_code_data["name"]).first()
    
    if not member:
        return render_template("error.html", message="Invalid QR Code")
    
    today = datetime.today().date()
    if today > member.validity:
        return render_template("error.html", message="Membership has expired")
    
    if member.membership_type in ["Xpress Pass", "Season Pass"]:
        if member.entries_left <= 0:
            return render_template("error.html", message="No entries left")
        member.entries_left -= 1
        session.commit()
    
    return render_template("member_info.html", member=member)

if __name__ == "__main__":
    from os import environ
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))