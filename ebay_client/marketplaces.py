from dataclasses import dataclass


@dataclass(frozen=True)
class Marketplace:
    code: str
    location: str
    country: str
    site: str
    currency: str
    language: str

    @classmethod
    def from_mapping(cls, data):
        return cls(
            code=data["code"],
            location=data["location"],
            country=data["country"],
            site=data["site"],
            currency=data["currency"],
            language=data["language"],
        )

    def as_dict(self):
        return {
            "code": self.code,
            "location": self.location,
            "country": self.country,
            "site": self.site,
            "currency": self.currency,
            "language": self.language,
        }


MARKETPLACES = {
    "EBAY_GB": Marketplace(
        code="EBAY_GB",
        location="GB",
        country="United Kingdom",
        site="ebay.co.uk",
        currency="GBP",
        language="en-GB",
    ),
    "EBAY_US": Marketplace(
        code="EBAY_US",
        location="US",
        country="United States",
        site="ebay.com",
        currency="USD",
        language="en-US",
    ),
    "EBAY_DE": Marketplace(
        code="EBAY_DE",
        location="DE",
        country="Germany",
        site="ebay.de",
        currency="EUR",
        language="de-DE",
    ),
    "EBAY_CA": Marketplace(
        code="EBAY_CA",
        location="CA",
        country="Canada",
        site="ebay.ca",
        currency="CAD",
        language="en-CA",
    ),
    "EBAY_AU": Marketplace(
        code="EBAY_AU",
        location="AU",
        country="Australia",
        site="ebay.com.au",
        currency="AUD",
        language="en-AU",
    ),
    "EBAY_FR": Marketplace(
        code="EBAY_FR",
        location="FR",
        country="France",
        site="ebay.fr",
        currency="EUR",
        language="fr-FR",
    ),
    "EBAY_IT": Marketplace(
        code="EBAY_IT",
        location="IT",
        country="Italy",
        site="ebay.it",
        currency="EUR",
        language="it-IT",
    ),
    "EBAY_ES": Marketplace(
        code="EBAY_ES",
        location="ES",
        country="Spain",
        site="ebay.es",
        currency="EUR",
        language="es-ES",
    ),
    "EBAY_NL": Marketplace(
        code="EBAY_NL",
        location="NL",
        country="Netherlands",
        site="ebay.nl",
        currency="EUR",
        language="nl-NL",
    ),
    "EBAY_PL": Marketplace(
        code="EBAY_PL",
        location="PL",
        country="Poland",
        site="ebay.pl",
        currency="PLN",
        language="pl-PL",
    ),
    "EBAY_ANY": Marketplace(
        code="EBAY_ANY",
        location="any",
        country="ANY",
        site="ebay.com",
        currency="USD",
        language="en-US",
    ),
}


MARKETPLACE_IDS = {
    code: marketplace.as_dict() for code, marketplace in MARKETPLACES.items()
}


def get_marketplace(code, default="EBAY_GB"):
    return MARKETPLACES.get(code, MARKETPLACES[default])


__all__ = ["MARKETPLACE_IDS", "MARKETPLACES", "Marketplace", "get_marketplace"]
