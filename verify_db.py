import sqlite3
import os

DB_FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(DB_FOLDER, 'students.db')

def init_db(db_name):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                track TEXT NOT NULL,
                order_index INTEGER,
                total_modules INTEGER DEFAULT 6,
                price INTEGER DEFAULT 2500000
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS specializations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                track_code TEXT UNIQUE NOT NULL,
                original_price INTEGER,
                discounted_price INTEGER,
                icon TEXT
            )
        ''')
        cursor.execute("PRAGMA table_info(courses)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'price' not in columns:
            cursor.execute("ALTER TABLE courses ADD COLUMN price INTEGER DEFAULT 2500000")
        
        cursor.execute('SELECT COUNT(*) FROM specializations')
        if cursor.fetchone()[0] == 0:
            specializations_data = [
                ("مسیر تخصصی مدل‌های زبانی بزرگ (LLM Mastery)", "تمرکز عمیق بر مبانی ریاضی، نظریه یادگیری آماری و معماری مدل‌های زبانی.", "LLM", 12500000, 9900000, "💬"),
                ("مسیر جامع هوش مصنوعی و رباتیک (AI & Robotics - 6 Steps)", "یک برنامه جامع ۶ مرحله‌ای از مبانی تا سیستم‌های هوشمند پیشرفته.", "AI_ROBOTICS", 15000000, 11900000, "🤖")
            ]
            cursor.executemany('INSERT INTO specializations (title, description, track_code, original_price, discounted_price, icon) VALUES (?, ?, ?, ?, ?, ?)', specializations_data)
        
        cursor.execute('SELECT COUNT(*) FROM courses')
        if cursor.fetchone()[0] == 0:
            courses_data = [
                ('ریاضیات پیشرفته و نظریه یادگیری آماری', 'تمرکز بر مبانی ریاضی و نظریه یادگیری', 'LLM', 1, 6, 2500000),
                ('مبانی نظری زبان‌شناسی محاسباتی', 'اصول زبان‌شناسی برای NLP', 'LLM', 2, 6, 2500000),
                ('تحلیل ریاضی معماری ترنسفورمرها', 'معماری و مکانیزم توجه', 'LLM', 3, 6, 2500000),
                ('نظریه مدل‌های مولد', 'مدل‌های مولد و استنتاج احتمالاتی', 'LLM', 4, 6, 2500000),
                ('سمینار پژوهشی NLP', 'تحلیل مقالات پیشرفته', 'LLM', 5, 6, 2500000),
                ('مبانی پایتون و ساختمان داده‌ها', 'شروع مسیر برنامه‌نویسی', 'AI_ROBOTICS', 1, 6, 2500000),
                ('الگوریتم‌ها و تفکر محاسباتی', 'حل مسئله و طراحی الگوریتم', 'AI_ROBOTICS', 2, 6, 2500000),
                ('ریاضیات پایه AI و بهینه‌سازی', 'جبر خطی، حساب دیفرانسیل و بهینه‌سازی', 'AI_ROBOTICS', 3, 6, 2500000),
                ('اصول یادگیری ماشین و عمیق', 'ML و DL از مبانی تا پیشرفته', 'AI_ROBOTICS', 4, 6, 2500000),
                ('بینایی ماشین و مکانیزم‌های توجه', 'Computer Vision و Attention', 'AI_ROBOTICS', 5, 6, 2500000),
                ('رباتیک و سیستم‌های هوشمند', 'کاربردهای عملی AI در رباتیک', 'AI_ROBOTICS', 6, 6, 2500000),
            ]
            cursor.executemany('INSERT INTO courses (title, description, track, order_index, total_modules, price) VALUES (?, ?, ?, ?, ?, ?)', courses_data)
        
        conn.commit()

def verify():
    init_db(DB_NAME)
    if not os.path.exists(DB_NAME):
        print(f"FAILURE: Database file {DB_NAME} not found.")
        return

    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check specializations
            print("Checking specializations...")
            cursor.execute('SELECT * FROM specializations')
            specs = cursor.fetchall()
            if len(specs) == 2:
                print(f"SUCCESS: Found 2 specializations.")
                for spec in specs:
                    print(f" - {spec['title']}: {spec['discounted_price']} Toman")
            else:
                print(f"FAILURE: Expected 2 specializations, found {len(specs)}.")

            # Check courses and prices
            print("\nChecking courses...")
            cursor.execute('SELECT COUNT(*) FROM courses WHERE price = 2500000')
            count = cursor.fetchone()[0]
            if count >= 11:
                print(f"SUCCESS: Found {count} courses with correct price.")
            else:
                print(f"FAILURE: Expected at least 11 courses with price 2500000, found {count}.")

            # Check individual tracks
            print("\nChecking track distribution...")
            cursor.execute('SELECT track, COUNT(*) as count FROM courses GROUP BY track')
            tracks = cursor.fetchall()
            for track in tracks:
                print(f" - Track {track['track']}: {track['count']} courses")
                if track['track'] == 'LLM' and track['count'] != 5:
                    print("   WARNING: LLM should have 5 courses.")
                if track['track'] == 'AI_ROBOTICS' and track['count'] != 6:
                    print("   WARNING: AI_ROBOTICS should have 6 courses.")

    except Exception as e:
        print(f"FAILURE: An error occurred during verification: {e}")

if __name__ == "__main__":
    verify()
