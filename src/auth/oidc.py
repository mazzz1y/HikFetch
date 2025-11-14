import logging

import requests
from authlib.integrations.flask_client import OAuth

logger = logging.getLogger(__name__)


def check_oidc_claims(userinfo, oidc_config):
    if not oidc_config.get('enabled'):
        return False

    claim_field = oidc_config.get('claim_field')
    allowed_values = oidc_config.get('allowed_values', [])

    if not claim_field or not allowed_values:
        return True

    claim_value = userinfo.get(claim_field)

    if claim_value is None:
        logger.warning(
            f"Access denied: claim field '{claim_field}' not found in userinfo. Available claims: {list(userinfo.keys())}")
        return False

    if isinstance(claim_value, list):
        result = any(val in allowed_values for val in claim_value)
        if not result:
            logger.warning(
                f"Access denied: no matching values in claim '{claim_field}'. User has {claim_value}, allowed values are {allowed_values}")
        return result
    else:
        result = claim_value in allowed_values
        if not result:
            logger.warning(
                f"Access denied: claim '{claim_field}' value mismatch. User has '{claim_value}', allowed values are {allowed_values}")
        return result


def init_oidc(app, oidc_discovery_url, oidc_client_id, oidc_client_secret,
              oidc_claim_field, oidc_allowed_values, oidc_scopes):
    try:
        discovery_response = requests.get(oidc_discovery_url, timeout=10)
        discovery_response.raise_for_status()
        discovery_doc = discovery_response.json()

        oidc_config = {
            'enabled': True,
            'discovery_url': oidc_discovery_url,
            'authorization_endpoint': discovery_doc.get('authorization_endpoint'),
            'token_endpoint': discovery_doc.get('token_endpoint'),
            'userinfo_endpoint': discovery_doc.get('userinfo_endpoint'),
            'end_session_endpoint': discovery_doc.get('end_session_endpoint'),
            'client_id': oidc_client_id,
            'client_secret': oidc_client_secret,
            'claim_field': oidc_claim_field,
            'allowed_values': oidc_allowed_values
        }

        oauth = OAuth(app)
        oauth.register(
            name='oidc',
            client_id=oidc_client_id,
            client_secret=oidc_client_secret,
            server_metadata_url=oidc_discovery_url,
            client_kwargs={
                'scope': oidc_scopes,
            }
        )

        return oauth, oidc_config

    except Exception as e:
        logger.error(f"Failed to initialize OIDC: {e}")
        raise
