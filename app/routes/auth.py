from datetime import datetime, timedelta
from flask import Blueprint, app, current_app, render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user, login_required
from markupsafe import Markup
from app.models import User
from app.forms import ForgotPasswordForm, LoginForm, RegistrationForm, ResetPasswordForm
from app import db
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import limiter


from app.utils.email import send_email, send_password_reset_email
from app.utils.token import confirm_token, generate_confirmation_token

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    print("User pressed login button")
    form = LoginForm()
    print("Form data:", form.data)
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        print("User found:", user)
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('auth.login'))
        if not user.email_verified:
            resend_url = url_for('auth.resend_verification', email=user.email)
            flash(Markup(f'Please verify your email first. <a href="{resend_url}">Resend verification email</a>'), 'danger')
            return redirect(url_for('auth.login'))
        if not user.check_password(form.password.data):
            flash('Invalid password', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user)
        print(f"User logged in: {user.email}")
        flash('Logged in successfully!', 'success')
        return redirect(url_for('queries.manage_queries'))
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            print("User already exists")
            flash('This email is already registered. Please use a different email.', 'danger')
            return render_template('auth/register.html', form=form)
        try:
            user = User(email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            token = generate_confirmation_token(user.email)
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            html = render_template('auth/email_template.html', confirm_url=confirm_url)
            send_email(user.email, 'Please confirm your email', html)
            print("Token generated:", token)
            flash('A confirmation email has been sent via email.', 'info')
            return redirect(url_for('auth.login'))
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"DB commit failed: {str(e)}")
            flash('Registration failed', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.resend_confirmation'))
    user = User.query.filter_by(email=email).first_or_404()
    if user.email_verified:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.email_verified = True
        user.email_verified_on = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        flash('You have verified your email. Thanks!', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/resend-verification/<email>')
@limiter.limit("3/hour", error_message="Too many resend attempts")
def resend_verification(email):
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('auth.login'))
    
    if user.email_verified:
        flash('Email already verified', 'info')
        return redirect(url_for('main.index'))
    
    try:
        token = generate_confirmation_token(user.email)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        html = render_template('auth/email_template.html', confirm_url=confirm_url)
        send_email(user.email, 'Please confirm your email', html)
        flash('Verification email resent - check your inbox', 'success')
    except Exception as e:
        current_app.logger.error(f"Resend failed: {str(e)}")
        flash('Error resending verification email', 'danger')
    
    return redirect(url_for('auth.login'))

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    print("Forgot password button pressed")
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        print("User email:", form.email.data)
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_confirmation_token(user.email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            html = render_template('auth/forgot_password_email.html', reset_url=reset_url)
            try:
                send_password_reset_email(user.email, html)
            except Exception as e:
                current_app.logger.error(f"Error sending password reset email: {str(e)}")
                flash('Error sending password reset email', 'danger')
        flash('If that email exists, a password reset link has been sent', 'info')

    return render_template('auth/forgot_password.html', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = confirm_token(token)
    except:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password updated successfully', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index')) 

