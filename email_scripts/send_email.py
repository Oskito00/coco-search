#!/usr/bin/env python3
"""
Email Sender Script for CocoSearch

Usage:
  python send_email.py --to recipient@example.com --subject "Test Subject" --html email_template.html
  python send_email.py --to recipient@example.com --subject "Quick Message" --message "Hello, this is a plain text email."

Options:
  --to         Recipient email address
  --cc         CC recipient email address
  --subject    Email subject
  --html       Path to HTML template file
  --message    Plain text message (alternative to --html)
  --test       Send a test email to verify configuration
"""

import smtplib
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import sys
import os
from datetime import datetime
import socket
import ssl
from email.utils import formataddr

# SMTP Configuration - Update these with your details
SMTP_SERVER = "smtp.gmail.com"  # e.g., smtp.gmail.com
SMTP_PORT = 465  # Common ports: 25, 465, 587
SMTP_USERNAME = "oscar.alberigo@gmail.com"
SMTP_PASSWORD = "ubvx anwn zzum rvvl"
DEFAULT_SENDER = ('Coco', 'cocosearchhelp@gmail.com')
USE_TLS = False

# Set to True to see detailed connection information
DEBUG = True

def send_email(to_address, subject, html_content=None, text_content=None, cc_address=None):
    """Send an email with HTML and/or plain text content."""
    
    if not html_content and not text_content:
        print("Error: Either HTML or text content must be provided")
        return False
        
    try:
        # Create a simpler message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        
        # Format the sender properly with name and email
        sender_name, sender_email = DEFAULT_SENDER
        msg['From'] = formataddr((sender_name, sender_email))
        
        msg['To'] = to_address
        
        # Add CC if provided - handle multiple CC addresses
        if cc_address:
            if isinstance(cc_address, str) and ',' in cc_address:
                # Split comma-separated addresses
                cc_list = [addr.strip() for addr in cc_address.split(',')]
                msg['Cc'] = ', '.join(cc_list)
            else:
                msg['Cc'] = cc_address
        
        # Add content
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        if html_content:
            msg.attach(MIMEText(html_content, 'html'))
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect with SSL directly
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.set_debuglevel(DEBUG)
            # Still use SMTP_USERNAME/PASSWORD for authentication
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            
            # Define all recipients (to + cc)
            all_recipients = [to_address]
            if cc_address:
                if isinstance(cc_address, str) and ',' in cc_address:
                    # Handle comma-separated list
                    all_recipients.extend([addr.strip() for addr in cc_address.split(',')])
                elif isinstance(cc_address, list):
                    all_recipients.extend(cc_address)
                else:
                    all_recipients.append(cc_address)
            
            # Send mail using the formatted sender email address
            server.sendmail(
                from_addr=sender_email,  # Use the email from DEFAULT_SENDER
                to_addrs=all_recipients,  # To + CC addresses
                msg=msg.as_string()
            )
            
        print(f"Email sent successfully to {to_address}" + (f" with CC to {cc_address}" if cc_address else ""))
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        if isinstance(e, ConnectionRefusedError):
            print("Connection was refused. Possible causes:")
            print("1. Incorrect port number")
            print("2. SMTP server doesn't accept connections from your IP")
            print("3. Firewall is blocking outgoing connections")
        
        return False

def test_email(to_address):
    """Send a test email with diagnostic information."""
    
    html = f"""
    <html>
    <body>
        <h1>CocoSearch Email Test</h1>
        <p>This is a test email from the CocoSearch email sender script.</p>
        <p>If you're receiving this, your email configuration is working correctly!</p>
        <hr>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>SMTP Server:</strong> {SMTP_SERVER}</p>
        <p><strong>SMTP Port:</strong> {SMTP_PORT}</p>
        <p><strong>Use TLS:</strong> {USE_TLS}</p>
        <p><strong>Sender:</strong> {DEFAULT_SENDER}</p>
    </body>
    </html>
    """
    
    text = f"""
    CocoSearch Email Test
    
    This is a test email from the CocoSearch email sender script.
    If you're receiving this, your email configuration is working correctly!
    
    Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    SMTP Server: {SMTP_SERVER}
    SMTP Port: {SMTP_PORT}
    Use TLS: {USE_TLS}
    Sender: {DEFAULT_SENDER}
    """
    
    return send_email(to_address, "CocoSearch Email Test", html, text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send emails for CocoSearch')
    parser.add_argument('--to', help='Recipient email address', required=False)
    parser.add_argument('--cc', help='CC recipient email address(es) - can be comma-separated list')
    parser.add_argument('--subject', help='Email subject', required=False)
    parser.add_argument('--html', help='Path to HTML template file')
    parser.add_argument('--message', help='Plain text message')
    parser.add_argument('--test', action='store_true', help='Send a test email')
    
    args = parser.parse_args()
    
    # Test mode
    if args.test:
        if not args.to:
            print("Error: --to argument is required with --test")
            sys.exit(1)
        test_email(args.to)
        sys.exit(0)
    
    # Normal mode
    if not args.to or not args.subject:
        print("Error: --to and --subject arguments are required")
        sys.exit(1)
        
    html_content = None
    if args.html:
        try:
            html_path = Path(args.html)
            if html_path.exists():
                html_content = html_path.read_text(encoding='utf-8')
            else:
                print(f"Error: HTML file not found: {args.html}")
                sys.exit(1)
        except Exception as e:
            print(f"Error reading HTML file: {str(e)}")
            sys.exit(1)
            
    text_content = args.message
    
    if not html_content and not text_content:
        print("Error: Either --html or --message must be provided")
        sys.exit(1)
        
    success = send_email(args.to, args.subject, html_content, text_content, args.cc)
    sys.exit(0 if success else 1)