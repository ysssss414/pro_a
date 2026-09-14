"""Explicit operator commands; HTTP has no registration or knowledge-write endpoint."""
import argparse
import json
from pathlib import Path

from .artifacts import Artifacts
from .config import BoundaryError, WorkbenchConfig
from .store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    commands.add_parser('prepare-review')
    register = commands.add_parser('register')
    register.add_argument('--packet', required=True, help='Relative to configured artifact root')
    register.add_argument('--run', required=True, help='Relative native engine/run root')
    serve = commands.add_parser('serve')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    try:
        config = WorkbenchConfig.load(args.config)
        if args.command == 'init':
            Store(config).initialize()
            print(json.dumps({'status': 'WORKBENCH_READY', 'mode': config.mode}))
        elif args.command == 'prepare-review':
            from .review_store import prepare_reviews, recover_workbench
            recover_workbench(config)
            print(json.dumps(prepare_reviews(config)))
        elif args.command == 'register':
            print(json.dumps(Artifacts(config).register(args.packet, args.run)))
        else:
            if not config.remote and args.host not in ('127.0.0.1', '::1', 'localhost'):
                raise BoundaryError('REMOTE_DISABLED')
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(config), host=args.host, port=args.port, proxy_headers=False, access_log=False)
    except Exception:
        parser.exit(1, 'Workbench command failed; verify configuration, schema and artifact boundaries.\n')


if __name__ == '__main__':
    main()
