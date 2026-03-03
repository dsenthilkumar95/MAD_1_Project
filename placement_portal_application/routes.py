from extensions import app, db
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, PlacementDrive, Application
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def home():
    return render_template("home.html")

@main_bp.route("/register/<role>", methods=["GET","POST"])
def register(role):
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        user = User(name=name, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully. Wait for admin approval.")
        return redirect(url_for("main.login"))
    return render_template("register.html", role=role)

@main_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if user.blacklisted:
                flash("Account blacklisted.")
                return redirect(url_for("main.login"))
            if user.role != "admin" and not user.approved:
                flash("Waiting for admin approval.")
                return redirect(url_for("main.login"))
            login_user(user)
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials")
    return render_template("login.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        users = User.query.all()
        drives = PlacementDrive.query.all()
        applications = Application.query.all()
        return render_template("admin/dashboard.html", users=users, drives=drives, applications=applications, User=User)
    elif current_user.role == "company":
        drives = PlacementDrive.query.filter_by(company_id=current_user.id).all()
        return render_template("company/dashboard.html", drives=drives)
    else:
        apps = Application.query.filter_by(student_id=current_user.id).all()
        drive_id_list = [ap.drive_id for ap in apps]
        drive_id_list = list(set(drive_id_list))
        drives = PlacementDrive.query.filter_by(status="Approved").filter(~PlacementDrive.id.in_(drive_id_list)).all()
        return render_template("student/dashboard.html", drives=drives, apps=apps, User=User, PlacementDrive=PlacementDrive)

@main_bp.route("/approve_user/<int:user_id>")
@login_required
def approve_user(user_id):
    if current_user.role == "admin":
        user = User.query.get(user_id)
        user.approved = True
        db.session.commit()
    return redirect(url_for("main.dashboard"))

@main_bp.route("/approve_drive/<int:drive_id>")
@login_required
def approve_drive(drive_id):
    if current_user.role == "admin":
        drive = PlacementDrive.query.get(drive_id)
        drive.status = "Approved"
        db.session.commit()
    return redirect(url_for("main.dashboard"))

@main_bp.route("/create_drive", methods=["GET","POST"])
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
            return redirect(url_for("main.dashboard"))
        return render_template("company/create_drive.html")
    return redirect(url_for("main.dashboard"))

@main_bp.route("/apply/<int:drive_id>")
@login_required
def apply(drive_id):
    if current_user.role == "student":
        existing = Application.query.filter_by(student_id=current_user.id, drive_id=drive_id).first()
        if not existing:
            app_entry = Application(student_id=current_user.id, drive_id=drive_id)
            db.session.add(app_entry)
            db.session.commit()
    return redirect(url_for("main.dashboard"))

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))