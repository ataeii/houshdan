# Authentication routes for Houshdan AI
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

def register_auth_routes(app, db_name, google_oauth):
    """Register all authentication routes"""
    
    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not name or not email or not password:
                flash('لطفاً تمام فیلدها را پر کنید', 'error')
                return render_template('signup.html')
            
            # Check if user exists
            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
                if cursor.fetchone():
                    flash('این ایمیل قبلاً ثبت شده است', 'error')
                    return render_template('signup.html')
                
                # Create user
                password_hash = generate_password_hash(password)
                cursor.execute('INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)',
                             (email, name, password_hash))
                conn.commit()
                
                flash('ثبت نام با موفقیت انجام شد! لطفاً وارد شوید', 'success')
                return redirect(url_for('login'))
        
        return render_template('signup.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            with sqlite3.connect(db_name) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
                user_data = cursor.fetchone()
                
                if user_data and user_data['password_hash'] and check_password_hash(user_data['password_hash'], password):
                    from main import User
                    user = User(user_data['id'], user_data['email'], user_data['name'])
                    login_user(user)
                    flash(f'خوش آمدید، {user.name}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('ایمیل یا رمز عبور اشتباه است', 'error')
        
        return render_template('login.html')
    
    @app.route('/auth/google')
    def google_login():
        redirect_uri = url_for('google_callback', _external=True)
        return google_oauth.authorize_redirect(redirect_uri)
    
    @app.route('/auth/google/callback')
    def google_callback():
        token = google_oauth.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('خطا در ورود با Google', 'error')
            return redirect(url_for('login'))
        
        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')
        
        with sqlite3.connect(db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT * FROM users WHERE google_id = ? OR email = ?', (google_id, email))
            user_data = cursor.fetchone()
            
            if user_data:
                # Update google_id if needed
                if not user_data['google_id']:
                    cursor.execute('UPDATE users SET google_id = ? WHERE id = ?', (google_id, user_data['id']))
                    conn.commit()
            else:
                # Create new user
                cursor.execute('INSERT INTO users (email, name, google_id) VALUES (?, ?, ?)',
                             (email, name, google_id))
                conn.commit()
                cursor.execute('SELECT * FROM users WHERE google_id = ?', (google_id,))
                user_data = cursor.fetchone()
            
            from main import User
            user = User(user_data['id'], user_data['email'], user_data['name'])
            login_user(user)
            flash(f'خوش آمدید، {user.name}!', 'success')
            return redirect(url_for('dashboard'))
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('با موفقیت خارج شدید', 'success')
        return redirect(url_for('home'))
