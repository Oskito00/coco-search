from datetime import datetime, timezone


def parse_ebay_datetime(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
