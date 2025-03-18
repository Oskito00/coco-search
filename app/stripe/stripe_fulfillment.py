from datetime import datetime, timedelta
import stripe
from flask import current_app
from app.ebay import constants
from app.models import User
from app.extensions import db
from app.utils.email import notify_user
from app.utils.query_helpers import pause_queries_exceeding_limit

#User buys new subscription

def handle_new_subscription(event):
    subscription = event['data']['object']
    print("Subscription customer: ", subscription['customer'])
    user = User.query.filter_by(
        stripe_customer_id=subscription['customer']
    ).first()
    print("User found: ", user)
    
    if not user:
        print("No user found for subscription")
        # Create user from subscription info
        customer = stripe.Customer.retrieve(subscription['customer'])
        user = User(
            email=customer.email,
            stripe_customer_id=customer.id
        )
        db.session.add(user)
    
    user.stripe_subscription_id = subscription['id']
    print("Subscription ID: ", subscription['id'])
    user.tier = get_tier_from_price(subscription['items']['data'][0]['price']['id'])
    user.subscription_status = 'active'
    user.current_period_end = datetime.fromtimestamp(
        subscription['current_period_end']
    )
    db.session.commit()

  # User updates their subscription

def handle_subscription_updated(event):
    sub = event['data']['object']
    prev = event['data'].get('previous_attributes', {})
    
    # 1. Handle Cancellation Requests
    if 'cancel_at_period_end' in prev and sub.cancel_at_period_end:
        user = User.query.filter_by(
            stripe_customer_id=sub.customer
        ).first()
        if user:
            user.subscription_status = 'pending_cancellation'
            user.current_period_end = datetime.fromtimestamp(
                sub.current_period_end
            )
            db.session.commit()
    
    # 2. Handle Price Changes
    if 'items' in prev:
        current_price = sub['items']['data'][0]['price']['id']
        previous_price = prev['items']['data'][0]['price']['id']

        # Store previous price in metadata
        stripe.Subscription.modify(
            sub['id'],
            metadata={'previous_price': previous_price}
        )

        if current_price != previous_price:
            user = User.query.filter_by(
                stripe_customer_id=sub.customer
            ).first()
            if user:
                # Immediate upgrade
                if is_upgrade(current_price, previous_price):
                  user.tier = get_tier_from_price(current_price) #Assume payment is successful and revert in payment failed handler
                  user.pending_tier = None  # Clear any pending downgrade
                if is_downgrade(current_price, previous_price):
                  user.pending_tier = get_tier_from_price(current_price)
                  user.pending_effective_date = datetime.fromtimestamp(
                  sub.current_period_end
                )
                  db.session.commit()
    
    # 3. Handle Downgrade Completion
    if 'billing_cycle_anchor' in prev and sub.billing_cycle_anchor == 'unchanged':
        user = User.query.filter_by(
            stripe_customer_id=sub.customer
        ).first()
        if user and user.pending_tier:
            user.tier = user.pending_tier
            user.pending_tier = None
            user.pending_effective_date = None
            pause_queries_exceeding_limit(user)
            db.session.commit()

    # 4. Handle Canceled Downgrade via Metadata
    if sub.metadata.get('cancel_downgrade') == 'True':
        user = User.query.filter_by(
            stripe_customer_id=sub.customer
        ).first()
        if user:
            user.pending_tier = None
            user.pending_effective_date = None
            db.session.commit()
            # Clear metadata to prevent reprocessing
            stripe.Subscription.modify(
                sub.id,
                metadata={'cancel_downgrade': None}
            )

#The subscription expires and is deleted

def handle_subscription_deleted(event):
    try:
        sub = event['data']['object']
        customer_id = sub['customer']  # Access as dictionary
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if not user:
            current_app.logger.error(f"User not found for customer {customer_id}")
            return
        
        user.subscription_status = 'canceled'
        user.tier = {'name': 'free', 'query_limit': 0}
        user.current_period_end = None
        user.cancellation_requested = False
        
        # Handle query pausing
        pause_queries_exceeding_limit(user)
        
        db.session.commit()
        current_app.logger.info(f"Canceled subscription for user {user.id}")
        
    except Exception as e:
        current_app.logger.error(f"Subscription deletion error: {str(e)}")
        raise  # Re-raise to trigger 500 response

def get_or_create_user(checkout_session):
  """Find or create user based on checkout session"""
  user = User.query.filter_by(
        stripe_customer_id=checkout_session.customer
    ).first()
    
  if not user:
      user = User(
            email=checkout_session.customer_details.email,
            stripe_customer_id=checkout_session.customer
        )
      db.session.add(user)
      db.session.commit()
    
  return user

#Payments

def handle_invoice_paid(event):
    invoice = event['data']['object']
    sub = stripe.Subscription.retrieve(invoice.subscription)
    
    user = User.query.filter_by(
        stripe_subscription_id=sub.id
    ).first()
    
    if not user:
        return
    
    # Renewal Cycle
    if invoice.billing_reason == 'subscription_cycle':
        # Apply pending downgrade
        if user.pending_tier:
            user.tier = user.pending_tier
            user.pending_tier = None
            user.pending_effective_date = None
            pause_queries_exceeding_limit(user)
        # Update period end
        user.current_period_end = datetime.fromtimestamp(
            sub.current_period_end
        )
    
    # Immediate Upgrade (already handled)
    elif invoice.billing_reason == 'subscription_update':
        pass  # Existing logic
    
    db.session.commit()

def handle_invoice_payment_failed(event):
    try:
        invoice = event['data']['object']
        sub = stripe.Subscription.retrieve(invoice['subscription'])
        user = User.query.filter_by(stripe_subscription_id=sub.id).first()

        if not user:
            return

        attempt_count = invoice.get('attempt_count', 1)
        max_attempts = 3  # Stripe's default retry count
        
        # Store first failure timestamp
        if attempt_count == 1:
            user.payment_failure_start = datetime.utcnow()
            db.session.commit()

        # Check retry status
        if attempt_count < max_attempts:
            # In grace period - maintain access
            user.grace_period_end = datetime.utcnow() + timedelta(days=3)
            message = f"Hi, {user.email}, just to let you know that your payment for your subscription has failed (attempt {attempt_count}/{max_attempts}). Please update payment method to ensure you don't lose access to your premium features."
            notify_user(user, message)
            return  # Don't downgrade yet
            
        # Final failure handling
        previous_price = sub.metadata.get('previous_price')
        current_price = sub['items']['data'][0]['price']['id']

        if previous_price and is_upgrade(current_price, previous_price):
            user.tier = get_tier_from_price(previous_price)
            message = f"Hi, {user.email}, your subscription upgrade failed after {max_attempts} attempts. Reverted to previous tier."
        else:
            user.tier = {'name': 'free', 'query_limit': 0}
            user.subscription_status = 'canceled'
            message = f"Hi, {user.email}, your subscription was canceled after {max_attempts} failed payment attempts. Downgraded to free tier."

        # Clear payment fields
        user.pending_tier = None
        user.pending_effective_date = None
        user.grace_period_end = None
        user.payment_failure_start = None
        
        pause_queries_exceeding_limit(user)
        db.session.commit()
        notify_user(user, message)
        
    except Exception as e:
        current_app.logger.error(f"Payment failure error: {str(e)}")
        raise
#HELPER FUNCTIONS

def get_tier_from_price(price_id):
    """Get tier data from price ID"""
    for price_key, tier_data in constants.PRICE_TIER_MAPPINGS.items():
        if price_key == price_id:
            return tier_data
    return {'name': 'free', 'query_limit': 100}  # Default tier

def get_price_id_from_tier(tier_name):
    """Get price ID from tier name"""
    for price_key, tier_data in constants.PRICE_TIER_MAPPINGS.items():
        if tier_data['name'] == tier_name:
            return price_key
    return None

def is_upgrade(new_price_id, old_price_id):
    """Check if new price is higher tier"""
    new_tier = get_tier_from_price(new_price_id)
    old_tier = get_tier_from_price(old_price_id)
    
    tier_order = ['free', 'individual', 'business', 'pro']
    return tier_order.index(new_tier['name']) > tier_order.index(old_tier['name'])

def is_downgrade(new_price_id, old_price_id):
    """Check if new price is lower tier"""
    new_tier = get_tier_from_price(new_price_id)
    old_tier = get_tier_from_price(old_price_id)
    
    tier_order = ['free', 'individual', 'business', 'pro']
    return tier_order.index(new_tier['name']) < tier_order.index(old_tier['name'])