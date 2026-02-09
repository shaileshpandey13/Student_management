from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime
import csv
from io import StringIO
import urllib.parse

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-99'

# --- DATABASE CONFIGURATION ---
DB_USER = 'root'
DB_PASS = urllib.parse.quote_plus("shailesh")  # <--- UPDATE THIS
DB_NAME = 'student_db'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASS}@localhost/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    course = db.Column(db.String(50), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "course": self.course, "date": self.date_added.strftime("%d %b %Y")
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create Database and Admin User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('password123')
        admin = User(username='admin', password=hashed_pw)
        db.session.add(admin)
        db.session.commit()

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid Username or Password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user.username)

@app.route('/get_students')
@login_required
def get_students():
    students = Student.query.order_by(Student.date_added.desc()).all()
    return jsonify([s.to_dict() for s in students])

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    data = request.get_json()
    new_student = Student(name=data['name'], email=data['email'], course=data['course'])
    try:
        db.session.add(new_student)
        db.session.commit()
        return jsonify({"message": "Student Added Successfully!"}), 201
    except:
        db.session.rollback()
        return jsonify({"message": "Error: Duplicate Email"}), 400

@app.route('/delete_student/<int:id>', methods=['DELETE'])
@login_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({"message": "Deleted!"})

@app.route('/get_stats')
@login_required
def get_stats():
    total = Student.query.count()
    course_data = db.session.query(Student.course, func.count(Student.course)).group_by(Student.course).all()
    return jsonify({
        "total": total,
        "labels": [row[0] for row in course_data],
        "values": [row[1] for row in course_data]
    })

@app.route('/export_csv')
@login_required
def export_csv():
    students = Student.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Email', 'Course', 'Date'])
    for s in students:
        cw.writerow([s.id, s.name, s.email, s.course, s.date_added])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment; filename=student_report.csv"})

if __name__ == '__main__':
    app.run(debug=True)