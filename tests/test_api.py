from fastapi.testclient import TestClient

from face_blur.api.app import create_app


class DummyBackend:
    async def get_result(self, task_id):
        return None


class DummyBroker:
    def __init__(self):
        self.result_backend: DummyBackend = DummyBackend()

    async def startup(self):
        return None

    async def shutdown(self):
        return None


class DummyTask:
    def __init__(self, task_id):
        self.task_id = task_id


async def fake_submitter(payload):
    return DummyTask("test-task")


def test_health_endpoint():
    app = create_app(broker_instance=DummyBroker(), task_submitter=fake_submitter)
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_blur_rejects_unsupported_extension():
    app = create_app(broker_instance=DummyBroker(), task_submitter=fake_submitter)
    with TestClient(app) as client:
        response = client.post(
            "/blur",
            files={"files": ("bad.gif", b"data", "image/gif")},
        )
    assert response.status_code == 415
    payload = response.json()
    assert payload["code"] == "unsupported_media_type"


def test_blur_returns_task_id():
    app = create_app(broker_instance=DummyBroker(), task_submitter=fake_submitter)
    with TestClient(app) as client:
        minimal_jpeg = b"\xff\xd8\xff" + b"\x00" * 16
        response = client.post(
            "/blur",
            files={"files": ("sample.jpg", minimal_jpeg, "image/jpeg")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["task_id"] == "test-task"


def test_results_pending():
    app = create_app(broker_instance=DummyBroker(), task_submitter=fake_submitter)
    with TestClient(app) as client:
        response = client.get("/results/test-task")
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
