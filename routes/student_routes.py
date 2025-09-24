from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from myextensions import db
from models import Student, Event, FeedbackResponse, Course, Staff, Question, QuestionResponse, GeneralFeedback

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        password = request.form.get('password')
        if not roll_number.startswith('718123') or len(roll_number) != 11 or not roll_number.isdigit():
            flash("Invalid roll number format", "danger")
            return redirect(url_for('student.login'))
        student = Student.query.filter_by(roll_number=roll_number).first()
        if student and student.check_password(password):
            session['student_id'] = student.id
            flash("Logged in successfully", "success")
            return redirect(url_for('student.dashboard'))
        else:
            flash("Invalid credentials", "danger")
    return render_template('student/login.html')

@student_bp.route('/logout')
def logout():
    session.pop('student_id', None)
    flash("Logged out successfully", "success")
    return redirect(url_for('student.login'))

@student_bp.route('/dashboard')
def dashboard():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('student.login'))
    student = Student.query.get_or_404(student_id)
    try:
        active_event = Event.query.filter_by(is_active=True, is_deleted=False).first()
    except Exception:
        active_event = Event.query.filter_by(is_active=True).first()
    # Restrict event access by roll number
    event_blocked = False
    warning_message = None
    if active_event and not active_event.is_open_to_all:
        if not (active_event.start_roll_number and active_event.end_roll_number):
            event_blocked = True
            warning_message = active_event.warning_message or "This event is not open to your roll number."
        elif not (active_event.start_roll_number <= student.roll_number <= active_event.end_roll_number):
            event_blocked = True
            warning_message = active_event.warning_message or "This event is not open to your roll number."
    has_submitted = False
    if active_event:
        existing_feedback = FeedbackResponse.query.filter_by(student_id=student_id, event_id=active_event.id).first()
        if existing_feedback:
            has_submitted = True
    return render_template('student/dashboard.html', 
                           student=student,
                           active_event=active_event,
                           has_submitted=has_submitted,
                           event_blocked=event_blocked,
                           warning_message=warning_message)

@student_bp.route('/general-feedback')
def general_feedback_dashboard():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('student.login'))
    
    student = Student.query.get_or_404(student_id)
    
    # Get student's feedback history
    feedback_history = GeneralFeedback.query.filter_by(student_id=student_id).order_by(GeneralFeedback.timestamp.desc()).all()
    
    return render_template('student/general_feedback_dashboard.html', 
                         student=student,
                         feedback_history=feedback_history)

@student_bp.route('/submit-feedback/<category>', methods=['GET', 'POST'])
def submit_feedback(category):
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('student.login'))
    
    student = Student.query.get_or_404(student_id)
    
    valid_categories = ['fc', 'library', 'transport', 'sports', 'bookdepot', 'general']
    if category not in valid_categories:
        flash('Invalid feedback category', 'danger')
        return redirect(url_for('student.general_feedback_dashboard'))
    
    category_names = {
        'fc': 'Food Court',
        'library': 'Library',
        'transport': 'Transport',
        'sports': 'Sports',
        'bookdepot': 'Book Depot',
        'general': 'General'
    }
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('Please provide your feedback before submitting.', 'warning')
            return render_template('student/submit_feedback.html', 
                                 category=category,
                                 category_name=category_names[category],
                                 student=student)
        
        feedback = GeneralFeedback(
            category=category,
            content=content,
            student_id=student_id
        )
        db.session.add(feedback)
        db.session.commit()
        
        flash('Your feedback has been submitted successfully!', 'success')
        return redirect(url_for('student.general_feedback_dashboard'))
    
    return render_template('student/submit_feedback.html', 
                         category=category,
                         category_name=category_names[category],
                         student=student)

@student_bp.route('/feedback', methods=['GET', 'POST'])
def feedback_form():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('student.login'))
    student = Student.query.get_or_404(student_id)
    try:
        active_event = Event.query.filter_by(is_active=True, is_deleted=False).first()
    except Exception:
        active_event = Event.query.filter_by(is_active=True).first()
    # Restrict event access by roll number
    if active_event and not active_event.is_open_to_all:
        if not (active_event.start_roll_number and active_event.end_roll_number):
            flash(active_event.warning_message or "This event is not open to your roll number.", "warning")
            return redirect(url_for('student.dashboard'))
        elif not (active_event.start_roll_number <= student.roll_number <= active_event.end_roll_number):
            flash(active_event.warning_message or "This event is not open to your roll number.", "warning")
            return redirect(url_for('student.dashboard'))
    if not active_event:
        flash('No active feedback event available', 'warning')
        return redirect(url_for('student.dashboard'))
    existing_feedback = FeedbackResponse.query.filter_by(student_id=student_id, event_id=active_event.id).first()
    if existing_feedback:
        flash('You have already submitted feedback for this event', 'warning')
        return redirect(url_for('student.dashboard'))
    if request.method == 'POST':
        courses_data = {}
        courses = active_event.courses
        for course in courses:
            staff_selected = request.form.get(f"staff_{course.id}")
            if staff_selected:
                courses_data[course.id] = {int(staff_selected): {}}
        for key, value in request.form.items():
            if key.startswith('rating_'):
                parts = key.split('_')
                if len(parts) == 4:
                    course_id = int(parts[1])
                    staff_id = list(courses_data.get(course_id, {}).keys())[0] if course_id in courses_data else None
                    question_id = int(parts[3])
                    rating = int(value)
                    if course_id in courses_data and staff_id:
                        courses_data[course_id][staff_id][question_id] = rating
        for course_id, staffs in courses_data.items():
            for staff_id, questions in staffs.items():
                feedback = FeedbackResponse(student_id=student_id,
                                            event_id=active_event.id,
                                            course_id=course_id,
                                            staff_id=staff_id)
                db.session.add(feedback)
                db.session.flush()
                for question_id, rating in questions.items():
                    qr = QuestionResponse(feedback_id=feedback.id,
                                          question_id=question_id,
                                          rating=rating)
                    db.session.add(qr)
        db.session.commit()
        flash('Feedback submitted successfully', 'success')
        return redirect(url_for('student.thank_you'))
    courses = active_event.courses
    questions = Question.query.all()
    course_staffs = {}
    for course in courses:
        course_staffs[course.id] = Staff.query.filter_by(course_id=course.id).all()
    return render_template('student/feedback_form.html',
                           student=student,
                           event=active_event,
                           courses=courses,
                           questions=questions,
                           course_staffs=course_staffs)

@student_bp.route('/thank-you')
def thank_you():
    if not session.get('student_id'):
        return redirect(url_for('student.login'))
    return render_template('student/thank_you.html')