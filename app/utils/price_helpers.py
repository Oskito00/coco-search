import numpy as np

def remove_price_outliers(items, multiplier=1.5):
    """
    Remove outliers using IQR method.
    Returns filtered list of items and outlier indices.
    """
    if len(items) < 4:  # Not enough data to determine outliers
        return items, []

    prices = [item.item.price for item in items if item.item.price is not None]
    
    # Calculate percentiles
    q1 = np.percentile(prices, 25)
    q3 = np.percentile(prices, 75)
    iqr = q3 - q1
    
    # Calculate outlier bounds
    lower_bound = q1 - (multiplier * iqr)
    upper_bound = q3 + (multiplier * iqr)
    
    # Filter items
    filtered = []
    outliers = []
    for idx, item in enumerate(items):
        price = item.item.price
        if price and lower_bound <= price <= upper_bound:
            filtered.append(item)
        else:
            outliers.append(idx)
    
    return filtered, outliers