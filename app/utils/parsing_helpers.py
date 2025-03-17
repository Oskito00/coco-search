from datetime import datetime, timezone

def parse_date(date_str):
    if not date_str:
        return None
    
    # Handle eBay's format: 2021-12-18T20:03:17.000Z
    try:
        # Parse with timezone awareness
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            # Fallback for non-UTC or alternative formats
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None