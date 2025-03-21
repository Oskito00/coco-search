from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models import Item, ItemRelevanceFeedback, Keyword, KeywordItems, User, UserQuery, UserQueryItems
from app.utils.levenshtein_string_similarity_helper import calculate_relevance_score
from app.utils.notifications import NotificationManager
from app.utils.scraper import scrape_ebay, scrape_new_items
from sqlalchemy import inspect
from app.extensions import scheduler

def full_scrape_job(query_id):
    print(f"FULL_SCRAPE_JOB: Query ID: {query_id}")
    with scheduler.app.app_context():
        session = db.session()
        try:
            with session.begin():
                # Get the user query from the query_id
                query = UserQuery.query.get(query_id)
                if not query or not query.is_active:
                    scheduler.app.logger.debug(f"[Job {query_id}] Aborting - no active query")
                    return

            # Get the keywords based on the query keyword_id
            keywords = Keyword.query.get(query.keyword_id)
            
            # Call scrape ebay with the right filters
            items = scrape_ebay(
                keywords.keyword_text,
                filters={
                    'min_price': query.min_price,
                    'max_price': query.max_price,
                    'item_location': query.item_location,
                    'condition': query.condition,
                    'buying_options': query.buying_options
                },
                required_keywords=query.required_keywords,
                excluded_keywords=query.excluded_keywords,
                marketplace=query.marketplace
            )

            # Process items based on first_run status
            if query.first_run:
                process_items(items, query, full_scan=True, notify=True, first_run=True)
                query.first_run = False
            else:
                process_items(items, query, full_scan=True, notify=True, first_run=False)
            
            # Update query timestamps
            query.last_full_run = datetime.now(timezone.utc)
            query.next_full_run = datetime.now(timezone.utc) + timedelta(hours=24)
            db.session.commit()
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            session.close()
            db.session.remove()

def recent_scrape_job(query_id):
    print(f"RECENT_SCRAPE_JOB: Query ID: {query_id}")
    with scheduler.app.app_context():
        try:
            session = db.session
            with session.begin():
                query = UserQuery.query.get(query_id)
                print(f"[Job {query_id}] Query: {query}")
                if not query or not query.is_active:
                    print(f"[Job {query_id}] Aborting - no active query")
                    return
            try:
                keywords = Keyword.query.get(query.keyword_id)
                new_items = scrape_new_items(
                    keywords.keyword_text,
                    filters={'min_price': query.min_price, 'max_price': query.max_price, 'item_location': query.item_location,'condition': query.condition, 'buying_options': query.buying_options},
                    required_keywords=query.required_keywords,
                    excluded_keywords=query.excluded_keywords,
                    marketplace=query.marketplace
                )
                process_items(new_items, query, check_existing=False, notify=True)
                query.last_recent_run = datetime.now(timezone.utc)
                db.session.commit()
            except Exception as e:
                print(f"Recent scrape failed: {e}")
        except Exception as e:
            print(f"Error: {e}")

def process_items(items, query, check_existing=False, full_scan=False, notify=True, first_run=False):
    print(f"[Process Items] Starting processing for query {query.query_id}")

    # Lists to store new items, updated items, price drops, and ending auctions
    new_items = []
    updated_items = []
    price_drops = []
    ending_auctions = []
    item_columns = {c.key for c in inspect(Item).mapper.column_attrs}

    # Extract the keyword (text) from the query
    keyword = query.keyword
    current_time = datetime.now(timezone.utc)
    # Loop through all the items found
    for idx, item_data in enumerate(items):
        # If an item with the same ebay_id exists, get it
        existing = Item.query.filter_by(ebay_id=item_data['ebay_id']).first()
        if existing:
            feedback = ItemRelevanceFeedback.query.filter_by(
                user_id=query.user_id,
                item_id=existing.item_id,
                keyword_id=keyword.keyword_id
            ).one_or_none()
            if feedback:
                print(f"Is relevant: {feedback.is_relevant}")
            else:
                feedback = None
                print(f"No feedback found")
        if first_run:
            if existing:
                # Check if the item is already linked to this keyword, if not add the link
                if not KeywordItems.query.filter_by(keyword_id=keyword.keyword_id, item_id=existing.item_id).first():
                    print(f"[Process Items] Linking existing item {existing.item_id} to keyword {keyword.keyword_text}")
                    print(f"existing market: {existing.marketplace}")
                    print(f"existing country: {existing.location_country}")
                    db.session.add(KeywordItems(keyword_id=keyword.keyword_id, item_id=existing.item_id))
                # Check if the item is already linked to the query
                if not UserQueryItems.query.filter_by(query_id=query.query_id, item_id=existing.item_id).first():
                    if feedback and feedback.is_relevant is False:
                        #If the item has already been marked as irrelevant for this keyword by the user, don't link it to the query
                        continue
                    else:
                        print(f"existing market: {existing.marketplace}")
                        print(f"existing country: {existing.location_country}")
                        db.session.add(UserQueryItems(query_id=query.query_id, item_id=existing.item_id, created_at=current_time))
                        # Add the item to the list of new items for the query
            else:
                # If we have never seen this item before, create a new global item
                valid_data = {k: v for k, v in item_data.items() if k in item_columns}
                new_item = Item(**valid_data)
                # Add the location data to the item
                new_item.location_country = item_data.get('location', {}).get('country')
                new_item.postal_code = item_data.get('location', {}).get('postal_code')
                db.session.add(new_item)
                print(f"[Process Items] Item {idx+1}/{len(items)}: New item created (eBay ID: {item_data['ebay_id']})")

                print(f"new item market: {new_item.marketplace}")
                print(f"new item country: {new_item.location_country}")
                # Flush to get the new item ID
                db.session.flush()

                print(f"[Process Items] Linking new item {new_item.item_id} to keyword {keyword.keyword_text}")
            
                # Link to keyword
                db.session.add(KeywordItems(
                keyword_id=keyword.keyword_id,
                item_id=new_item.item_id,
                found_at=current_time
                ))

                print(f"[Process Items] Linking new item {new_item.item_id} to query {query.query_id}")
                # Link to user query
                db.session.add(UserQueryItems(
                query_id=query.query_id,
                item_id=new_item.item_id,
                auction_ending_notification_sent=False,
                created_at=current_time
                ))
            
                db.session.commit()
        
        else:
            # If it is not the first time the query has been run (subsequent full scrapes/recent scrapes)
            if existing:
                # Check if the item is already linked to this keyword, if not add the link
                if not KeywordItems.query.filter_by(keyword_id=keyword.keyword_id, item_id=existing.item_id).first():
                    db.session.add(KeywordItems(keyword_id=keyword.keyword_id, item_id=existing.item_id))
                # Check if the item is already linked to the query
                if not UserQueryItems.query.filter_by(query_id=query.query_id, item_id=existing.item_id).first():
                    print(f"[Process Items] Linking existing item {existing.item_id} to query {query.query_id}")
                    # If not add the link and include in new_items for notification
                    if feedback and feedback.is_relevant is False:
                        #If the item has already been marked as irrelevant for this keyword by the user, don't link it to the query
                        continue
                    else:
                        db.session.add(UserQueryItems(query_id=query.query_id, item_id=existing.item_id, created_at=current_time))
                        new_items.append(existing)
            else:
                # If we have never seen this item before, create a new global item
                valid_data = {k: v for k, v in item_data.items() if k in item_columns}
                new_item = Item(**valid_data)
                # Add the location data to the item
                new_item.location_country = item_data.get('location', {}).get('country')
                new_item.postal_code = item_data.get('location', {}).get('postal_code')
                db.session.add(new_item)
                new_items.append(new_item)
                print(f"[Process Items] Item {idx+1}/{len(items)}: New item created (eBay ID: {item_data['ebay_id']})")

                # Flush to get the new item ID
                db.session.flush()
            
                # Link to keyword
                db.session.add(KeywordItems(
                    keyword_id=keyword.keyword_id,
                    item_id=new_item.item_id,
                    found_at=current_time
                    ))

                # Link to user query
                db.session.add(UserQueryItems(
                    query_id=query.query_id,
                    item_id=new_item.item_id,
                    auction_ending_notification_sent=False,
                    created_at=current_time
                    ))
            
                db.session.commit()


        #Update the existings item fields if they have changed
        if existing:
            update_count = 0
            for key in item_columns - {'item_id', 'created_at'}:
                if key in item_data and getattr(existing, key) != item_data[key]:
                    update_count += 1
                    setattr(existing, key, item_data[key])
                    existing.last_updated = current_time
            if update_count > 0:
                updated_items.append(existing)

        # Track price changes using the existing price that the item was found at
        if existing:
            old_price = existing.price
            new_price = item_data.get('price')
            if new_price and old_price and new_price < old_price:
                price_drops.append({
                    'item': existing,
                    'old_price': old_price,
                    'new_price': new_price
                })

        # Auction ending detection (now global)
        end_time = item_data.get('end_time')
        print(f"[Process Items] Auction ending detection: {end_time}")
        if end_time:
            end_time = end_time.replace(tzinfo=timezone.utc)
            if (end_time - current_time) < timedelta(hours=12):
                item = existing or new_item
                user_query_item = UserQueryItems.query.filter_by(
                    query_id=query.query_id,
                    item_id=item.item_id
                ).first()
                
                if user_query_item and not user_query_item.auction_ending_notification_sent:
                    ending_auctions.append(item)
                    user_query_item.auction_ending_notification_sent = True
    
    try:
        db.session.commit()
        print(f"[Process Items] Commit successful")
        print(f"[Process Items] New items: {len(new_items)}, Updated items: {len(updated_items)}")
        print(f"[Process Items] Price drops: {len(price_drops)}, Ending auctions: {len(ending_auctions)}")

        if notify:
            # Notify only for this query's user
            user = User.query.get(query.user_id)
            prefs = user.notification_preferences
            notification_counts = {'new_items': 0, 'price_drops': 0, 'auction_alerts': 0}
            
            if new_items:
                if new_items and prefs.get('new_items', True):
                    notification_counts['new_items'] = len(new_items)
                    NotificationManager.send_item_notification(user, new_items, query.keyword.keyword_text)

            if price_drops:
                if price_drops and prefs.get('price_drops', True):
                    notification_counts['price_drops'] = len(price_drops)
                    NotificationManager.send_price_drops(user, price_drops, query.keyword.keyword_text)

            if ending_auctions:
                print(f"[Process Items] Auction ending detection: {ending_auctions}")
                if ending_auctions and prefs.get('auction_alerts', True):
                    notification_counts['auction_alerts'] = len(ending_auctions)
                    print(f"[Process Items] Sending auction alerts for {len(ending_auctions)} items")
                    NotificationManager.send_auction_alerts(user, ending_auctions, query.keyword.keyword_text)

            print(f"[Process Items] Notifications sent: {notification_counts}")

        return new_items, updated_items

    except Exception as e:
        print(f"[Process Items] Database commit failed: {str(e)}")
        db.session.rollback()
        raise




