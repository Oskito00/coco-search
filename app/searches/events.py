from dataclasses import dataclass, field


@dataclass
class SearchProcessingResult:
    new_items: list = field(default_factory=list)
    updated_items: list = field(default_factory=list)
    price_drops: list = field(default_factory=list)
    ending_auctions: list = field(default_factory=list)
