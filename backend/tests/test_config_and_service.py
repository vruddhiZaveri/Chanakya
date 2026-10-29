import asyncio

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import BackendError
from app.llm.ollama import strict_json
from app.schemas import BaselineRequest
from app.services.baseline import BaselineService
from conftest import envelope, registry


@pytest.mark.parametrize("url", ["https://remote.example", "http://remote.example:11434", "http://user:secret@localhost:11434", "http://localhost:11434/path", "http://localhost:11434?x=y"])
def test_remote_and_credential_endpoints_blocked(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ollama_base_url=url)


def test_cloud_tag_and_large_runtime_config_blocked():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, model_name="qwen:cloud")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, context_tokens=32768)


def test_duplicate_keys_and_nonfinite_json_rejected():
    for text in ['{"a":1,"a":2}', '{"score":NaN}']:
        with pytest.raises(ValueError):
            strict_json(text)


def test_concurrent_request_is_rejected_and_lock_released():
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        class Provider:
            async def installed_model(self):
                return registry()["models"][0]
            async def generate(self, messages, schema):
                started.set()
                await release.wait()
                return envelope()
        service = BaselineService(Provider(), Settings(_env_file=None))
        payload = BaselineRequest(mode="source_grounded", question="Is the pilot approved?", sources=[{"id": "S1", "title": "Test", "excerpt": "A pilot is approved."}])
        first = asyncio.create_task(service.run(payload, "first"))
        await started.wait()
        with pytest.raises(BackendError, match="already active") as error:
            await service.run(payload, "second")
        assert error.value.status == 429
        release.set()
        assert (await first).request_id == "first"
        assert (await service.run(payload, "third")).request_id == "third"
    asyncio.run(scenario())


def test_total_deadline_and_cancellation_release_lock():
    async def scenario():
        class Provider:
            async def installed_model(self):
                await asyncio.Event().wait()
        service = BaselineService(Provider(), Settings(_env_file=None, request_timeout_seconds=.01))
        payload = BaselineRequest(question="Explain an evidence based decision.")
        with pytest.raises(BackendError) as error:
            await service.run(payload, "timeout")
        assert error.value.code == "model_timeout" and not service._lock.locked()
        task = asyncio.create_task(service.run(payload, "cancel"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not service._lock.locked()
    asyncio.run(scenario())
