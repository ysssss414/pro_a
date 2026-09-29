"""Reuse operational read methods without constructing write-capable services.

Only the selected existing methods are bound here. There is no profile, provider,
worker, retry, initialization or mutation method on either facade. Nested domain
reads retain Store's mode=ro/query_only and registered-artifact checks.
"""
from pro_a.workbench.cloud_jobs import CloudJobs
from pro_a.workbench.source_operations import SourceOperations
from pro_a.workbench.store import Store


class JobReads:
    _project = staticmethod(CloudJobs._project)
    get = CloudJobs.get

    def __init__(self, config):
        self.store = Store(config)


class OperationalReads:
    _project_run = SourceOperations._project_run
    _post_processing = SourceOperations._post_processing
    _source_projection = staticmethod(SourceOperations._source_projection)
    get_run = SourceOperations.get_run
    source = SourceOperations.source

    def __init__(self, config):
        self.config = config
        self.store = Store(config)
        self.jobs = JobReads(config)
