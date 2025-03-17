import re
from decimal import Decimal, InvalidOperation


def filter_items_by_keywords(items, required_keywords, excluded_keywords, min_price=None, max_price=None):
    # Convert None to empty string for safety
    required = required_keywords or ''
    excluded = excluded_keywords or ''
    
    # Normalize inputs
    req_kws = {kw.strip().lower() for kw in required.split(',') if kw.strip()}
    excl_kws = {ekw.strip().lower() for ekw in excluded.split(',') if ekw.strip()}
    
    # Preprocess titles with null handling
    processed = []
    for item in items:
        # Handle null title/description
        title = (item.get('title') or '').lower()
        description = (item.get('description') or '').lower()
        full_text = f"{title} {description}"
        
        # Split into words from both title and description
        words = set(re.findall(r'\w+', full_text))
        processed.append((item, full_text, words))

    # Filter logic
    filtered = []
    for item, full_text, words in processed:
        # Required: all keywords present as whole words
        req_ok = all(
            re.search(rf'\b{re.escape(kw)}\b', full_text) 
            for kw in req_kws
        ) if req_kws else True
        
        # Excluded: none present as substrings
        excl_ok = not any(
            ekw in full_text
            for ekw in excl_kws
        ) if excl_kws else True
        
        if req_ok and excl_ok:
            filtered.append(item)
    
    return filtered

def filter_items_by_price(items, min_price=None, max_price=None):
    filtered = []
    
    for item in items:
        try:
            # Convert all prices to Decimal
            item_price = Decimal(str(item.get('price'))) if item.get('price') else None
            min_dec = Decimal(str(min_price)) if min_price else None
            max_dec = Decimal(str(max_price)) if max_price else None
        except (InvalidOperation, TypeError) as e:
            print(f"Price conversion error: {e}")
            continue  # Skip invalid items

        if item_price is None:
            continue  # Skip items without price

        # Calculate buffer bounds
        lower_bound = min_dec * Decimal('0.5') if min_dec else None
        upper_bound = max_dec * Decimal('2') if max_dec else None

        # Check if price is outside buffer
        price_ok = True
        if min_dec and item_price < lower_bound:
            price_ok = False
        if max_dec and item_price > upper_bound:
            price_ok = False

        if price_ok:
            filtered.append(item)
    
    return filtered

def item_matches_keywords(item, required_keywords_str, excluded_keywords_str):
    """
    Check if item matches keyword requirements
    Returns True if item should stay linked, False if should be removed
    """
    # Process keyword strings
    required = [k.strip().lower() for k in required_keywords_str.split(',') if k.strip()]
    excluded = [k.strip().lower() for k in excluded_keywords_str.split(',') if k.strip()]
    
    title_lower = item.title.lower()
    title_words = title_lower.split()
    
    # Check required keywords
    if required:
        if not all(
            any(keyword in word for word in title_words)
            for keyword in required
        ):
            return False
    
    # Check excluded keywords
    if excluded:
        if any(
            any(keyword in word for word in title_words)
            for keyword in excluded
        ):
            return False
            
    return True