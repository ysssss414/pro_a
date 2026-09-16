"""Reusable registered synthetic input for Stage 6 durable cloud jobs."""
from pro_a.workbench.artifacts import Artifacts
from pro_a.workbench.attribution_store import prepare_attribution
from pro_a.workbench.cloud_jobs import CloudJobs, CloudProfile, prepare_cloud_jobs
from pro_a.workbench.impact_store import prepare_impact
from pro_a.workbench.research_store import prepare_research
from pro_a.workbench.review_store import prepare_reviews
from pro_a.workbench.store import Store
from pro_a.workbench.view_store import prepare_current_views
from workbench_fixture import make_fixture


def stage6_fixture(root, *, origin="http://127.0.0.1:8000", profile=None):
    value = make_fixture(root, origin=origin)
    config = value["config"]
    Store(config).initialize()
    prepare_reviews(config)
    prepare_attribution(config)
    prepare_current_views(config)
    prepare_impact(config)
    prepare_research(config)
    before = config.state_db.read_bytes()
    prepared = prepare_cloud_jobs(config)
    registered = Artifacts(config).register(value["packet_relative"], value["run_relative"])
    selected_profile = profile or CloudProfile.demo()
    return {**value, "prepared": prepared, "stage5_bytes": before,
            "artifact_id": registered["artifact_id"],
            "jobs": CloudJobs(config, selected_profile), "profile": selected_profile}
