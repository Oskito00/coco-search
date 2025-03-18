from flask import Blueprint, jsonify, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import exists, func
from app.models import ItemRelevanceFeedback, Keyword, KeywordItems, UserQuery, UserQueryItems, db, Item, copy_item
from app.forms import QueryForm, DeleteForm  # Create this form if needed
from flask import current_app
from datetime import datetime, timezone
from app.utils.graph_helpers import get_query_price_data
from app.utils.price_helpers import remove_price_outliers
from app.utils.query_helpers import update_user_usage
from app.utils.text_helpers import item_matches_keywords
import numpy as np

bp = Blueprint('queries', __name__, url_prefix='/queries')

@bp.route('/manage')
@login_required
def manage_queries():
    print("Current user:", current_user)
    queries = UserQuery.query.options(db.joinedload(UserQuery.keyword))\
        .filter(UserQuery.user_id == current_user.id)\
        .order_by(UserQuery.created_at.desc())\
        .all()
    print("Queries found:", queries)
    total_queries = len(queries)
    active_queries = len([query for query in queries if query.is_active])
    all_active = active_queries == total_queries
    delete_form = DeleteForm()
    return render_template('queries/manage.html', queries=queries, delete_form=delete_form, all_active=all_active)

@bp.route('/edit_query/<string:query_id>', methods=['GET', 'POST'])
def edit_query(query_id):
    # Authentication check
    if not current_user.is_authenticated:
        flash('You need to be logged in to perform this action.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Fetch query with ownership check
    user_query = UserQuery.query.get_or_404(query_id)
    if user_query.user_id != current_user.id:
        abort(403)

    form = QueryForm(obj=user_query)
    
    # Pre-fill keyword if needed
    if request.method == 'GET':
        form.keywords.data = user_query.keyword.keyword_text

    if form.validate_on_submit():
        try:
            old_interval = user_query.check_interval
            new_interval = form.check_interval.data
            
            # Handle usage updates for interval changes
            if old_interval != new_interval:
                # Remove old usage
                if not update_user_usage(current_user, old_interval, 'remove'):
                    raise ValueError("Could not remove old interval usage")
                
                # Add new usage
                if not update_user_usage(current_user, new_interval, 'add'):
                    # Rollback usage change if limit exceeded
                    update_user_usage(current_user, old_interval, 'add')
                    raise ValueError("This interval would exceed your daily limit")
    
        
            if form.required_keywords.data != user_query.required_keywords or form.excluded_keywords.data != user_query.excluded_keywords:

                # 1. Remove non-matching items
                query_items = UserQueryItems.query.filter_by(query_id=query_id).all()
                deletions = [
                    qi for qi in query_items
                    if not item_matches_keywords(qi.item, form.required_keywords.data, form.excluded_keywords.data)
                ]
            
                # 2. Find new items to add (that match both keyword and new filters)
                # Get the keyword_id from the user's original query
                keyword_id = user_query.keyword_id

                # Subquery to find items already linked to this query
                existing_item_ids = db.session.query(UserQueryItems.item_id)\
                    .filter(UserQueryItems.query_id == query_id)\
                    .subquery()

                # Get potential items that match the keyword but aren't linked yet
                potential_items = db.session.query(Item)\
                    .join(KeywordItems, Item.item_id == KeywordItems.item_id)\
                    .outerjoin(
                        ItemRelevanceFeedback,
                        (ItemRelevanceFeedback.item_id == Item.item_id) &
                        (ItemRelevanceFeedback.user_id == current_user.id) &
                        (ItemRelevanceFeedback.keyword_id == keyword_id)
                    )\
                    .filter(
                        KeywordItems.keyword_id == keyword_id,
                        ~Item.item_id.in_(existing_item_ids),
                        # Exclude items marked as irrelevant
                        db.or_(
                            ItemRelevanceFeedback.is_relevant.is_(None),
                            ItemRelevanceFeedback.is_relevant.is_(True)
                        )
                    )\
                    .all()
                print(f"Potential items: {len(potential_items)}")

                additions = [
                    UserQueryItems(query_id=query_id, item_id=item.item_id)
                    for item in potential_items
                    if item_matches_keywords(
                        item,
                        form.required_keywords.data,
                        form.excluded_keywords.data
                    )
                ]

                # 3. Batch process changes
                for qi in deletions:
                    db.session.delete(qi)
            
                for qi in additions:
                    db.session.add(qi)

                db.session.commit()
            
            # Update query fields
            form.populate_obj(user_query)
            user_query.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            flash('Query updated successfully', 'success')
            return redirect(url_for('queries.manage_queries'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Query update failed: {str(e)}")
            flash(f'Error updating query: {str(e)}', 'danger')

    return render_template('queries/edit.html', form=form, query=user_query)

@bp.route('/delete_query/<string:query_id>', methods=['POST'])
def delete_query(query_id):
    # Authentication check
    if not current_user.is_authenticated:
        flash('You need to be logged in to perform this action.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Fetch query with ownership check
    user_query = UserQuery.query.get_or_404(query_id)
    if user_query.user_id != current_user.id:
        abort(403)

    try:
        # Store interval for usage update
        old_interval = user_query.check_interval
        
        # Delete associations and query
        UserQueryItems.query.filter_by(query_id=query_id).delete()
        db.session.delete(user_query)
        
        # Update user usage before commit
        if not update_user_usage(current_user, old_interval, 'remove'):
            raise ValueError("Usage update failed during deletion")
            
        db.session.commit()
        flash('Query deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Query deletion failed: {str(e)}")
        flash(f'Error deleting query: {str(e)}', 'danger')

    return redirect(url_for('queries.manage_queries'))

@bp.route('/create_query', methods=['GET', 'POST'])
def create_query():
    print("Current user authenticated:", current_user.is_authenticated)
    form = QueryForm()
    if request.method == 'GET':
        form.check_interval.data = 5  # Default to 5 minutes
    if form.validate_on_submit():
        try:

            # Update the user's query usage based on their query
            try:
                if not update_user_usage(current_user, form.check_interval.data, 'add'):
                    flash('This query would exceed your daily limit', 'danger')
                    return render_template('queries/create.html', form=form)
                
            except ValueError as e:
                db.session.rollback()
                flash(str(e), 'danger')
                return render_template('queries/create.html', form=form)
            
            # Check if keyword exists (case-insensitive)
            existing = Keyword.query.filter(
                db.func.lower(Keyword.keyword_text) == db.func.lower(form.keywords.data.strip())
            ).first()
            
            keyword_id = None
            if form.keywords.data.strip():  # Prevent empty strings
                if not existing:
                    new_keyword = Keyword(keyword_text=form.keywords.data.strip())
                    db.session.add(new_keyword)
                    db.session.commit()  # Need to commit to get the ID
                    keyword_id = new_keyword.keyword_id
                else:
                    keyword_id = existing.keyword_id
                
                # Prevent duplicate queries
                existing_query = UserQuery.query.filter(
                    UserQuery.user_id == current_user.id,
                    UserQuery.keyword_id == keyword_id
                ).first()
                
                if existing_query:
                    flash('You already have a query with this keyword', 'danger')
                    return render_template('queries/create.html', form=form)
                
                # Proceed with query creation
                new_user_query = UserQuery()
                form.populate_obj(new_user_query)
                new_user_query.user_id = current_user.id
                new_user_query.keyword_id = keyword_id
                new_user_query.created_at = datetime.now(timezone.utc)
                new_user_query.is_active = True
                
                db.session.add(new_user_query)
                db.session.commit()
            
            #Load historical data if exists
            historical_items = KeywordItems.query.filter_by(keyword_id=keyword_id).all()
            count = 0
            for keyword_item in historical_items:
                feedback = ItemRelevanceFeedback.query.filter_by(user_id=current_user.id, item_id=keyword_item.item_id, keyword_id=keyword_id).first()
                if feedback:
                    if feedback.is_relevant == False:
                        continue
                # Create association unless the unless the user has marked the item as irrelevant
                user_query_item = UserQueryItems(
                    query_id=new_user_query.query_id,
                    item_id=keyword_item.item_id,
                    auction_ending_notification_sent=False
                )
                db.session.add(user_query_item)
                count += 1
            
            if count > 0:
                db.session.commit()
                print(f"Loaded {count} historical items")
            
            return redirect(url_for('queries.manage_queries'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Query creation failed: {str(e)}")
            flash('Error creating query: ' + str(e), 'danger')
    else:
        print("Form not validated. Errors:", form.errors)
    return render_template('queries/create.html', form=form) 

@bp.route('/queries/toggle_all', methods=['POST'])
@login_required
def toggle_all_queries():
    print("Toggling all queries")
    new_state = not UserQuery.query.filter_by(user_id=current_user.id, is_active=True).count() > 0
    for query in UserQuery.query.filter_by(user_id=current_user.id).all():
        if query.is_active != new_state:
            operation = 'add' if new_state else 'remove'
            try:
                update_user_usage(current_user, query.check_interval, operation)
                query.is_active = new_state
            except ValueError as e:
                db.session.rollback()
                flash(str(e), 'danger')
                return redirect(url_for('queries.manage_queries'))
    db.session.commit()
    return redirect(url_for('queries.manage_queries'))

@bp.route('/<string:query_id>/toggle', methods=['POST'])
@login_required
def toggle_query(query_id):
    query = UserQuery.query.get_or_404(query_id)
    if query.user_id != current_user.id:
        abort(403)
    
    operation = 'remove' if query.is_active else 'add'
    try:
        update_user_usage(current_user, query.check_interval, operation)
        query.is_active = not query.is_active
        db.session.commit()
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('queries.manage_queries'))
    
    return redirect(url_for('queries.manage_queries'))


@bp.route('/<string:query_id>')
@login_required
def query_details(query_id):
    query = UserQuery.query.filter_by(user_id=current_user.id, query_id=query_id).first_or_404()
    
    # Get ALL items for accurate stats
    all_items = UserQueryItems.query\
                         .filter_by(query_id=query_id)\
                         .order_by(UserQueryItems.created_at.desc())\
                         .all()

    # Remove outliers using IQR method
    filtered_items, _ = remove_price_outliers(all_items)
    
    # Calculate stats using filtered items
    stats = {
        'total_items': len(filtered_items),
        'avg_price': np.mean([item.item.price for item in filtered_items]) if filtered_items else 0
    }
    
    # Only show first 100 items
    visible_items = filtered_items[:100]

    price_data = get_query_price_data(query_id)

    return render_template('queries/details.html', 
                         query=query, 
                         items=visible_items,
                         stats=stats,
                         price_data=price_data
                         )


@bp.route('/feedback/<string:query_id>/<int:item_id>', methods=['POST'])
@login_required
def submit_feedback(query_id, item_id):
    user_query_item = UserQueryItems.query.get_or_404((query_id, item_id))
    
    if user_query_item.user_query.user_id != current_user.id:
        abort(403)
    
    feedback = request.form.get('feedback')
    if feedback not in ['relevant', 'irrelevant']:
        abort(400)
    
    # Handle feedback recording
    feedback_entry = ItemRelevanceFeedback.query.filter_by(
        user_id=current_user.id,
        item_id=user_query_item.item_id,
        keyword_id=user_query_item.user_query.keyword_id
    ).first()

    if feedback_entry:
        print("Required keywords:", user_query_item.user_query.required_keywords)
        print("Excluded keywords:", user_query_item.user_query.excluded_keywords)
        feedback_entry.is_relevant = (feedback == 'relevant')
        feedback_entry.required_keywords = user_query_item.user_query.required_keywords
        feedback_entry.excluded_keywords = user_query_item.user_query.excluded_keywords
    else:
        print("required_keywords:", user_query_item.user_query.required_keywords)
        print("excluded_keywords:", user_query_item.user_query.excluded_keywords)
        feedback_entry = ItemRelevanceFeedback(
            user_id=current_user.id,
            item_id=user_query_item.item_id,
            keyword_id=user_query_item.user_query.keyword_id,
            required_keywords=user_query_item.user_query.required_keywords,
            excluded_keywords=user_query_item.user_query.excluded_keywords,
            is_relevant=(feedback == 'relevant'),
            created_at=datetime.utcnow()
        )
        db.session.add(feedback_entry)

    if feedback == 'irrelevant':
        ordered_items = UserQueryItems.query.filter_by(query_id=query_id)\
                            .order_by(UserQueryItems.created_at.asc()).all()
        item_ids = [str(item.item_id) for item in ordered_items]
        
        try:
            current_idx = item_ids.index(str(item_id))
            prev_item_id = item_ids[current_idx - 1] if current_idx > 0 else None
        except ValueError:
            prev_item_id = None

        db.session.delete(user_query_item)
        db.session.commit()

        # Handle no previous item case
        if not prev_item_id:
            return redirect(url_for('queries.query_details', query_id=query_id))
            
        return redirect(url_for('queries.query_details', query_id=query_id) + f"#item-{prev_item_id}")

    db.session.commit()
    return redirect(url_for('queries.query_details', query_id=query_id) + f"#item-{item_id}")
