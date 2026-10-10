from copy import deepcopy
import pytest
from pro_a.evidence_binding import identity
from pro_a.workbench import lossless_compatibility as compatibility, lossless_recovery as recovery
from pro_a.workbench.source_operations import SourceOperationError


def proof():
    manifest={'synthetic.py':'a'*64}
    return {'version':compatibility.CONTINUATION_VERSION,
        'old_code':{'target_commit':compatibility.CONTINUATION_RELEASE,'target_manifest':manifest},
        'old_install':{'commit':compatibility.CONTINUATION_RELEASE,'manifest':manifest},
        'code':{'target_commit':'b'*40,'target_manifest':manifest},'target_contract':{},
        'regeneration_contract':recovery.evidence_contract(),'scope':{'run_id':'SYNTHETIC_HISTORICAL_RUN'}}


def test_historical_read_never_issues_current_execution_authority():
    evidence=proof();before=deepcopy(evidence)
    assert compatibility.read_continuation_evidence(evidence,identity(evidence))==before
    assert type(compatibility.read_continuation_evidence(evidence,identity(evidence))) is dict
    with pytest.raises(SourceOperationError,match='EVIDENCE_CONTINUATION_TARGET_DRIFT'):
        compatibility.restore_continuation(evidence,identity(evidence))
    assert evidence==before


def test_historical_proof_still_requires_immutable_identity_and_contract():
    evidence=proof();sealed=identity(evidence)
    evidence['scope']['run_id']='CHANGED'
    with pytest.raises(SourceOperationError,match='EVIDENCE_CONTINUATION_TOKEN_DRIFT'):
        compatibility.read_continuation_evidence(evidence,sealed)
    evidence=proof();evidence['regeneration_contract']['guidance_sha256']='0'*64
    with pytest.raises(SourceOperationError,match='EVIDENCE_CONTINUATION_TARGET_DRIFT'):
        compatibility.read_continuation_evidence(evidence,identity(evidence))
