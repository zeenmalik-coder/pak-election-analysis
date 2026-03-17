from flask import Flask, render_template, request, redirect, session, url_for, flash
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64
import os
import csv
import uuid
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO

app = Flask(__name__)
app.secret_key = "pak_election_secret_key_2024" 

# File Paths
CANDIDATES_FILE = "candidates.csv"
USERS_FILE = "users.csv"
VOTES_FILE = "votes.csv"
DETAILS_FILE = "voter_details.csv"
ADMIN_USERS_FILE = "admin_users.csv"

# Owner Credentials
OWNER_USERNAME = "admin"
OWNER_PASSWORD = "secret123" 

# Pakistan Cities Data
PAKISTAN_CITIES = {
    "Punjab": ["Lahore", "Rawalpindi", "Faisalabad", "Multan", "Gujranwala", "Sialkot", "Bahawalpur", "Sargodha", "Sheikhupura", "Jhang", "Rahim Yar Khan", "Gujrat", "Mardan", "Kasur", "Dera Ghazi Khan", "Sahiwal", "Narowal", "Okara", "Chiniot", "Sadiqabad", "Burewala", "Khanewal", "Hafizabad", "Kohat", "Muzaffargarh", "Khanpur", "Gojra", "Bahawalnagar", "Muridke", "Pakpattan", "Abottabad", "Toba Tek Singh", "Jhelum", "Kamoke"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah", "Mirpur Khas", "Jacobabad", "Shikarpur", "Khairpur", "Dadu", "Thatta", "Umerkot", "Tando Allahyar", "Jamshoro", "Badin", "Ghotki", "Sanghar", "Benazirabad", "Kashmore", "Matiari", "Tando Muhammad Khan", "Hala", "Diplo", "Islamkot"],
    "KPK": ["Peshawar", "Mardan", "Abbottabad", "Swat", "Kohat", "Bannu", "Dera Ismail Khan", "Charsadda", "Nowshera", "Haripur", "Tank", "Mansehra", "Mingora", "Hangu", "Lakki Marwat", "Batagram", "Upper Dir", "Lower Dir", "Shangla", "Tor Ghar"],
    "Balochistan": ["Quetta", "Gwadar", "Turbat", "Zhob", "Khuzdar", "Sibi", "Chaman", "Kalat", "Nasirabad", "Jaffarabad", "Loralai", "Musakhel", "Barkhan", "Killa Abdullah", "Killa Saifullah", "Ziarat", "Harnai", "Sherani", "Pishin", "Panjgur", "Washuk", "Awaran"],
    "Islamabad": ["Islamabad"],
    "Gilgit-Baltistan": ["Gilgit", "Skardu", "Hunza", "Nagar", "Ghanche", "Diamer"],
    "Azad Kashmir": ["Muzaffarabad", "Mirpur", "Kotli", "Rawalakot", "Bagh", "Poonch"]
}

# -------------------------
# 1. FILE INITIALIZATION
# -------------------------
def setup_files():
    # Users CSV
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Password", "CNIC", "Phone"])
    
    # Votes CSV
    if not os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Voted"])
            
    # Voter Details CSV
    if not os.path.exists(DETAILS_FILE):
        with open(DETAILS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "CNIC", "City", "Province", "Candidate", "Timestamp"])
            
    # Candidates CSV
    if not os.path.exists(CANDIDATES_FILE):
        data = [
            ["Candidate", "Party", "Votes"],
            ["Imran Khan", "PTI", 0],
            ["Shehbaz Sharif", "PML-N", 0],
            ["Bilawal Bhutto Zardari", "PPP", 0],
            ["Maulana Fazlur Rehman", "JUI-F", 0],
            ["Siraj-ul-Haq", "JI", 0]
        ]
        with open(CANDIDATES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    # Admin Users CSV (NEW)
    if not os.path.exists(ADMIN_USERS_FILE):
        with open(ADMIN_USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Password", "Role"])
            # Create main owner automatically
            writer.writerow([OWNER_USERNAME, generate_password_hash(OWNER_PASSWORD), "Owner"])
        print("[OK] Admin Users DB Initialized")

    print("[OK] System Ready with CNIC Support")

setup_files()

# -------------------------
# 2. HELPER FUNCTIONS
# -------------------------
def validate_cnic(cnic):
    pattern = r'^\d{5}-\d{7}-\d{1}$'
    return re.match(pattern, cnic) is not None

def get_users_list():
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f): users.append(row)
    return users

def add_user(username, pwd_hash, cnic, phone):
    with open(USERS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([username, pwd_hash, cnic, phone])

def get_candidates_df():
    try: return pd.read_csv(CANDIDATES_FILE)
    except: return pd.DataFrame(columns=["Candidate", "Party", "Votes"])

def save_candidates_df(df):
    df.to_csv(CANDIDATES_FILE, index=False)

def get_votes_list():
    votes = []
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f): votes.append(row)
    return votes

def add_vote(username):
    with open(VOTES_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([username, True])

def add_voter_detail(name, cnic, city, province, candidate, timestamp):
    with open(DETAILS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([name, cnic, city, province, candidate, timestamp])

def get_voter_details():
    details = []
    if os.path.exists(DETAILS_FILE):
        with open(DETAILS_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f): details.append(row)
    return details

# --- NEW ADMIN HELPERS ---
def get_admin_users():
    admins = []
    if os.path.exists(ADMIN_USERS_FILE):
        with open(ADMIN_USERS_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f):
                admins.append(row)
    return admins

def add_admin_user(username, pwd_hash, role="Observer"):
    with open(ADMIN_USERS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([username, pwd_hash, role])



@app.route("/admin/export-voters-pdf")
def export_voters_pdf():
    # Check if admin is logged in
    if not session.get('is_owner'):
        flash("Access Denied", "danger")
        return redirect("/admin/voter-list")

    # Get data
    details = get_voter_details()
    if not details:
        flash("No voters to export.", "warning")
        return redirect("/admin/voter-list")

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=0.5*inch, leftMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title Style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'), # Navy
        spaceAfter=30,
        alignment=1 # Center
    )
    
    # Header
    elements.append(Paragraph("Official Voter Audit Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))

    # Table Data
    data = [['Name', 'CNIC', 'City', 'Province', 'Voted For', 'Time']]
    
    for row in details:
        data.append([
            row['Name'],
            row['CNIC'],
            row['City'],
            row['Province'],
            row['Candidate'],
            row['Timestamp']
        ])

    # Create Table
    tbl = Table(data, repeatRows=1)
    
    # Table Styling
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')), # Navy Header
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')), # Light grey rows
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]), # Striped rows
    ])
    tbl.setStyle(style)
    
    elements.append(tbl)
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    
    # Send file to user
    from flask import send_file
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Voter_List_{datetime.now().strftime("%Y%m%d")}.pdf'
    )
# -------------------------
# 3. ROUTES
# -------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    # CHECK 1: Is the user logged in?
    if "username" in session:
        # --- EXISTING VOTING LOGIC (Only for logged-in users) ---
        username = session["username"]
        votes = get_votes_list()
        voted = any(v.get('Username') == username for v in votes)
        candidates = get_candidates_df().to_dict(orient="records")

        if request.method == "POST" and not voted:
            selected = request.form.get("candidate")
            city = request.form.get("city")
            
            province = "Unknown"
            for prov, cities in PAKISTAN_CITIES.items():
                if city in cities:
                    province = prov
                    break

            if selected and city:
                try:
                    df = get_candidates_df()
                    df.loc[df["Candidate"] == selected, "Votes"] += 1
                    save_candidates_df(df)
                    add_vote(username)
                    
                    users = get_users_list()
                    user_cnic = "N/A"
                    for u in users:
                        if u['Username'] == username:
                            user_cnic = u.get('CNIC', 'N/A')
                            break
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    add_voter_detail(username, user_cnic, city, province, selected, timestamp)
                    
                    tx_id = str(uuid.uuid4())[:8].upper()
                    session['last_receipt'] = {"candidate": selected, "tx_id": tx_id, "time": timestamp}
                    
                    flash("Vote cast successfully!", "success")
                    return redirect("/results")
                except Exception as e:
                    print(f"VOTE ERROR: {e}")
                    flash(f"Error: {str(e)}", "danger")
        
        # Render the main voting page for logged-in users
        return render_template("index.html", candidates=candidates, voted=voted, cities=PAKISTAN_CITIES)

    else:
        # --- NEW BEHAVIOR: If NOT logged in, show the Landing Page ---
        # Do NOT flash a warning yet. Just show the welcome screen.
        return render_template("landing.html")
    
    # NEW ROUTE: Specifically for the Landing/Welcome Page
# ... imports and setup ...

# --- ROUTE 1: The Welcome/Landing Page (Optional, if you want a specific URL) ---
@app.route("/welcome")
def welcome():
    return render_template("landing.html")


# ... rest of your routes (login, register, results, etc.) ...
@app.route("/results")
def results():
    if "username" not in session:
        flash("Please login to view results.", "warning")
        return redirect("/login")
        
    df = get_candidates_df()
    votes = get_votes_list()
    total_voters = len(votes)
    
    winner, loser, chart_bar, chart_pie = "No votes yet", "N/A", "", ""
    total_votes = 0
    candidates = []

    if not df.empty and df["Votes"].sum() > 0:
        total_votes = df["Votes"].sum()
        df["Percentage"] = ((df["Votes"] / total_votes) * 100).round(2)
        
        max_votes = df["Votes"].max()
        winner_rows = df[df["Votes"] == max_votes]
        winner = winner_rows["Candidate"].tolist()[0] + (" & Others" if len(winner_rows) > 1 else "")
        
        min_votes = df["Votes"].min()
        loser_rows = df[df["Votes"] == min_votes]
        loser = loser_rows["Candidate"].tolist()[0] + (" & Others" if len(loser_rows) > 1 else "")

        try:
            img = io.BytesIO()
            plt.figure(figsize=(10, 6))
            colors = ['#ca8a04' if c in winner_rows['Candidate'].values else '#991b1b' if c in loser_rows['Candidate'].values else '#1e3a8a' for c in df['Candidate']]
            plt.bar(df["Candidate"], df["Votes"], color=colors)
            plt.title("Votes by Candidate")
            plt.tight_layout()
            plt.savefig(img, format="png")
            plt.close()
            img.seek(0)
            chart_bar = base64.b64encode(img.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Bar Chart Error: {e}")

        try:
            img2 = io.BytesIO()
            df_pie = df[df['Votes'] > 0]
            if not df_pie.empty:
                plt.figure(figsize=(5, 5))
                plt.pie(df_pie["Votes"], labels=df_pie["Candidate"], autopct="%1.0f%%", startangle=140)
                plt.title("Vote Share")
                plt.tight_layout()
                plt.savefig(img2, format="png", dpi=150)
                plt.close()
                img2.seek(0)
                chart_pie = base64.b64encode(img2.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Pie Chart Error: {e}")

        candidates = df.to_dict(orient="records")

    return render_template("results.html", candidates=candidates, chart_bar=chart_bar, chart_pie=chart_pie, winner=winner, loser=loser, total_votes=total_votes, total_voters=total_voters)


@app.route("/history")
def history():
    # Data sourced from Wikipedia: Elections in Pakistan
    election_data = [
        {
            "year": "2024",
            "date": "Feb 8, 2024",
            "turnout": "47.4%",
            "seats": "266",
            "winner": "Independent (PTI-backed)",
            "party": "Independent",
            "context": "Highly contested election with independent candidates backed by PTI securing the most seats."
        },
        {
            "year": "2018",
            "date": "July 25, 2018",
            "turnout": "51.7%",
            "seats": "270",
            "winner": "Imran Khan",
            "party": "PTI",
            "context": "PTI formed government after 10 years of PML-N rule. First time PTI came to power at federal level."
        },
        {
            "year": "2013",
            "date": "May 11, 2013",
            "turnout": "55.0%",
            "seats": "126",
            "winner": "Nawaz Sharif",
            "party": "PML-N",
            "context": "First time in Pakistan's history that one elected government completed its term and another was elected."
        },
        {
            "year": "2008",
            "date": "Feb 18, 2008",
            "turnout": "44.0%",
            "seats": "124",
            "winner": "Yousaf Raza Gillani",
            "party": "PPP",
            "context": "Held after the assassination of Benazir Bhutto. PPP formed a coalition government."
        },
        {
            "year": "2002",
            "date": "Oct 10, 2002",
            "turnout": "41.9%",
            "seats": "77",
            "winner": "Zafarullah Jamali",
            "party": "PML-Q",
            "context": "First election under General Pervez Musharraf's military rule. Introduction of LFO."
        }
    ]
    return render_template("history.html", elections=election_data)

@app.route("/parties")
def parties():
    # Data on Major Political Parties in Pakistan
    party_data = [
        {
            "name": "Pakistan Tehreek-e-Insaf",
            "acronym": "PTI",
            "leader": "Imran Khan",
            "symbol": "Cricket Bat",
            "ideology": "Populism, Islamic Welfare State, Anti-Corruption",
            "color": "#000000", # Black
            "founded": "1996"
        },
        {
            "name": "Pakistan Muslim League (N)",
            "acronym": "PML-N",
            "leader": "Shehbaz Sharif",
            "symbol": "Lion",
            "ideology": "Conservatism, Economic Liberalism, Infrastructure Development",
            "color": "#006400", # Dark Green
            "founded": "1993"
        },
        {
            "name": "Pakistan Peoples Party",
            "acronym": "PPP",
            "leader": "Bilawal Bhutto Zardari",
            "symbol": "Arrow",
            "ideology": "Social Democracy, Progressivism, Populism",
            "color": "#FF0000", # Red
            "founded": "1967"
        },
        {
            "name": "Jamiat Ulema-e-Islam (F)",
            "acronym": "JUI-F",
            "leader": "Maulana Fazlur Rehman",
            "symbol": "Book",
            "ideology": "Islamic Conservatism, Deobandi Islam",
            "color": "#008000", # Green
            "founded": "1980"
        },
        {
            "name": "Muttahida Qaumi Movement",
            "acronym": "MQM-P",
            "leader": "Khalid Maqbool Siddiqui",
            "symbol": "Kite",
            "ideology": "Liberalism, Secularism, Urban Rights",
            "color": "#00CED1", # Dark Turquoise
            "founded": "1984"
        },
        {
            "name": "Jamiat-e-Islami",
            "acronym": "JI",
            "leader": "Siraj-ul-Haq",
            "symbol": "Balance Scale",
            "ideology": "Islamism, Pan-Islamism, Conservative",
            "color": "#FFD700", # Gold
            "founded": "1941"
        },
        {
            "name": "Istehkam-e-Pakistan Party",
            "acronym": "IPP",
            "leader": "Jahangir Tareen",
            "symbol": "Pen",
            "ideology": "Populism, Agrarianism, Centrism",
            "color": "#FFA500", # Orange
            "founded": "2023"
        }
    ]
    return render_template("parties.html", parties=party_data)
# --- ADMIN: Manage Users (NEW) ---
import csv
import os

@app.route("/admin/manage-users", methods=["GET", "POST"])
def manage_users():
    # Security Check
    if not session.get('is_owner'):
        flash("Access Denied", "danger")
        return redirect("/admin/voter-list")

    # Handle Adding New User
    if request.method == "POST":
        new_user = request.form.get("username")
        new_pass = request.form.get("password")
        
        if new_user and new_pass:
            admin_file = 'admin_users.csv'
            file_exists = os.path.exists(admin_file)
            
            # Check if user already exists
            if file_exists:
                with open(admin_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['Username'] == new_user:
                            flash("Username already exists!", "warning")
                            return redirect("/admin/manage-users")
            
            # Add new user
            with open(admin_file, 'a', newline='') as f:
                fieldnames = ['Username', 'Password', 'Role']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({'Username': new_user, 'Password': generate_password_hash(new_pass), 'Role': 'Observer'})
            
            flash(f"Observer '{new_user}' added successfully!", "success")
            return redirect("/admin/manage-users")

    # GET Request: Load the list of users
    users = []
    admin_file = 'admin_users.csv'
    
    if os.path.exists(admin_file):
        with open(admin_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append(row)

    return render_template("admin_manage.html", users=users)

# NEW: Delete Route
@app.route("/admin/delete-user/<username>")
def delete_user(username):
    if not session.get('is_owner'):
        flash("Access Denied", "danger")
        return redirect("/admin/manage-users")

    if username == 'admin':
        flash("Cannot delete the main admin account!", "warning")
        return redirect("/admin/manage-users")

    admin_file = 'admin_users.csv'
    if not os.path.exists(admin_file):
        return redirect("/admin/manage-users")

    rows = []
    found = False
    
    with open(admin_file, 'r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['Username'] == username:
                found = True
                continue 
            rows.append(row)

    if found:
        with open(admin_file, 'w', newline='') as file:
            if rows:
                fieldnames = ['Username', 'Password', 'Role']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        flash(f"Observer '{username}' deleted.", "success")
    
    return redirect("/admin/manage-users")
# --- ADMIN: Voter List (Updated Logic) ---
@app.route("/admin/voter-list", methods=["GET", "POST"])
def admin_voter_list():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        
        admins = get_admin_users()
        valid_user = False
        
        for admin in admins:
            if admin['Username'] == user and check_password_hash(admin['Password'], pwd):
                valid_user = True
                session['is_owner'] = True
                session['admin_username'] = user
                break
        
        if valid_user:
            return redirect("/admin/voter-list")
        else:
            flash("Access Denied: Invalid Credentials", "danger")
            return redirect("/admin/voter-list")
    
    if not session.get('is_owner'):
        return render_template("admin_login.html")
    
    all_details = get_voter_details()
    filter_party = request.args.get('party')
    
    if filter_party and filter_party != "All":
        filtered_details = [row for row in all_details if row['Candidate'] == filter_party]
    else:
        filtered_details = all_details
    
    parties = sorted(list(set(row['Candidate'] for row in all_details)))

    return render_template("admin_list.html", 
                           details=filtered_details, 
                           all_count=len(all_details),
                           current_filter=filter_party,
                           parties=parties)

@app.route("/admin/back-to-site")
def admin_back_to_site():
    session.pop('is_owner', None)
    session.pop('admin_username', None)
    return redirect("/")

@app.route("/admin/logout")
def admin_logout():
    session.pop('is_owner', None)
    session.pop('admin_username', None)
    flash("Owner session ended.", "info")
    return redirect("/admin/voter-list")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        # 1. Get all users
        users = get_users_list()
        
        # 2. Find the user
        user_found = None
        for user in users:
            if user['Username'] == username:
                user_found = user
                break
        
        # 3. Check results
        if not user_found:
            # USER DOES NOT EXIST
            flash("User does not exist! Please register first.", "warning")
            return redirect("/login")
        
        # User exists, check password
        if check_password_hash(user_found['Password'], password):
            session["username"] = username
            return redirect("/")
        else:
            # Wrong password
            flash("Incorrect password. Please try again.", "danger")
            return redirect("/login")

    # GET request: Just show the page
    return render_template("auth.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # ... (Your existing register logic) ...
        username = request.form["username"].strip()
        password = request.form["password"]
        cnic = request.form["cnic"].strip()
        phone = request.form["phone"].strip()

        if not validate_cnic(cnic):
            flash("Invalid CNIC format!", "danger")
            return redirect("/register")

        users = get_users_list()
        for user in users:
            if user.get('Username') == username or user.get('CNIC') == cnic:
                flash("Username or CNIC already exists!", "danger")
                return redirect("/register")

        add_user(username, generate_password_hash(password), cnic, phone)
        flash("Registered! Please login.", "success")
        return redirect("/register")
    
    return render_template("auth.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    print("Starting Election System...")
    app.run(debug=True)