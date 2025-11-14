from flask import render_template, request, jsonify, redirect, url_for, Response, session

from src.auth.oidc import check_oidc_claims


def register_routes(app, oauth, oidc_config, credentials, task_manager, config, requires_auth, auth_method='none'):
    @app.route('/')
    @requires_auth
    def index():
        return render_template('index.html')

    @app.route('/auth/login')
    def auth_login():
        if not oidc_config.get('enabled'):
            return redirect(url_for('index'))

        if oauth is None:
            return jsonify({'error': 'OIDC not configured'}), 500

        redirect_uri = url_for('auth_callback', _external=True, _scheme=app.config.get('PREFERRED_URL_SCHEME'))
        return oauth.oidc.authorize_redirect(redirect_uri)

    @app.route('/auth/callback')
    def auth_callback():
        if not oidc_config.get('enabled') or oauth is None:
            return redirect(url_for('index'))

        try:
            oauth.oidc.authorize_access_token()
            userinfo = oauth.oidc.userinfo()

            if not check_oidc_claims(userinfo, oidc_config):
                session.clear()
                return Response('Access denied: insufficient permissions', 403)

            session.permanent = True
            session['authenticated'] = True

            return redirect(url_for('index'))

        except Exception as e:
            app.logger.error(f"OIDC callback error: {e}")
            return Response('Authentication failed', 401)

    @app.route('/auth/logout')
    def auth_logout():
        if oidc_config.get('enabled'):
            session.clear()

            if oauth and oidc_config.get('end_session_endpoint'):
                redirect_uri = url_for('index', _external=True, _scheme=app.config.get('PREFERRED_URL_SCHEME'))
                return redirect(f"{oidc_config['end_session_endpoint']}?post_logout_redirect_uri={redirect_uri}")

        return redirect(url_for('index'))

    @app.route('/auth/userinfo')
    @requires_auth
    def auth_userinfo():
        return jsonify({'authenticated': True, 'method': auth_method})

    @app.route('/download', methods=['POST'])
    @requires_auth
    def download():
        data = request.json

        start_date = data.get('start_date')
        start_time = data.get('start_time')
        end_date = data.get('end_date')
        end_time = data.get('end_time')
        camera_channel = int(data.get('camera_channel', 1))

        start_datetime_str = f"{start_date} {start_time}"
        end_datetime_str = f"{end_date} {end_time}"

        task_params = {
            'config': config,
            'camera_url': credentials['camera_url'],
            'user_name': credentials['username'],
            'user_password': credentials['password'],
            'start_datetime_str': start_datetime_str,
            'end_datetime_str': end_datetime_str,
            'camera_channel': camera_channel
        }

        task_id = task_manager.create_task(task_params)

        return jsonify({'task_id': task_id})

    @app.route('/tasks', methods=['GET'])
    @requires_auth
    def get_tasks():
        tasks = task_manager.get_all_tasks()
        return jsonify([task.to_dict() for task in tasks])

    @app.route('/tasks/<task_id>', methods=['GET'])
    @requires_auth
    def get_task(task_id):
        task = task_manager.get_task(task_id)
        if task:
            return jsonify(task.to_dict())
        return jsonify({'error': 'Task not found'}), 404

    @app.route('/tasks/<task_id>/cancel', methods=['POST'])
    @requires_auth
    def cancel_task(task_id):
        if task_manager.cancel_task(task_id):
            return jsonify({'status': 'cancelled'})
        return jsonify({'error': 'Task not found'}), 404
