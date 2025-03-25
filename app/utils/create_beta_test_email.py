from app.utils.email import send_email


def create_beta_welcome_email(name, email, test_email, test_password):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Welcome to Beta Testing!</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <!-- Header -->
            <div style="text-align: center; padding: 20px 0;">
            </div>

            <!-- Content -->
            <div style="background-color: #f7f7f7; padding: 30px; border-radius: 10px;">
                <h1 style="color: #333333; margin-top: 0;">Welcome to the Beta, {name}! 🚀</h1>
                
                <p style="color: #666666;">We would love to invite you to join our beta testing program! Below are your temporary credentials to access the testing environment:</p>
                
                <!-- Credentials Box -->
                <div style="background-color: #ffffff; padding: 20px; border-radius: 8px; margin: 25px 0;">
                    <p style="margin: 5px 0;">
                        <strong>Test Environment URL:</strong> 
                        <a href="https://ebaychecker-5222ac845812.herokuapp.com/" style="color: #007bff;">https://ebaychecker-5222ac845812.herokuapp.com/</a>
                    </p>
                    <p style="margin: 5px 0;">
                        <strong>Test Email:</strong> 
                        <code style="background-color: #f0f0f0; padding: 2px 5px; border-radius: 3px;">{test_email}</code>
                    </p>
                    <p style="margin: 5px 0;">
                        <strong>Test Password:</strong> 
                        <code style="background-color: #f0f0f0; padding: 2px 5px; border-radius: 3px;">{test_password}</code>
                    </p>
                </div>

                <p style="color: #666666;">Here's how to get started:</p>
                <ol style="color: #666666;">
                    <li>Log in using the credentials above</li>
                    <li>Explore the new features</li>
                    <li>Report any issues via the in-app feedback button</li>
                    <li>Check your email ({email}) for daily updates</li>
                </ol>

                <!-- Login Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://ebaychecker-5222ac845812.herokuapp.com/" 
                       style="background-color: #28a745; 
                              color: #ffffff; 
                              padding: 12px 30px;
                              border-radius: 5px;
                              text-decoration: none;
                              display: inline-block;
                              font-weight: bold;">
                        Launch Beta Environment
                    </a>
                </div>

                <!-- Security Note -->
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 25px;">
                </div>
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding: 20px; color: #999999; font-size: 12px;">
                <p>© 2025 EbayChecker. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return {
        "to": email,
        "subject": f"🚀 Welcome to the Beta Program, {name}!",
        "html": html_content
    }



