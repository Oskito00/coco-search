
from flask import current_app
from flask_mail import Message
from app.extensions import mail

def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(msg)

def send_password_reset_email(to, template):
    msg = Message(
        'Password Reset Request',
        recipients=[to],
        html = template,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(msg)