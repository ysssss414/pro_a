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
    commands.add_parser('prepare-attribution')
    commands.add_parser('prepare-current-view')
    commands.add_parser('prepare-impact')
    commands.add_parser('prepare-research')
    commands.add_parser('prepare-cloud-jobs')
    commands.add_parser('reconcile-cloud-jobs')
    worker = commands.add_parser('run-fake-cloud-job')
    worker.add_argument('--job-id')
    worker.add_argument('--worker-id', default='stage6-fake-worker')
    worker.add_argument('--delay-seconds', type=float, default=0.0)
    worker.add_argument('--scenario', choices=(
        'success', 'rate_limit_then_success', 'transport_failure', 'timeout_before_dispatch',
        'unknown_external_outcome', 'accepted_alias', 'model_mismatch', 'usage_unknown',
        'invalid_output'), default='success')
    worker.add_argument('--fault-at', choices=(
        'before_claim', 'after_claim', 'after_dispatch_intent', 'before_network_call',
        'after_provider_response', 'before_result_artifact_durable',
        'after_result_artifact_durable', 'before_terminal_update', 'after_terminal_update'))
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
        elif args.command == 'prepare-attribution':
            from .attribution_store import prepare_attribution
            print(json.dumps(prepare_attribution(config)))
        elif args.command == 'prepare-current-view':
            from .view_store import prepare_current_views
            print(json.dumps(prepare_current_views(config)))
        elif args.command == 'prepare-impact':
            from .impact_store import prepare_impact
            print(json.dumps(prepare_impact(config)))
        elif args.command == 'prepare-research':
            from .research_store import prepare_research
            print(json.dumps(prepare_research(config)))
        elif args.command == 'prepare-cloud-jobs':
            from .cloud_jobs import prepare_cloud_jobs
            print(json.dumps(prepare_cloud_jobs(config)))
        elif args.command == 'reconcile-cloud-jobs':
            from .cloud_jobs import CloudJobs
            print(json.dumps(CloudJobs(config).reconcile()))
        elif args.command == 'run-fake-cloud-job':
            if config.mode != 'DEMO':
                raise BoundaryError('FAKE_PROVIDER_DEMO_ONLY')
            if not 0 <= args.delay_seconds <= 30:
                raise BoundaryError('FAKE_PROVIDER_DELAY_INVALID')
            from pro_a.cloud_contract import DeterministicFakeProvider
            from .cloud_jobs import CloudJobs
            provider = DeterministicFakeProvider(args.scenario, delay_seconds=args.delay_seconds)
            result = CloudJobs(config).run_once(provider, worker_id=args.worker_id,
                                                job_id=args.job_id, fault_at=args.fault_at)
            print(json.dumps({'job': result, 'fake_provider_calls': provider.call_count}))
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
