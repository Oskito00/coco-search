from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app import db

from app.models import Feedback


bp = Blueprint('contact_feedback', __name__, url_prefix='/contact_feedback')

@bp.route('/')
def contact_feedback():
    return render_template('contact_feedback.html')


@bp.route('/submit-feedback', methods=['POST'])
@login_required
def submit_feedback():
    print("submit feedback button pressed")
    try:
        feedback = Feedback(
            user_id=current_user.id,
            email=request.form.get('email'),
            rating=request.form.get('rating'),
            message=request.form.get('message'),
            feedback_type='general'
        )
        
        # Validate required fields
        if not feedback.message:
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('contact_feedback'))
            
        db.session.add(feedback)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error submitting feedback. Please try again.', 'error')
    
    return redirect(url_for('contact_feedback.contact_feedback'))