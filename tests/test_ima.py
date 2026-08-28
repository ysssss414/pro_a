import json
import traceback
from types import SimpleNamespace

import pytest
import requests

from pro_a.config import IMAConfig
from pro_a.ima import IMAClient, IMAError
from ima_helpers import IMASimulator, no_live_services


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    no_live_services(monkeypatch)


@pytest.fixture
def client():
    return IMAClient(IMAConfig(enabled=True, base_url="https://ima.invalid"))


@pytest.mark.parametrize("case,code", [
    ("timeout", "IMA_TIMEOUT"), ("connection", "IMA_CONNECTION_FAILED"),
    (400, "IMA_HTTP_ERROR"), (500, "IMA_HTTP_ERROR"), (302, "IMA_HTTP_ERROR"),
    ("invalid_json", "IMA_INVALID_JSON"), ({"code": 1, "msg": "simulated-api-key"}, "IMA_API_ERROR"),
    ({}, "IMA_INVALID_RESPONSE"), ([], "IMA_INVALID_RESPONSE"),
    ({"code": 0}, "IMA_INVALID_RESPONSE"), ({"code": 0, "data": None}, "IMA_INVALID_RESPONSE"),
    ({"code": 0, "data": []}, "IMA_INVALID_RESPONSE"),
    ({"code": False, "data": {}}, "IMA_INVALID_RESPONSE"),
])
def test_http_errors_are_structured_and_secret_free(monkeypatch, client, case, code):
    def post(*args, **kwargs):
        if case == "timeout":
            raise requests.Timeout("simulated-client-id simulated-api-key")
        if case == "connection":
            raise requests.ConnectionError("simulated-secret-id simulated-secret-key simulated-token")
        def response_json():
            if case == "invalid_json":
                raise ValueError("simulated-token")
            return case
        return SimpleNamespace(status_code=case if type(case) is int else 200,
                               text="simulated-api-key simulated-token", json=response_json)
    monkeypatch.setattr("requests.post", post)
    with pytest.raises(IMAError) as caught:
        client.call("test", {}, stage="duplicate_check")
    assert caught.value.code == code and caught.value.stage == "duplicate_check"
    assert caught.value.remote_state_uncertain is False
    assert "simulated-" not in "".join(traceback.format_exception(caught.value))


def test_http_success_and_environment_only_headers(monkeypatch, client):
    def post(url, **kwargs):
        assert kwargs["headers"] == {"ima-openapi-clientid": "simulated-client-id",
                                      "ima-openapi-apikey": "simulated-api-key", "Content-Type": "application/json"}
        assert kwargs["allow_redirects"] is False
        return SimpleNamespace(status_code=200, json=lambda: {"code": 0, "data": {"ok": True}})
    monkeypatch.setattr("requests.post", post)
    assert client.call("test", {}) == {"ok": True}
    monkeypatch.delenv("IMA_OPENAPI_APIKEY")
    with pytest.raises(IMAError, match="credentials are missing"):
        client.call("test", {})


@pytest.mark.parametrize("field", ["media_id", "cos_credential", "bucket_name", "region", "cos_key", "secret_id", "secret_key", "token"])
def test_create_media_rejects_missing_fields_before_cos(tmp_path, monkeypatch, client, field):
    sim = IMASimulator(monkeypatch)
    (sim.created if field in {"media_id", "cos_credential"} else sim.created["cos_credential"]).pop(field)
    path = tmp_path / "source.txt"
    path.write_text("fixture", encoding="utf-8")
    with pytest.raises(IMAError) as caught:
        client.upload_file(path, "kb")
    exc = caught.value
    assert (exc.code, exc.stage, exc.remote_state_uncertain) == ("CREATE_MEDIA_INVALID_RESPONSE", "create_media", True)
    assert sim.calls == ["duplicate_check", "create_media"]
    assert "simulated-" not in str(exc)


@pytest.mark.parametrize("results", [None, [], [{}], [{"is_repeated": "false"}], [{"is_repeated": False}, {"is_repeated": False}]])
def test_duplicate_check_missing_result_fails_closed(monkeypatch, client, results):
    monkeypatch.setattr(client, "call", lambda *args, **kwargs: {"results": results})
    with pytest.raises(IMAError) as caught:
        client.check_same_name("kb", "", "title", 1)
    assert caught.value.code == "DUPLICATE_CHECK_INVALID_RESPONSE"
    assert not caught.value.remote_state_uncertain


@pytest.mark.parametrize("added", [{}, {"media_id": ""}, {"media_id": "returned-media"}])
def test_upload_cos_sdk_contract_and_final_media_id(tmp_path, monkeypatch, client, added):
    sim = IMASimulator(monkeypatch)
    sim.added = added
    # Existing API accepts either bucket alias.
    sim.created["cos_credential"]["bucket"] = sim.created["cos_credential"].pop("bucket_name")
    path = tmp_path / "source.pdf"
    path.write_bytes(b"fixture")
    result = client.upload_file(path, "kb", "folder", title="[SRC_1] source.pdf")
    assert sim.calls == ["duplicate_check", "create_media", "cos_upload", "add_knowledge"]
    assert sim.cos_args == {"Bucket": "simulated-bucket", "Key": "simulated-cos-key", "LocalFilePath": str(path), "EnableMD5": False}
    assert sim.add_payload["folder_id"] == "folder" and sim.add_payload["title"] == "[SRC_1] source.pdf"
    assert result == {"skipped": False, "media_id": added.get("media_id") or "simulated-media"}
    assert "cos" not in json.dumps(result)


def test_cos_failure_does_not_expose_sdk_secrets(tmp_path, monkeypatch, client):
    sim = IMASimulator(monkeypatch)
    sim.fail_stage = "cos_upload"
    path = tmp_path / "source.txt"
    path.write_text("fixture", encoding="utf-8")
    with pytest.raises(IMAError) as caught:
        client.upload_file(path, "kb")
    assert caught.value.stage == "cos_upload" and caught.value.media_id == "simulated-media"
    assert caught.value.remote_state_uncertain
    assert "simulated-secret" not in "".join(traceback.format_exception(caught.value))
    assert "simulated-token" not in str(caught.value)
