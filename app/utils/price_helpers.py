import numpy as np

def remove_price_outliers(items, multiplier=1.5):
    """
    Remove price outliers while preserving items without prices
    - Only filters items with non-null prices
    - Keeps items with price=None
    """
    # Get all valid prices
    valid_prices = [item.item.price for item in items if item.item.price is not None]
    
    # Need at least 4 priced items to detect outliers
    if len(valid_prices) < 4:
        return items, []
    
    # Calculate bounds using valid prices
    q1 = np.percentile(valid_prices, 10)
    q3 = np.percentile(valid_prices, 90)
    iqr = q3 - q1
    lower = q1 - multiplier*iqr
    upper = q3 + multiplier*iqr
    
    # Filter while keeping null prices
    filtered = []
    outliers = []
    auction_items = []
    for idx, item in enumerate(items):
        price = item.item.price
        if price is None or price == 0.0:
            auction_items.append(item)  # Keep items without prices
        elif lower <= price <= upper:
            filtered.append(item)
        else:
            print(f"Outlier: {price}")
            outliers.append(idx)
    
    return filtered, auction_items, outliers