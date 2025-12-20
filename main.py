from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import sqlite3
import os
import csv
from io import StringIO
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')  # Change this in production!

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'لطفاً ابتدا وارد شوید'

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# Database Configuration for Liara
# If running on Liara (where /app/data exists), use the persistent disk.
# Otherwise (local), use the current directory.
if os.path.exists('/app/data'):
    DB_FOLDER = '/app/data'
else:
    DB_FOLDER = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(DB_FOLDER, 'students.db')

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Legacy students table (keep for admin reference)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Users table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT,
                google_id TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                track TEXT NOT NULL,
                order_index INTEGER,
                total_modules INTEGER DEFAULT 6,
                price INTEGER DEFAULT 2500000,
                duration_weeks INTEGER DEFAULT 4
            )
        ''')
        
        # Specializations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS specializations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                track_code TEXT UNIQUE NOT NULL,
                original_price INTEGER,
                discounted_price INTEGER,
                icon TEXT,
                duration_weeks INTEGER
            )
        ''')
        
        # Enrollments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                UNIQUE(user_id, course_id)
            )
        ''')
        
        # Course progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                module_number INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (course_id) REFERENCES courses(id),
                UNIQUE(user_id, course_id, module_number)
            )
        ''')

        # Contact messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        # Migration: Add price column to courses if it doesn't exist
        cursor.execute("PRAGMA table_info(courses)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'price' not in columns:
            cursor.execute("ALTER TABLE courses ADD COLUMN price INTEGER DEFAULT 2500000")
        if 'duration_weeks' not in columns:
            cursor.execute("ALTER TABLE courses ADD COLUMN duration_weeks INTEGER DEFAULT 4")
        if 'start_date' not in columns:
            cursor.execute("ALTER TABLE courses ADD COLUMN start_date TEXT")
            
        cursor.execute("PRAGMA table_info(specializations)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'duration_weeks' not in columns:
            cursor.execute("ALTER TABLE specializations ADD COLUMN duration_weeks INTEGER")
        
        # Always ensure durations and start dates are populated for existing specializations
        cursor.execute("UPDATE specializations SET duration_weeks = 20 WHERE track_code = 'LLM' AND duration_weeks IS NULL")
        cursor.execute("UPDATE specializations SET duration_weeks = 24 WHERE track_code = 'AI_ROBOTICS' AND duration_weeks IS NULL")

        # Start dates logic (4 Bahman 1404, 2 per week)
        start_dates = [
            ('ریاضیات پیشرفته و نظریه یادگیری آماری', '۴ بهمن ۱۴۰۴'),
            ('مبانی نظری زبان‌شناسی محاسباتی', '۴ بهمن ۱۴۰۴'),
            ('تحلیل ریاضی معماری ترنسفورمرها', '۱۱ بهمن ۱۴۰۴'),
            ('نظریه مدل‌های مولد', '۱۱ بهمن ۱۴۰۴'),
            ('سمینار پژوهشی NLP', '۱۸ بهمن ۱۴۰۴'),
            ('مبانی پایتون و ساختمان داده‌ها', '۱۸ بهمن ۱۴۰۴'),
            ('الگوریتم‌ها و تفکر محاسباتی', '۲۵ بهمن ۱۴۰۴'),
            ('ریاضیات پایه AI و بهینه سازی', '۲۵ بهمن ۱۴۰۴'),
            ('اصول یادگیری ماشین و عمیق', '۲ اسفند ۱۴۰۴'),
            ('بینایی ماشین و مکانیزم‌های توجه', '۲ اسفند ۱۴۰۴'),
            ('رباتیک و سیستم‌های هوشمند', '۹ اسفند ۱۴۰۴'),
            ('زبان تخصصی هوش مصنوعی', '۹ اسفند ۱۴۰۴')
        ]
        for title, date in start_dates:
            cursor.execute("UPDATE courses SET start_date = ? WHERE title = ?", (date, title))

        # Specific migration: Add "English for AI" course if missing
        cursor.execute("SELECT COUNT(*) FROM courses WHERE title = 'زبان تخصصی هوش مصنوعی'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO courses (title, description, track, order_index, total_modules, price, duration_weeks, start_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('زبان تخصصی هوش مصنوعی', 'تقویت مهارت‌های خواندن مقالات پژوهشی، درک مستندات فنی و مهارت‌های پرامپت‌نویسی به زبان انگلیسی.', 'GENERAL', 1, 4, 1500000, 4, '۹ اسفند ۱۴۰۴'))

        conn.commit()
        
        # Seed specializations if empty
        cursor.execute('SELECT COUNT(*) FROM specializations')
        if cursor.fetchone()[0] == 0:
            specializations_data = [
                ("مسیر تخصصی مدل‌های زبانی بزرگ (LLM Mastery)", "تمرکز عمیق بر مبانی ریاضی، نظریه یادگیری آماری و معماری مدل‌های زبانی.", "LLM", 12500000, 9900000, "💬", 20),
                ("مسیر جامع هوش مصنوعی و رباتیک (AI & Robotics - 6 Steps)", "یک برنامه جامع ۶ مرحله‌ای از مبانی تا سیستم‌های هوشمند پیشرفته.", "AI_ROBOTICS", 15000000, 11900000, "🤖", 24)
            ]
            cursor.executemany('INSERT INTO specializations (title, description, track_code, original_price, discounted_price, icon, duration_weeks) VALUES (?, ?, ?, ?, ?, ?, ?)', specializations_data)
            conn.commit()

        # Seed courses if empty
        cursor.execute('SELECT COUNT(*) FROM courses')
        if cursor.fetchone()[0] == 0:
            courses_data = [
                ('ریاضیات پیشرفته و نظریه یادگیری آماری', 'تمرکز بر مبانی ریاضی و نظریه یادگیری', 'LLM', 1, 6, 2500000, 4, '۴ بهمن ۱۴۰۴'),
                ('مبانی نظری زبان‌شناسی محاسباتی', 'اصول زبان‌شناسی برای NLP', 'LLM', 2, 6, 2500000, 4, '۴ بهمن ۱۴۰۴'),
                ('تحلیل ریاضی معماری ترنسفورمرها', 'معماری و مکانیزم توجه', 'LLM', 3, 6, 2500000, 4, '۱۱ بهمن ۱۴۰۴'),
                ('نظریه مدل‌های مولد', 'مدل‌های مولد و استنتاج احتمالاتی', 'LLM', 4, 6, 2500000, 4, '۱۱ بهمن ۱۴۰۴'),
                ('سمینار پژوهشی NLP', 'تحلیل مقالات پیشرفته', 'LLM', 5, 6, 2500000, 4, '۱۸ بهمن ۱۴۰۴'),
                ('مبانی پایتون و ساختمان داده‌ها', 'شروع مسیر برنامه‌نویسی', 'AI_ROBOTICS', 1, 6, 2500000, 4, '۱۸ بهمن ۱۴۰۴'),
                ('الگوریتم‌ها و تفکر محاسباتی', 'مبانی تفکر الگوریتمیک', 'AI_ROBOTICS', 2, 6, 2500000, 4, '۲۵ بهمن ۱۴۰۴'),
                ('ریاضیات پایه AI و بهینه سازی', 'ریاضیات مورد نیاز برای یادگیری ماشین', 'AI_ROBOTICS', 3, 6, 2500000, 4, '۲۵ بهمن ۱۴۰۴'),
                ('اصول یادگیری ماشین و عمیق', 'ML و DL از مبانی تا پیشرفته', 'AI_ROBOTICS', 4, 6, 2500000, 4, '۲ اسفند ۱۴۰۴'),
                ('بینایی ماشین و مکانیزم‌های توجه', 'Computer Vision و Attention', 'AI_ROBOTICS', 5, 6, 2500000, 4, '۲ اسفند ۱۴۰۴'),
                ('رباتیک و سیستم‌های هوشمند', 'کاربردهای عملی AI در رباتیک', 'AI_ROBOTICS', 6, 6, 2500000, 4, '۹ اسفند ۱۴۰۴'),
                ('زبان تخصصی هوش مصنوعی', 'تقویت مهارت‌های خواندن مقالات پژوهشی، درک مستندات فنی و مهارت‌های پرامپت‌نویسی به زبان انگلیسی.', 'GENERAL', 1, 4, 1500000, 4, '۹ اسفند ۱۴۰۴'),
            ]
            cursor.executemany('INSERT INTO courses (title, description, track, order_index, total_modules, price, duration_weeks, start_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', courses_data)
            conn.commit()

init_db()

# Common SEO Keywords
KEYWORDS = "موسسه, آموزشی, هوش مصنوعی, یادگیری ماشین, تهران, شهرک غرب, سعادت آباد, کرج, روباتیک, مدل های زبانی, دید ماشین, بینایی ماشین, علوم داده"

# Admin password (CHANGE THIS!)
ADMIN_PASSWORD = "houshdan2024"

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['email'], user_data['name'])
    return None

# Register authentication and student routes
from auth_routes import register_auth_routes
from student_routes import register_student_routes

register_auth_routes(app, DB_NAME, google)
register_student_routes(app, DB_NAME)

@app.route('/')
def home():
    return render_template('index.html', 
                         title="خانه", 
                         description="موسسه آموزشی هوشدان. برگزارکننده دوره‌های تخصصی آنلاین هوش مصنوعی، یادگیری ماشین، علوم داده، رباتیک و مدل‌های زبانی.",
                         keywords=KEYWORDS)

@app.route('/paths')
def paths():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all specializations
        cursor.execute('SELECT * FROM specializations')
        specs = cursor.fetchall()
        
        tracks = []
        for spec in specs:
            # Get courses for this track
            cursor.execute('SELECT * FROM courses WHERE track = ? ORDER BY order_index', (spec['track_code'],))
            track_courses = cursor.fetchall()
            
            # The start date of the track is the start date of its first course
            track_start_date = track_courses[0]['start_date'] if track_courses else 'بزودی'
            
            tracks.append({
                "title": spec['title'],
                "desc": spec['description'],
                "original_price": spec['original_price'],
                "discounted_price": spec['discounted_price'],
                "formatted_original": "{:,}".format(spec['original_price']),
                "formatted_discounted": "{:,}".format(spec['discounted_price']),
                "icon": spec['icon'],
                "duration": spec['duration_weeks'],
                "start_date": track_start_date,
                "courses": track_courses
            })
            
    return render_template('paths.html', tracks=tracks,
                         title="مسیرهای آموزشی",
                         description="مسیرهای تخصصی هوش مصنوعی و رباتیک با تخفیف ویژه ثبت‌نام کل دوره.",
                         keywords=KEYWORDS)

@app.route('/courses')
def courses():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all individual courses
        cursor.execute('SELECT * FROM courses ORDER BY track, order_index')
        all_courses = cursor.fetchall()
        
        formatted_courses = []
        for course in all_courses:
            c_dict = dict(course)
            c_dict['formatted_price'] = "{:,}".format(course['price'])
            c_dict['duration'] = course['duration_weeks']
            c_dict['start_date'] = course['start_date']
            formatted_courses.append(c_dict)
            
    return render_template('courses.html', courses=formatted_courses,
                         title="دوره‌های آموزشی",
                         description="لیست کامل دوره‌های تخصصی هوش مصنوعی، یادگیری ماشین و رباتیک.",
                         keywords=KEYWORDS)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject', 'بدون موضوع')
        message = request.form.get('message')
        
        if not name or not email or not message:
            flash('لطفاً تمامی فیلدها را پر کنید', 'error')
            return redirect(url_for('contact'))
            
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO contact_messages (name, email, subject, message)
                VALUES (?, ?, ?, ?)
            ''', (name, email, subject, message))
            conn.commit()
            
        # Send Email Notification
        try:
            msg = Message(
                subject=f"پیام جدید از {name}: {subject}",
                recipients=[os.environ.get('ADMIN_EMAIL', 'hadiataei@gmail.com')], # Default or env
                body=f"نام: {name}\nایمیل: {email}\nموضوع: {subject}\n\nپیام:\n{message}"
            )
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {e}")
            # We still show success since it's saved in the DB
            
        flash('پیام شما با موفقیت ارسال شد. به زودی با شما تماس خواهیم گرفت.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html',
                         title="تماس با ما",
                         description="با موسسه هوشدان در ارتباط باشید. مشاوره رایگان و پاسخ به سوالات شما.",
                         keywords=KEYWORDS)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        mode = request.form['mode'] # Online or In-Person

        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO students (name, email, phone, mode) VALUES (?, ?, ?, ?)',
                               (name, email, phone, mode))
                conn.commit()
            flash('ثبت نام با موفقیت انجام شد! به زودی با شما تماس خواهیم گرفت.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'خطا: {e}', 'error')
    
    return render_template('register.html',
                         title="ثبت نام",
                         description="ثبت نام در کلاس‌های حضوری هوش مصنوعی در شهرک غرب، سعادت آباد و کرج. شروع مسیر یادگیری ماشین و علوم داده.",
                         keywords=KEYWORDS)

@app.route('/robots.txt')
def robots():
    return "User-agent: *\nAllow: /", 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://houshdan.ai/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://houshdan.ai/courses</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://houshdan.ai/register</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>"""
    return xml, 200, {'Content-Type': 'application/xml'}

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='رمز عبور اشتباه است')
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students ORDER BY created_at DESC')
            students = cursor.fetchall()
        return render_template('admin_dashboard.html', students=students)
    except Exception as e:
        flash(f'خطا در بارگذاری داده‌ها: {e}', 'error')
        return render_template('admin_dashboard.html', students=[])

@app.route('/admin/export')
def admin_export_csv():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students ORDER BY created_at DESC')
            students = cursor.fetchall()
        
        # Create CSV
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Mode', 'Created At'])
        for student in students:
            writer.writerow([student['id'], student['name'], student['email'], 
                           student['phone'], student['mode'], student['created_at']])
        
        output = si.getvalue()
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=students.csv'}
        )
    except Exception as e:
        flash(f'خطا در ایجاد فایل CSV: {e}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    # Use 0.0.0.0 to allow external connections (required for Liara/Docker)
    app.run(debug=True, host='0.0.0.0', port=8000)
