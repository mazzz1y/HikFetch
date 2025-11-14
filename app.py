#!/usr/bin/env python3
import atexit
import signal

from flask import Flask

from src.auth import init_oidc
from src.auth.decorators import requires_auth as create_auth_decorator
from src.config import (
    configure_app,
    parse_arguments,
    get_config_from_env,
    validate_config,
    build_credentials,
    build_download_config
)
from src.logger import Logger
from src.routes import register_routes
from src.task_manager import TaskManager

task_manager = None


def create_app(args=None):
    global task_manager
    app = Flask(__name__)

    if args is None:
        args = get_config_from_env()
        validate_config(args, lambda msg: (_ for _ in ()).throw(ValueError(msg)))

    Logger.init_logger(log_level=args.get('log_level', 'INFO'))
    logger = Logger.get_logger()

    credentials = build_credentials(args)
    config = build_download_config(args)
    oidc_config = {}
    oauth = None

    if args['auth_method'] == 'oidc':
        oauth, oidc_config = init_oidc(
            app,
            args['oidc_discovery_url'],
            args['oidc_client_id'],
            args['oidc_client_secret'],
            args['oidc_claim_field'],
            args['oidc_allowed_values'],
            args['oidc_scopes']
        )

    configure_app(app, args['public_url'])

    requires_auth_decorator = create_auth_decorator(
        args['auth_method'], oidc_config, credentials
    )

    task_manager = TaskManager()
    register_routes(
        app, oauth, oidc_config, credentials,
        task_manager, config, requires_auth_decorator, args['auth_method']
    )

    task_manager.start()

    def cleanup():
        if task_manager:
            task_manager.stop()
    
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda signum, frame: cleanup())
    signal.signal(signal.SIGINT, lambda signum, frame: cleanup())

    logger.info("HikFetch Initialized")
    logger.info(f"Camera URL: {args['camera_url']}")
    logger.info(f"Media will be saved to: {args['download_dir']}")
    logger.info(f"Authentication: {args['auth_method']}")

    return app


app = create_app()


def main():
    args = parse_arguments()
    app = create_app(args)
    try:
        app.run(host=args['host'], port=args['port'], debug=False)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
