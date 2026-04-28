def extract_browse_rate(rate_data):
    for limit in rate_data.get("rateLimits", []):
        if limit.get("apiContext") == "buy" and limit.get("apiName") == "Browse":
            for resource in limit.get("resources", []):
                if resource.get("name") == "buy.browse":
                    return resource["rates"][0]
    return {}
