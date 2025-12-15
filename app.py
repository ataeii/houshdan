from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production!

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
        conn.commit()

init_db()

# Common SEO Keywords
KEYWORDS = "موسسه, آموزشی, هوش مصنوعی, یادگیری ماشین, تهران, شهرک غرب, سعادت آباد, کرج, روباتیک, مدل های زبانی, دید ماشین, بینایی ماشین, علوم داده"

@app.route('/')
def home():
    return render_template('index.html', 
                         title="خانه", 
                         description="موسسه آموزشی هوشدان در تهران (شهرک غرب و سعادت آباد) و کرج. برگزارکننده دوره‌های تخصصی هوش مصنوعی، یادگیری ماشین، علوم داده، رباتیک و مدل‌های زبانی.",
                         keywords=KEYWORDS)

@app.route('/courses')
def courses():
    tracks = [
        {
            "title": "مسیر تخصصی مدل‌های زبانی بزرگ (LLM Mastery)",
            "desc": "تمرکز عمیق بر مبانی ریاضی، نظریه یادگیری آماری و معماری مدل‌های زبانی.",
            "courses": [
                "ریاضیات پیشرفته و نظریه یادگیری آماری (Statistical Learning Theory)",
                "مبانی نظری زبان‌شناسی محاسباتی (Computational Linguistics)",
                "تحلیل ریاضی معماری ترنسفورمرها و مکانیزم توجه (Attention)",
                "نظریه مدل‌های مولد و استنتاج احتمالات (Generative Models Theory)",
                "سمینار پژوهشی: تحلیل مقالات پیشرفته NLP"
            ],
            "icon": "💬"
        },
        {
            "title": "مسیر جامع هوش مصنوعی و رباتیک (AI & Robotics - 6 Steps)",
            "desc": "یک برنامه جامع ۶ مرحله‌ای از مبانی تا سیستم‌های هوشمند پیشرفته.",
            "courses": [
                "۱. مبانی پایتون و ساختمان داده‌ها (Python & Data Structures)",
                "۲. الگوریتم‌ها و تفکر محاسباتی (Algorithms)",
                "۳. ریاضیات پایه هوش مصنوعی و بهینه‌سازی (Math & Optimization)",
                "۴. اصول یادگیری ماشین و عمیق (ML & Deep Learning Core)",
                "۵. بینایی ماشین و مکانیزم‌های توجه (Computer Vision & Attention)",
                "۶. رباتیک و سیستم‌های هوشمند (Robotics & Intelligent Systems)"
            ],
            "icon": "🤖"
        }
    ]
    return render_template('courses.html', tracks=tracks,
                         title="دوره آموزشی",
                         description="دوره جامع هوش مصنوعی و رباتیک در تهران و کرج. آموزش عملی مدل‌های زبانی، دید ماشین و علوم داده با مدرک معتبر.",
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
