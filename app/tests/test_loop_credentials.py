import os
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from ebay_client import EbayClient
from ebay_client.auth import InMemoryTokenStore
from flask import Flask

@pytest.fixture
def app():
    """Create a Flask app context for testing"""
    flask_app = Flask(__name__)
    flask_app.config['EBAY_CREDENTIALS'] = [
    {
        'client_id': 'test-client-1',
        'client_secret': 'test-secret-1',
        'token': None,          # Will be populated automatically
        'token_expiry': None   # Will be populated automatically
    },
    {
        'client_id': 'test-client-2',
        'client_secret': 'test-secret-2',
        'token': None,
        'token_expiry': None
    }
]
    return flask_app

@pytest.fixture
def mock_credentials():
    return [
        {
            'client_id': 'test-client-1',
            'client_secret': 'test-secret-1',
            'token': None,
            'token_expiry': None
        },
        {
            'client_id': 'test-client-2',
            'client_secret': 'test-secret-2',
            'token': None,
            'token_expiry': None
        }
    ]

@patch('requests.post')
def test_credential_rotation(mock_post, mock_credentials, app):
    """Verify credentials are used in round-robin order"""
    # Mock the token API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'fake-token', 'expires_in': 7200}
    mock_post.return_value = mock_response
    
    # Create app context
    with app.app_context():
        api = EbayClient(
            credentials=mock_credentials,
            token_store=InMemoryTokenStore(),
        )
        
        # Track used credentials
        used_indices = []
        
        # Simulate 5 API calls
        for _ in range(5):
            # Get credential before call
            expected_index = api.token_provider.current_cred_index
            used_indices.append(expected_index)
            
            # Trigger token refresh
            api.token_provider.get_token()
            
            # Verify rotation
            assert api.token_provider.current_cred_index == (
                expected_index + 1
            ) % len(api.credentials)
        
        # Verify rotation pattern: [0, 1, 0, 1, 0] for 2 credentials
        assert used_indices == [0, 1, 0, 1, 0]

@patch('requests.post')
@patch('requests.Session.get')
def test_token_refresh_flow(mock_get, mock_post, mock_credentials, app):
    """Verify token refresh works for each credential"""
    # Mock token responses
    mock_post.return_value.json.side_effect = [
        {'access_token': 'token1', 'expires_in': 7200},
        {'access_token': 'token2', 'expires_in': 7200}
    ]
    mock_post.return_value.status_code = 200
    
    # Mock API response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'items': []}
    
    with app.app_context():
        api = EbayClient(
            credentials=mock_credentials,
            token_store=InMemoryTokenStore(),
        )
        
        # First call - should use credential 0
        api.search_item_summaries("test")
        mock_post.assert_called_with(
            'https://api.ebay.com/identity/v1/oauth2/token',
            auth=('test-client-1', 'test-secret-1'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'client_credentials', 
                  'scope': 'https://api.ebay.com/oauth/api_scope'}
        )
        
        # Second call - should use credential 1
        api.search_item_summaries("test")
        mock_post.assert_called_with(
            'https://api.ebay.com/identity/v1/oauth2/token',
            auth=('test-client-2', 'test-secret-2'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={'grant_type': 'client_credentials', 
                  'scope': 'https://api.ebay.com/oauth/api_scope'}
        )

# Consider using the @pytest.mark.skip decorator for real API tests
@pytest.mark.skipif(
       os.environ.get('SKIP_REAL_API_TESTS') == '1',
       reason="Uses real API credentials"
   )
def test_real_world_rotation(app):
    """Integration test with real credentials (run sparingly)"""
    with app.app_context():
        api = EbayClient(token_store=InMemoryTokenStore())
        
        # Track used client IDs
        used_client_ids = []
        
        # Make 3 quick calls
        for _ in range(3):
            # Store current credential before rotation
            current_cred = api.credentials[api.token_provider.current_cred_index]
            used_client_ids.append(current_cred['client_id'])
            
            # Make API call
            result = api.search_item_summaries("test")
            assert 'itemSummaries' in result  # Verify basic response structure
        
        # Verify rotation pattern
        expected_pattern = [
            api.credentials[0]['client_id'],
            api.credentials[1]['client_id'],
            api.credentials[0]['client_id']
        ]
        assert used_client_ids == expected_pattern
