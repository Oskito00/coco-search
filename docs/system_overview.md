# Coco Search System Overview

## Product Goal

Coco Search is an eBay notifier SaaS. Users create saved searches, the app monitors eBay at a configured interval, stores matching items, and decides whether to notify the user about new or changed products.

The long-term goal is not just keyword matching. The app should learn what each user is likely to care about from explicit feedback and interactions.

## Current Major Components

### eBay SDK

Package: `ebay_client/`

Responsibilities:

- Own all direct eBay API interactions.
- Handle OAuth credentials and access tokens.
- Call Browse search endpoints.
- Call Analytics/rate-limit endpoints.
- Parse eBay responses into SDK-level item dictionaries.

This package should stay independent from Flask, SQLAlchemy, Stripe, notification code, and Coco-specific search/relevance rules.

### Saved Searches

Current files:

- `app/forms.py`
- `app/routes/queries.py`
- `app/models.py`
- `app/searches/`

Responsibilities:

- Let users create searches.
- Store search keywords, marketplace, filters, and schedule.
- Enforce a minimum check interval of 5 minutes.
- Convert stored searches into executable eBay SDK requests.

Current legacy search parameters:

- `required_keywords`
- `excluded_keywords`

These should remain as rule-based hard filters, but they should not be the primary relevance strategy long term.

### Search Execution

Current files:

- `app/searches/execution.py`
- `app/searches/scheduled.py`
- `app/jobs/query_check.py`

Responsibilities:

- Run saved searches on schedule.
- Call `ebay_client`.
- Apply legacy hard filters.
- Return candidate items for storage and relevance evaluation.

### Item Storage And Identity

Current files:

- `app/models.py`
- `app/repositories/items.py`
- `app/searches/item_processor.py`

Responsibilities:

- Store global eBay items.
- Link items to keywords and user searches.
- Detect duplicates by eBay item ID.
- Detect updates, price drops, and auctions ending soon.

### Relevance And ML

Current files:

- `app/relevance/`
- `app/models.py` via `ItemRelevanceFeedback`

Responsibilities:

- Record explicit user feedback.
- Extract item/search features.
- Decide whether a user is likely to want a notification for an item.
- Start with heuristics and feedback lookup.
- Later support a trained classifier or clustering-based pipeline.

Target feedback/interactions:

- likely to buy / not likely to buy
- relevant / not relevant
- clicked
- dismissed
- notified
- ignored
- purchased

Target features:

- item title
- item description if available
- price
- condition
- category
- location
- seller features
- query text
- marketplace

### Notifications

Current files:

- `app/notifications/`
- `app/utils/notifications.py`

Responsibilities:

- Convert domain events into notifications.
- Respect user notification preferences.
- Send via Telegram/email adapters.

Notification decisions should eventually depend on relevance output, not only whether an item is new.

## Target Monitoring Flow

```text
User creates saved search
-> validate search and schedule
-> run onboarding preview search
-> show diverse candidate items
-> ask "Would you be likely to buy this?"
-> store feedback/interactions
-> scheduled monitoring begins
-> eBay SDK returns candidate items
-> hard filters run
-> item is normalized and stored
-> relevance service scores item for user/search
-> domain event is emitted
-> notification service sends only if relevant enough
```

## Onboarding Preview Flow

When a user creates a search, the app should fetch an initial sample of results before relying on notifications.

Suggested first implementation:

1. Fetch about 100 items from eBay for the saved search.
2. Apply hard filters.
3. Extract lightweight features.
4. Select about 20 diverse examples.
5. Ask the user whether they would be likely to buy each item.
6. Store feedback for the relevance pipeline.

The first version should use diverse sampling, not a full clustering model. Clustering can replace or improve the sampler later.

## Recommended Next Slice

Build the saved-search definition and onboarding-preview layer.

Why:

- It is the bridge between user-created searches and ML/relevance.
- It defines the domain language before execution, storage, and notifications become more complex.
- It can be implemented without changing database schema initially.
- It preserves legacy keyword filters while preparing the ML pipeline.

Suggested files:

```text
app/searches/definitions.py
app/searches/mapping.py
app/searches/onboarding.py
app/searches/sampling.py
app/relevance/features.py
```

Suggested core API:

```python
saved_search = saved_search_from_model(user_query)
params = to_ebay_search_params(saved_search)
preview = SearchOnboardingService().create_preview(saved_search)
features = extract_item_features(item, saved_search)
```

## Boundaries To Preserve

- `ebay_client` only talks to eBay.
- `app/searches` owns saved-search definitions, execution, onboarding, and hard filters.
- `app/relevance` owns feature extraction, feedback, scoring, and future model inference.
- `app/repositories` owns database access.
- `app/notifications` owns event-to-notification mapping and channel adapters.
- Scheduled jobs should stay thin wrappers.
