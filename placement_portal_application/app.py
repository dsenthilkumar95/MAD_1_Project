
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------------- MODELS ----------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))  # admin/company/student
    approved = db.Column(db.Boolean, default=False)
    blacklisted = db.Column(db.Boolean, default=False)

class PlacementDrive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    eligibility = db.Column(db.String(200))
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default="Pending")
    company_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'))
    status = db.Column(db.String(20), default="Applied")
    date_applied = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------- INIT DB ----------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role="admin").first():
        admin = User(
            name="Admin",
            email="admin@portal.com",
            password=generate_password_hash("admin123"),
            role="admin",
            approved=True
        )
        db.session.add(admin)
        db.session.commit()

# ---------------------- ROUTES ----------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register/<role>", methods=["GET","POST"])
def register(role):
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        user = User(name=name, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully. Wait for admin approval.")
        return redirect(url_for("login"))
    return render_template("register.html", role=role)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if user.blacklisted:
                flash("Account blacklisted.")
                return redirect(url_for("login"))
            if user.role != "admin" and not user.approved:
                flash("Waiting for admin approval.")
                return redirect(url_for("login"))
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        users = User.query.all()
        drives = PlacementDrive.query.all()
        applications = Application.query.all()
        return render_template("admin/dashboard.html", users=users, drives=drives, applications=applications)
    elif current_user.role == "company":
        drives = PlacementDrive.query.filter_by(company_id=current_user.id).all()
        return render_template("company/dashboard.html", drives=drives)
    else:
        drives = PlacementDrive.query.filter_by(status="Approved").all()
        apps = Application.query.filter_by(student_id=current_user.id).all()
        return render_template("student/dashboard.html", drives=drives, apps=apps)

@app.route("/approve_user/<int:user_id>")
@login_required
def approve_user(user_id):
    if current_user.role == "admin":
        user = User.query.get(user_id)
        user.approved = True
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/create_drive", methods=["GET","POST"])
@login_required
def create_drive():
    if current_user.role == "company":
        if request.method == "POST":
            drive = PlacementDrive(
                title=request.form["title"],
                description=request.form["description"],
                eligibility=request.form["eligibility"],
                deadline=datetime.strptime(request.form["deadline"], "%Y-%m-%d"),
                company_id=current_user.id
            )
            db.session.add(drive)
            db.session.commit()
            return redirect(url_for("dashboard"))
        return render_template("company/create_drive.html")
    return redirect(url_for("dashboard"))

@app.route("/apply/<int:drive_id>")
@login_required
def apply(drive_id):
    if current_user.role == "student":
        existing = Application.query.filter_by(student_id=current_user.id, drive_id=drive_id).first()
        if not existing:
            app_entry = Application(student_id=current_user.id, drive_id=drive_id)
            db.session.add(app_entry)
            db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
