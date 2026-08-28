"""In-process HTTP/COS simulators; never use real credentials or cloud services."""

from copy import deepcopy
from types import SimpleNamespace


def created_media():
    return {"media_id": "simulated-media", "cos_credential": {
        "bucket_name": "simulated-bucket", "region": "simulated-region", "cos_key": "simulated-cos-key",
        "secret_id": "simulated-secret-id", "secret_key": "simulated-secret-key", "token": "simulated-token",
    }}


class IMASimulator:
    def __init__(self, monkeypatch):
        self.calls = []
        self.repeated = False
        self.fail_stage = ""
        self.created = created_media()
        self.added = {"media_id": "simulated-media"}
        self.on_duplicate = None
        monkeypatch.setattr("requests.post", self.post)
        monkeypatch.setitem(__import__("sys").modules, "qcloud_cos", SimpleNamespace(
            CosConfig=lambda **kwargs: kwargs, CosS3Client=lambda config: SimpleNamespace(upload_file=self.cos_upload)))

    def post(self, url, *, json, headers, timeout, allow_redirects):
        import requests

        assert url.startswith("https://ima.invalid/")
        assert headers["ima-openapi-clientid"] == "simulated-client-id"
        assert headers["ima-openapi-apikey"] == "simulated-api-key"
        assert timeout == 90 and allow_redirects is False
        name = url.rsplit("/", 1)[-1]
        stage = {"check_repeated_names": "duplicate_check", "create_media": "create_media", "add_knowledge": "add_knowledge"}[name]
        self.calls.append(stage)
        if stage == "duplicate_check" and self.on_duplicate:
            self.on_duplicate()
        if stage == self.fail_stage:
            raise requests.Timeout("simulated-api-key simulated-token must never appear in diagnostics")
        if stage == "duplicate_check":
            data = {"results": [{"is_repeated": self.repeated}]}
            self.duplicate_payload = deepcopy(json)
        elif stage == "create_media":
            data = self.created
            self.create_payload = deepcopy(json)
        else:
            data = self.added
            self.add_payload = deepcopy(json)
        return SimpleNamespace(status_code=200, json=lambda: {"code": 0, "data": deepcopy(data)})

    def cos_upload(self, **kwargs):
        self.calls.append("cos_upload")
        self.cos_args = kwargs
        if self.fail_stage == "cos_upload":
            raise RuntimeError("simulated-secret-id simulated-secret-key simulated-token")


def enable_ima(cfg):
    cfg.ima.enabled = True
    cfg.ima.source_kb_id = "simulated-source-kb"
    cfg.ima.source_folder_id = "simulated-source-folder"
    cfg.ima.base_url = "https://ima.invalid"


def no_live_services(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Live network/LLM/Propagation is forbidden during IMA acceptance")
    monkeypatch.setenv("IMA_OPENAPI_CLIENTID", "simulated-client-id")
    monkeypatch.setenv("IMA_OPENAPI_APIKEY", "simulated-api-key")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    monkeypatch.setattr("pro_a.llm.ChatLLM.json", forbidden)
    monkeypatch.setattr("pro_a.proposals.ProposalManager.accept", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager.start_from_accepted_view", forbidden)
    monkeypatch.setattr("pro_a.propagation.PropagationManager.enqueue_from_accepted_view", forbidden)
