import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from flask import Flask, request, render_template, redirect, url_for, session, flash
from datetime import datetime, timedelta
from models import session as db_session, Membership
from qr_utils import generate_qr
import os
import secrets
import string
import json
import base64
from flask import render_template, make_response
from openpyxl import Workbook, load_workbook
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from sqlalchemy import create_engine


app = Flask(__name__)
app.secret_key = "supersecretkey"
BASE_URL = os.getenv("BASE_URL", "https://your-heroku-app.herokuapp.com")
#BASE_URL = "http://127.0.0.1:5000"


# Admin credentials
ADMIN_USERNAME = "PicklePlexAdmin"
ADMIN_PASSWORD = "PlexAdmin@123"

# Email credentials
EMAIL_ADDRESS = "pickleplexhyd@gmail.com"  # Update with your email
EMAIL_PASSWORD = "enpt akwm mliz gfte"  # Use app password

#GOOGLE_SHEET_CREDENTIALS = "/Users/rajkumardandu/Downloads/pickleplex-449610-5b6f84d4afda.json"

# Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEET_CREDENTIALS, scope)
#client = gspread.authorize(creds)

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_SHEET_CREDENTIALS")

if GOOGLE_CREDENTIALS_JSON:
    decoded_creds = base64.b64decode(GOOGLE_CREDENTIALS_JSON).decode("utf-8")
    creds_json = json.loads(decoded_creds)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
else:
    raise ValueError("Google credentials not found in environment variables")

# Open the Google Sheet (replace with your sheet name)
SHEET_NAME = "PicklePlex Data"
spreadsheet = client.open(SHEET_NAME)

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///membership.db')  # Use SQLite locally, PostgreSQL on Heroku

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)  # Heroku fix

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL




#Adding Membership Data to Excel Sheet 
def add_membership_to_google_sheets(member):
    try:
        sheet = spreadsheet.worksheet("Memberships")
    except:
        sheet = spreadsheet.add_worksheet(title="Memberships", rows="10000", cols="8")
        sheet.append_row(["Membership ID", "Name", "Email", "Membership Type", "Start Date", "End Date", "Entries Left", "Created At"])

    start_date = member.validity - timedelta(days=30)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([member.id, member.name, member.email, member.membership_type, str(start_date), str(member.validity), member.entries_left, created_at])

#Adding Scan Data to Excel Sheet
def add_scan_to_google_sheets(member):
    try:
        sheet = spreadsheet.worksheet("Scans")
    except:
        sheet = spreadsheet.add_worksheet(title="Scans", rows="1000", cols="6")
        sheet.append_row(["Membership ID", "Name", "Email", "Membership Type", "Scan Date", "Entries Left","Last Scan Date"])

    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([member.id, member.name, member.email, member.membership_type, scan_date, member.entries_left, scan_date])

def update_entries_left_in_membership_sheet(member):
    try:
        sheet = spreadsheet.worksheet("Memberships")  # Get Memberships sheet
        records = sheet.get_all_records()  # Fetch all records as a list of dictionaries

        for index, record in enumerate(records, start=2):  # Start from row 2 (1st row is headers)
            if record["Membership ID"] == member.id:
                sheet.update_cell(index, 7, member.entries_left)  # Column 7 = Entries Left
                break  # Stop after updating the correct record

    except Exception as e:
        print(f"Error updating Google Sheets: {e}")

# Function to send email
def send_email(to_email, subject, body, qr_path=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = formataddr(("Pickleplex", EMAIL_ADDRESS))
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        # Attach QR code if available
        if qr_path:
            with open(qr_path, 'rb') as f:
                qr_image = MIMEImage(f.read(), name=os.path.basename(qr_path))
                msg.attach(qr_image)

        # Connect to SMTP server and send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

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

@app.route('/admin/dashboard')
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

def generate_unique_id(length=6):
    """Generate a unique ID with the given length."""
    alphabet = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@app.route('/generate', methods=['GET', 'POST'])
def generate_membership():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == 'GET':
        return render_template("form.html")

    if request.method == 'POST':
        try:
            name = request.form.get("name")
            email = request.form.get("email")
            membership_type = request.form.get("membership_type")
            start_date_str = request.form.get("start_date")

            if not name or not email or not membership_type or not start_date_str:
                flash("All fields are required!", "error")
                return redirect(url_for("generate_membership"))

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=30)
            membership_id = generate_unique_id()

            if membership_type == "Morning Pass":
                entries_left = 30
                perks = [
                    "Free 1-hour slot daily (7 AM - 11 AM), including weekends!",
                    "Paddles included!"
                ]
            elif membership_type == "Xpress Pass":
                entries_left = 8
                perks = [
                    "4 hours (8 slots) per month.",
                    "Carry forward unused slots for up to 15 days if the pass is still valid.",
                    "Redeem up to 2 slots per day!"
                ]
            elif membership_type == "Xpress Plus Pass":
                entries_left = 16
                perks = [
                    "8 hours (16 slots) per month.",
                    "Carry forward unused slots for up to 15 days if the pass is still valid.",
                    "Redeem up to 4 slots per day!"
                ]
            else:
                entries_left = None
                perks = []

            new_member = Membership(
                id=membership_id,
                name=name,
                email=email,
                membership_type=membership_type,
                validity=end_date,
                entries_left=entries_left,
                qr_code=""
            )
            db_session.add(new_member)
            db_session.commit()

            add_membership_to_google_sheets(new_member)

            qr_code_dir = os.path.abspath(os.path.join("static", "qr_codes"))
            qr_code_filename = f"{name.replace(' ', '_')}_{membership_type}.png"
            qr_code_path = os.path.join(qr_code_dir, qr_code_filename)
            os.makedirs(qr_code_dir, exist_ok=True)

            qr_link = f"{BASE_URL}/pass/{new_member.id}"
            #qr_link = f"pass/{new_member.id}"
            generate_qr(qr_link, qr_code_path)

            new_member.qr_code = qr_code_path
            db_session.commit()

            subject = "Your Pickleplex Membership Details"
            body = f"""
            <h2>Welcome to Pickleplex, {name}!</h2>
            <p>Your Membership Id: <strong>{membership_id}</strong> </p>
            <p>Thank you for purchasing the <strong>{membership_type}</strong>.</p>
            <p><strong>Validity:</strong> {start_date} to {end_date}</p>
            <p><strong>Entries Left:</strong> {entries_left}</p>
            <h3>Perks:</h3>
            <ul>
                {''.join(f'<li>{perk}</li>' for perk in perks)}
            </ul>
            <p>You can access your membership pass <a href="{qr_link}">here</a>.</p>
            """
            send_email(email, subject, body, qr_path=qr_code_path)

            return render_template(
                "success.html",
                qr_code_url=f"/static/qr_codes/{qr_code_filename}",
                qr_status="QR code generated and email sent successfully!",
                
            )
        except Exception as e:
            print(f"Error generating membership: {e}")
            flash("Something went wrong. Please try again later.", "error")
            return redirect(url_for("generate_membership"))



@app.route('/admin/scan', methods=['GET', 'POST'])
def admin_scan():
    if "admin" not in session:
        return redirect(url_for("login"))

    member = None  

    if request.method == 'POST':
        membership_id = request.form.get("membership_id")
        print(f"Received Membership ID: {membership_id}")
        try:
            # Case-insensitive query
            member = db_session.query(Membership).filter_by(id=membership_id).first()
            print(f"Queried Member: {member}")

            if not member:
                print("No member found with the provided name.")
                return render_template("error.html", message="Invalid Membership Id")

            # Handle Xpress Pass and Season Pass logic
            # Handle logic for each membership type
            if member.membership_type in ["Morning Pass", "Xpress Pass", "Xpress Plus Pass"]:
                if member.entries_left > 0:
                    member.entries_left -= 1
                    db_session.commit()
                    add_scan_to_google_sheets(member)
                    update_entries_left_in_membership_sheet(member)
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

    return render_template("admin_scan.html", member=member)

@app.route('f"{BASE_URL}/pass/<string:membership_id>',methods=['GET', 'POST'])
def show_pass(membership_id):
    print(f"Accessing pass for Membership ID: {membership_id}")
    try:
        member = db_session.query(Membership).filter_by(id=membership_id).first()
        if not member:
            return render_template("error.html", message="Invalid Membership")

        perks = []
        if member.membership_type == "Morning Pass":
            perks = [
                "Free 1-hour slot daily (7 AM - 11 AM), including weekends!",
                "Paddles included!"
            ]
        elif member.membership_type == "Xpress Pass":
            perks = [
                "4 hours (8 slots) per month.",
                "Carry forward unused slots for up to 15 days if the pass is still valid.",
                "Redeem up to 2 slots per day!"
            ]
        elif member.membership_type == "Xpress Plus Pass":
            perks = [
                "8 hours (16 slots) per month.",
                "Carry forward unused slots for up to 15 days if the pass is still valid.",
                "Redeem up to 4 slots per day!"
            ]

        start_date = member.validity - timedelta(days=30)
        return render_template("pass.html", member=member, perks=perks, start_date=start_date)
    except Exception as e:
        print(f"Error displaying pass: {e}")
        return "Internal Server Error", 500

@app.route('/admin/expire_entries', methods=['GET', 'POST'])
def expire_entries():
    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':
        membership_id = request.form.get("membership_id")
        expire_entries = request.form.get("expire_entries")

        if not membership_id or not expire_entries.isdigit():
            return render_template("error.html", message="Invalid input. Please try again.")

        expire_entries = int(expire_entries)

        try:
            member = db_session.query(Membership).filter_by(id=membership_id).first()

            if not member:
                return render_template("error.html", message="Invalid Membership ID.")

            if expire_entries <= 0:
                return render_template("error.html", message="Expiration value must be greater than 0.")

            if member.entries_left >= expire_entries:
                member.entries_left -= expire_entries
                db_session.commit()
                
                # Update Google Sheets
                add_scan_to_google_sheets(member)
                update_entries_left_in_membership_sheet(member)

                return render_template(
                    "scan_success.html",
                    member=member,
                    message=f"Successfully expired {expire_entries} entries!"
                )
            else:
                return render_template("error.html", message="Not enough entries left to expire.")

        except Exception as e:
            print(f"Error during expiration: {e}")
            return render_template("error.html", message="Error processing expiration!")

    return render_template("expire_entries.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)
