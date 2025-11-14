from functools import wraps

from flask import request, redirect, url_for, Response, session

from .basic import check_basic_auth


def requires_auth(auth_method, oidc_config, credentials):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if auth_method == 'oidc':
                if not session.get('authenticated'):
                    return redirect(url_for('auth_login'))
                return f(*args, **kwargs)
            elif auth_method == 'basic':
                auth = request.authorization
                if not check_basic_auth(auth.username if auth else None,
                                        auth.password if auth else None,
                                        credentials):
                    return Response(
                        'Authentication required', 401,
                        {'WWW-Authenticate': 'Basic realm="Login Required"'}
                    )
                return f(*args, **kwargs)
            else:  # none
                return f(*args, **kwargs)

        return decorated

    return decorator
