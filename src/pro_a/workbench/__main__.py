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
    commands.add_parser('prepare-source-operations')
    commands.add_parser('prepare-domains')
    commands.add_parser('rollback-domains')
    register_domain = commands.add_parser('register-domain')
    register_domain.add_argument('--pack', type=Path, required=True)
    assign_domain = commands.add_parser('assign-domains')
    assign_domain.add_argument('--assignment', type=Path, required=True)
    commands.add_parser('reconcile-cloud-jobs')
    preflight = commands.add_parser('preflight')
    preflight.add_argument('--max-path-chars', type=int, default=240)
    backup = commands.add_parser('backup')
    backup.add_argument('--output', type=Path, required=True)
    restore = commands.add_parser('restore')
    restore.add_argument('--backup', type=Path, required=True)
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
    source_worker = commands.add_parser('run-fake-source-operation')
    source_worker.add_argument('--phase4-config', type=Path, required=True)
    source_worker.add_argument('--processing-run-id')
    source_worker.add_argument('--worker-id', default='stage7-fake-worker')
    source_worker.add_argument('--scenario', choices=(
        'success', 'rate_limit_then_success', 'transport_failure', 'timeout_before_dispatch',
        'unknown_external_outcome', 'accepted_alias', 'model_mismatch', 'usage_unknown',
        'invalid_output'), default='success')
    serve = commands.add_parser('serve')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', type=int, default=8000)
    serve.add_argument('--phase4-config', type=Path)
    serve.add_argument('--max-pdf-mib', type=int, default=20)
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
        elif args.command == 'prepare-source-operations':
            from .source_operations import prepare_source_operations
            print(json.dumps(prepare_source_operations(config)))
        elif args.command in ('prepare-domains', 'rollback-domains', 'register-domain', 'assign-domains'):
            from .domains import Domains, prepare_domains, rollback_domains
            from pro_a.domain_packs import read_json
            if args.command == 'prepare-domains':
                result = prepare_domains(config)
            elif args.command == 'rollback-domains':
                result = rollback_domains(config)
            elif args.command == 'register-domain':
                result = Domains(config).register(args.pack)
            else:
                result = Domains(config).assign(**read_json(args.assignment))
            print(json.dumps(result))
        elif args.command == 'reconcile-cloud-jobs':
            from .cloud_jobs import CloudJobs
            print(json.dumps(CloudJobs(config).reconcile()))
        elif args.command == 'preflight':
            from .operations import path_preflight
            result = path_preflight(config, limit=args.max_path_chars)
            print(json.dumps(result))
            if result['status'] != 'PASS':
                raise BoundaryError('PATH_LENGTH_UNSAFE')
        elif args.command == 'backup':
            from .operations import create_backup
            print(json.dumps(create_backup(config, args.output)))
        elif args.command == 'restore':
            from .operations import restore_backup
            print(json.dumps(restore_backup(config, args.backup)))
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
        elif args.command == 'run-fake-source-operation':
            from pro_a.cloud_contract import DeterministicFakeProvider
            from .cloud_jobs import CloudProfile
            from .source_operations import SourceOperations, SourceProfile
            provider = DeterministicFakeProvider(args.scenario)
            service = SourceOperations(
                config, SourceProfile(args.phase4_config), CloudProfile.demo())
            result = service.advance_once(
                worker_id=args.worker_id, provider=provider,
                processing_run_id=args.processing_run_id)
            print(json.dumps({'run': result, 'fake_provider_calls': provider.call_count}))
        else:
            if not config.remote and args.host not in ('127.0.0.1', '::1', 'localhost'):
                raise BoundaryError('REMOTE_DISABLED')
            import uvicorn
            from .api import create_app
            from .source_operations import SourceProfile
            source_profile = (SourceProfile(args.phase4_config, args.max_pdf_mib * 1024 * 1024)
                              if args.phase4_config else None)
            uvicorn.run(create_app(config, source_profile=source_profile), host=args.host, port=args.port,
                        proxy_headers=False, access_log=False)
    except Exception:
        parser.exit(1, 'Workbench command failed; verify configuration, schema and artifact boundaries.\n')


if __name__ == '__main__':
    main()
