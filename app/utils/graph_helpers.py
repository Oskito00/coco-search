from app.models import Item, UserQueryItems
import pandas as pd
from datetime import datetime, timedelta

def get_price_data(items):
    """
    Returns 3-day rolling average price history
    Format: [{'price': float, 'date': iso_date_str}]
    """
    # Filter items with valid dates
    valid_items = [
        item for item in items 
        if item.item and 
        item.item.start_time and  # Ensures not None
        pd.notna(pd.to_datetime(item.item.start_time, errors='coerce')) and
        item.item.price and 
        item.item.currency
    ]

    # Create separate DataFrames
    price_df = pd.DataFrame({
        'date': [item.item.start_time for item in valid_items],
        'price': [float(item.item.price) for item in valid_items],
        'currency': [item.item.currency for item in valid_items]
    }).sort_values('date')

    location_df = pd.DataFrame({
        'date': [item.item.start_time for item in valid_items],
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

    average_price_last_30_days = merged_df[merged_df['date'] > (datetime.now() - timedelta(days=30))]['price'].mean() if merged_df['date'].size > 0 else 0
    most_frequent_currency = merged_df['currency'].mode()[0] if merged_df['currency'].mode().size > 0 else 'GBP'
    
    return merged_df.to_dict('records'), average_price_last_30_days, most_frequent_currency