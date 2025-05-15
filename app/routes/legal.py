from flask import Blueprint, render_template

legal_bp = Blueprint('legal', __name__)

@legal_bp.route('/terms')
def terms_of_use():
    return render_template('legal/terms_of_use.html')

@legal_bp.route('/privacy')
def privacy_policy():
    """Route for future privacy policy page"""
    return render_template('legal/privacy_policy.html')