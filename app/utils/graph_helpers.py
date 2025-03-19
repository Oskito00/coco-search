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
        .with_entities(
            Item.price, 
            Item.start_time,
            Item.location_country,  # Add this
            Item.postal_code,
            Item.currency
        )\
        .join(UserQueryItems, Item.item_id == UserQueryItems.item_id)\
        .filter(
            UserQueryItems.query_id == query_id,
            Item.start_time.isnot(None),
            Item.price.isnot(None),
            Item.location_country.isnot(None),
            Item.postal_code.isnot(None),
            Item.currency.isnot(None)
        )\
        .all()

    if not raw_data:
        return []

    # Create separate DataFrames
    price_df = pd.DataFrame({
        'date': [item.start_time for item in raw_data],
        'price': [float(item.price) for item in raw_data],
        'currency': [item.currency for item in raw_data]
    }).sort_values('date')

    location_df = pd.DataFrame({
        'date': [item.start_time for item in raw_data],
        'country': [item.location_country for item in raw_data],
        'postal_code': [item.postal_code for item in raw_data]
    })

    # Separate numeric and non-numeric data
    numeric_df = price_df[['date', 'price']]
    non_numeric_df = price_df[['date', 'currency']]

    # Calculate rolling average
    numeric_df = numeric_df.set_index('date')
    rolling_avg = numeric_df.rolling('3D', min_periods=1).mean().reset_index()

    # Merge data
    merged_df = pd.merge(
        rolling_avg,
        non_numeric_df,
        on='date',
        how='left'
    )
    merged_df = pd.merge(
        merged_df,
        location_df,
        on='date',
        how='left'
    )
    
    return merged_df.to_dict('records')
