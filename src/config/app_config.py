import argparse
import os
import secrets


def get_config_from_env():
    camera_url = os.environ.get('HIKFETCH_CAMERA_URL')
    username = os.environ.get('HIKFETCH_CAMERA_USERNAME')
    password = os.environ.get('HIKFETCH_CAMERA_PASSWORD')
    download_dir = os.environ.get('HIKFETCH_DOWNLOAD_DIR')
    web_username = os.environ.get('HIKFETCH_WEB_USERNAME')
    web_password = os.environ.get('HIKFETCH_WEB_PASSWORD')
    oidc_discovery_url = os.environ.get('HIKFETCH_OIDC_DISCOVERY_URL')
    oidc_client_id = os.environ.get('HIKFETCH_OIDC_CLIENT_ID')
    oidc_client_secret = os.environ.get('HIKFETCH_OIDC_CLIENT_SECRET')
    oidc_claim_field = os.environ.get('HIKFETCH_OIDC_CLAIM_FIELD')
    oidc_allowed_values_str = os.environ.get('HIKFETCH_OIDC_ALLOWED_VALUES', '')
    oidc_allowed_values = [v.strip() for v in oidc_allowed_values_str.split(',') if v.strip()]
    oidc_scopes = os.environ.get('HIKFETCH_OIDC_SCOPES', 'openid profile email groups')
    public_url = os.environ.get('HIKFETCH_PUBLIC_URL')
    auth_method = os.environ.get('HIKFETCH_AUTH_METHOD', 'none')
    log_level = os.environ.get('HIKFETCH_LOG_LEVEL', 'INFO').upper()

    return {
        'camera_url': camera_url,
        'username': username,
        'password': password,
        'download_dir': download_dir,
        'web_username': web_username,
        'web_password': web_password,
        'oidc_discovery_url': oidc_discovery_url,
        'oidc_client_id': oidc_client_id,
        'oidc_client_secret': oidc_client_secret,
        'oidc_claim_field': oidc_claim_field,
        'oidc_allowed_values': oidc_allowed_values,
        'oidc_scopes': oidc_scopes,
        'public_url': public_url,
        'auth_method': auth_method,
        'log_level': log_level
    }


def validate_config(config, error_fn):
    if not config['camera_url']:
        error_fn('Camera URL is required (set HIKFETCH_CAMERA_URL env var)')
    if not config['username']:
        error_fn('Username is required (set HIKFETCH_CAMERA_USERNAME env var)')
    if not config['password']:
        error_fn('Password is required (set HIKFETCH_CAMERA_PASSWORD env var)')
    if not config['download_dir']:
        error_fn('Download directory is required (set HIKFETCH_DOWNLOAD_DIR env var)')

    basic_provided = config['web_username'] and config['web_password']
    oidc_provided = config['oidc_discovery_url'] and config['oidc_client_id'] and config['oidc_client_secret']

    if config['auth_method'] == 'basic':
        if not basic_provided:
            error_fn('Auth method set to basic but HIKFETCH_WEB_USERNAME and HIKFETCH_WEB_PASSWORD required')
        if oidc_provided:
            error_fn('Cannot enable both Basic and OIDC authentication')
    elif config['auth_method'] == 'oidc':
        if not oidc_provided:
            error_fn('Auth method set to oidc but OIDC env vars required')
        if basic_provided:
            error_fn('Cannot enable both Basic and OIDC authentication')
    elif config['auth_method'] == 'none':
        if basic_provided or oidc_provided:
            error_fn('Auth method set to none but authentication vars provided')
    else:
        error_fn('Invalid HIKFETCH_AUTH_METHOD. Must be none, basic, or oidc')

    if config['download_dir']:
        config['download_dir'] = config['download_dir'].rstrip('/') + '/'


def parse_arguments():
    parser = argparse.ArgumentParser(description='HikFetch')
    parser.add_argument('--host', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, help='Port to bind (default: 5000)')

    args = parser.parse_args()

    config = get_config_from_env()
    validate_config(config, parser.error)

    config['host'] = args.host or '0.0.0.0'
    config['port'] = args.port or 5000

    return config


def build_credentials(args):
    return {
        'username': args['username'],
        'password': args['password'],
        'camera_url': args['camera_url'],
        'web_username': args.get('web_username'),
        'web_password': args.get('web_password')
    }


def build_download_config(args):
    return {
        'path_to_media_archive': args['download_dir'],
        'default_timeout_seconds': 15,
        'retry_delay_seconds': 5
    }


def configure_app(app, public_url):
    from datetime import timedelta

    app.config['SECRET_KEY'] = os.environ.get('HIKFETCH_SECRET_KEY', secrets.token_hex(32))
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('HIKFETCH_SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    if public_url:
        from urllib.parse import urlparse
        parsed = urlparse(public_url)
        app.config['SERVER_NAME'] = parsed.netloc
        app.config['PREFERRED_URL_SCHEME'] = parsed.scheme
