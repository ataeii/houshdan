# Student dashboard and course management routes
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import sqlite3
from datetime import datetime

def register_student_routes(app, db_name):
    """Register student dashboard and course routes"""
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        with sqlite3.connect(db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get enrolled courses with progress
            cursor.execute('''
                SELECT c.*, e.enrolled_at,
                       COUNT(CASE WHEN cp.completed = 1 THEN 1 END) as completed_modules
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                LEFT JOIN course_progress cp ON cp.course_id = c.id AND cp.user_id = e.user_id
                WHERE e.user_id = ?
                GROUP BY c.id
                ORDER BY e.enrolled_at DESC
            ''', (current_user.id,))
            enrolled_courses = cursor.fetchall()
            
            # Get available courses (not enrolled)
            cursor.execute('''
                SELECT c.* FROM courses c
                WHERE c.id NOT IN (
                    SELECT course_id FROM enrollments WHERE user_id = ?
                )
                ORDER BY c.track, c.order_index
            ''', (current_user.id,))
            available_courses = cursor.fetchall()
            
        return render_template('dashboard.html', 
                             enrolled_courses=enrolled_courses,
                             available_courses=available_courses)
    
    @app.route('/enroll/<int:course_id>', methods=['POST'])
    @login_required
    def enroll_course(course_id):
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            
            # Check if already enrolled
            cursor.execute('SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?',
                         (current_user.id, course_id))
            if cursor.fetchone():
                flash('شما قبلاً در این دوره ثبت نام کرده‌اید', 'error')
                return redirect(url_for('dashboard'))
            
            # Enroll user
            cursor.execute('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
                         (current_user.id, course_id))
            
            # Get course info
            cursor.execute('SELECT title, total_modules FROM courses WHERE id = ?', (course_id,))
            course = cursor.fetchone()
            
            # Initialize progress for all modules
            for module_num in range(1, course[1] + 1):
                cursor.execute('''
                    INSERT INTO course_progress (user_id, course_id, module_number, completed)
                    VALUES (?, ?, ?, 0)
                ''', (current_user.id, course_id, module_num))
            
            conn.commit()
            flash(f'با موفقیت در دوره "{course[0]}" ثبت نام شدید!', 'success')
        
        return redirect(url_for('dashboard'))
    
    @app.route('/course/<int:course_id>')
    @login_required
    def course_detail(course_id):
        with sqlite3.connect(db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check enrollment
            cursor.execute('SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?',
                         (current_user.id, course_id))
            if not cursor.fetchone():
                flash('شما در این دوره ثبت نام نکرده‌اید', 'error')
                return redirect(url_for('dashboard'))
            
            # Get course info
            cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
            course = cursor.fetchone()
            
            # Get progress
            cursor.execute('''
                SELECT * FROM course_progress 
                WHERE user_id = ? AND course_id = ?
                ORDER BY module_number
            ''', (current_user.id, course_id))
            progress = cursor.fetchall()
            
        return render_template('course_detail.html', course=course, progress=progress)
    
    @app.route('/course/<int:course_id>/module/<int:module_num>/complete', methods=['POST'])
    @login_required
    def complete_module(course_id, module_num):
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            
            # Mark as complete
            cursor.execute('''
                UPDATE course_progress 
                SET completed = 1, completed_at = ?
                WHERE user_id = ? AND course_id = ? AND module_number = ?
            ''', (datetime.now(), current_user.id, course_id, module_num))
            conn.commit()
            
            flash(f'ماژول {module_num} تکمیل شد!', 'success')
        
        return redirect(url_for('course_detail', course_id=course_id))
    
    @app.route('/course/<int:course_id>/module/<int:module_num>/uncomplete', methods=['POST'])
    @login_required
    def uncomplete_module(course_id, module_num):
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            
            # Mark as incomplete
            cursor.execute('''
                UPDATE course_progress 
                SET completed = 0, completed_at = NULL
                WHERE user_id = ? AND course_id = ? AND module_number = ?
            ''', (current_user.id, course_id, module_num))
            conn.commit()
            
            flash(f'ماژول {module_num} به عنوان ناتمام علامت‌گذاری شد', 'success')
        
        return redirect(url_for('course_detail', course_id=course_id))
