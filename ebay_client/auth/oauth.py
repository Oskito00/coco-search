from datetime import timedelta

import requests


class EbayOAuthClient:
    scope = "https://api.ebay.com/oauth/api_scope"

    def __init__(self, token_url, session=None):
        self.token_url = token_url
        self.session = session or requests

    def fetch_client_credentials_token(self, credential):
        response = self.session.post(
            self.token_url,
            auth=(credential.client_id, credential.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": self.scope,
            },
        )
        response.raise_for_status()

        token_data = response.json()
        return token_data["access_token"], timedelta(seconds=token_data["expires_in"])
