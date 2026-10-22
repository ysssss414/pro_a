"""Explicit operator-only Recovery Origin inspection/registration. No workers."""
import argparse
import json
from pathlib import Path

from pro_a.evidence_binding import identity
from .candidate_inputs import CandidateArchive, CandidateInputs, inspect_attempt
from .config import BoundaryError, WorkbenchConfig


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--run',required=True)
    parser.add_argument('--attempt',required=True)
    parser.add_argument('--recovery',type=Path,required=True)
    parser.add_argument('--revisions',type=Path,required=True)
    parser.add_argument('--metadata-resolution',type=Path)
    parser.add_argument('--expected-identity',required=True)
    parser.add_argument('--register',action='store_true')
    parser.add_argument('--confirm-run')
    args=parser.parse_args(argv)
    load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    plan,revisions=load(args.recovery),load(args.revisions)
    resolution=load(args.metadata_resolution) if args.metadata_resolution else None
    archive=CandidateArchive(WorkbenchConfig.load(args.config))
    document=inspect_attempt(archive,args.run,args.attempt,revisions,resolution,recovery=plan)
    if document['identity']!=args.expected_identity:
        raise BoundaryError('RECOVERED_EXPECTED_IDENTITY_MISMATCH')
    reference=None
    if args.register:
        if args.confirm_run!=args.run:
            raise BoundaryError('RECOVERED_REGISTRATION_CONFIRMATION_REQUIRED')
        reference=CandidateInputs(archive).publish_recovered(args.run,args.attempt,plan,revisions,
            metadata_resolution=resolution,expected_identity=args.expected_identity)
    result={'origin_identity':document['identity'],'version':document['version'],
        'revision_sha256':identity(revisions),'registered':reference is not None,'reference':reference,
        'formal_accepted':False,'human_selected':False,'canonical_permission':False,
        'independent_child_ids':[o['semantic_revision']['child']['child_id'] for o in document['objects']
            if o.get('parent') and o['status']=='SEMANTIC_REVIEW_REQUIRED']}
    print(json.dumps(result,ensure_ascii=False))
    return result


if __name__=='__main__':
    main()
