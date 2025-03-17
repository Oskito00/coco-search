from app.models import Item, UserQueryItems
import pandas as pd
from datetime import timedelta

def get_query_price_data(query_id):
    """
    Returns 3-day rolling average price history
    Format: [{'price': float, 'date': iso_date_str}]
    """
    # Get raw data
    raw_data = Item.query\
        .with_entities(Item.price, Item.start_time)\
        .join(UserQueryItems, Item.item_id == UserQueryItems.item_id)\
        .filter(
            UserQueryItems.query_id == query_id,
            Item.start_time.isnot(None),
            Item.price.isnot(None
        ))\
        .all()

    if not raw_data:
        return []

    # Create DataFrame with datetime index
    df = pd.DataFrame([{
        'date': item.start_time,
        'price': float(item.price)
    } for item in raw_data]).sort_values('date')

    # Calculate 3-day rolling average
    df = df.set_index('date')
    rolling_avg = df.rolling('3D', min_periods=1).mean().reset_index()
    
    return [{
        'date': row['date'].isoformat(),
        'price': row['price']
    } for _, row in rolling_avg.iterrows()]