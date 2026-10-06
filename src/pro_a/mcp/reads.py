"""Reuse operational read methods without constructing write-capable services.

Only the selected existing methods are bound here. There is no profile, provider,
worker, retry, initialization or mutation method on these facades. Nested domain
reads retain Store's mode=ro/query_only and registered-artifact checks.
"""
from pro_a.workbench.artifacts import Artifacts
from pro_a.workbench.bounded_extraction_store import BoundedExtractionStore
from pro_a.workbench.bounded_source_analysis import BoundedSourceAnalysisRunner
from pro_a.workbench.output_decomposition import OutputDecompositionRunner
from pro_a.workbench.cloud_jobs import CloudJobs
from pro_a.workbench.config import BoundaryError
from pro_a.workbench.review_store import schema_version
from pro_a.workbench.review_workbench import ReviewWorkbench
from pro_a.workbench.source_operations import SourceOperations
from pro_a.workbench.store import Store
from pro_a.workbench.domains import Domains
from pro_a.workbench.stage1_scale import Stage1ReviewProjection


class ReadStore:
    def __init__(self, config):
        self.config = config

    def connect(self):
        return Store(self.config).connect()


class ArtifactReads:
    resolve = Artifacts.resolve
    inventory = Artifacts.inventory
    validate = Artifacts.validate
    native = Artifacts.native
    read = Artifacts.read
    listing = Artifacts.listing

    def __init__(self, config):
        self.config = config
        self.store = ReadStore(config)


class DomainReads:
    read = Domains.read

    def __init__(self, config):
        self.config = config
        self.store = ReadStore(config)


class ReviewQueueReads:
    page = Stage1ReviewProjection.page
    _decode_cursor = staticmethod(Stage1ReviewProjection._decode_cursor)
    _encode_cursor = staticmethod(Stage1ReviewProjection._encode_cursor)

    def __init__(self, config):
        self.store = ReadStore(config)


class JobReads:
    _project = staticmethod(CloudJobs._project)
    get = CloudJobs.get

    def __init__(self, config):
        self.store = ReadStore(config)


class ReviewReads:
    _context = ReviewWorkbench._context
    _state = ReviewWorkbench._state
    _sealed = ReviewWorkbench._sealed
    read = ReviewWorkbench.read

    def __init__(self, config):
        self.config = config
        self.store = ReadStore(config)
        self.artifacts = ArtifactReads(config)


class BoundedLedgerReads:
    _load = BoundedExtractionStore._load
    _path = BoundedExtractionStore._path
    _read_artifact = BoundedExtractionStore._read_artifact
    _request = staticmethod(BoundedExtractionStore._request)
    _attempt_id = staticmethod(BoundedExtractionStore._attempt_id)
    _result = BoundedExtractionStore._result
    _final_result = BoundedExtractionStore._final_result

    def __init__(self, config):
        self.config = config
        self.store = ReadStore(config)

    def read(self, series_id):
        with self.store.connect() as connection:
            if schema_version(connection) != "12":
                raise BoundaryError("BOUNDED_SCHEMA_REQUIRED")
            connection.execute("BEGIN")
            return self._load(connection, series_id)


class BoundedReads:
    projection = BoundedSourceAnalysisRunner.projection

    def __init__(self, config):
        self.ledger = BoundedLedgerReads(config)


class OperationalReads:
    _project_run = SourceOperations._project_run
    _post_processing = SourceOperations._post_processing
    _source_projection = staticmethod(SourceOperations._source_projection)
    get_run = SourceOperations.get_run
    source = SourceOperations.source

    def __init__(self, config):
        self.config = config
        self.store = ReadStore(config)
        self.jobs = JobReads(config)
        self.bounded = BoundedReads(config)
        self.output_batches = OutputBatchReads(config)


class OutputBatchReads(BoundedReads):
    projection = OutputDecompositionRunner.projection
