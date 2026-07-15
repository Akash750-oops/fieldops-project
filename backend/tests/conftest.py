import pytest
import app.database
import app.redis_client

# Store original references
_orig_session_local = app.database.SessionLocal
_orig_get_redis = app.redis_client.get_redis_client

_current_request = None
_last_request_module = None

def dynamic_get_redis_client():
    module = None
    if _current_request and _current_request.module:
        module = _current_request.module
    elif _last_request_module:
        module = _last_request_module

    if module:
        for attr_name in ("fake_redis", "fake_sync_redis", "mock_redis", "fake_async_redis"):
            if hasattr(module, attr_name):
                return getattr(module, attr_name)
    return _orig_get_redis()

def dynamic_session_local(*args, **kwargs):
    module = None
    if _current_request and _current_request.module:
        module = _current_request.module
    elif _last_request_module:
        module = _last_request_module

    if module and hasattr(module, "TestingSessionLocal"):
        return getattr(module, "TestingSessionLocal")(*args, **kwargs)
    return _orig_session_local(*args, **kwargs)

# Apply global dynamic routing before importing main application
app.database.SessionLocal = dynamic_session_local
app.redis_client.get_redis_client = dynamic_get_redis_client

# Helper to prevent global import-time monkeypatch overwrites in test modules
def make_write_resistant(module_name):
    import sys
    if module_name in sys.modules:
        mod = sys.modules[module_name]
        class CustomModule(mod.__class__):
            def __setattr__(self, name, value):
                if name in ("SessionLocal", "get_redis_client"):
                    return
                super().__setattr__(name, value)
        mod.__class__ = CustomModule

make_write_resistant("app.database")
make_write_resistant("app.redis_client")

import app.main
from app.celery_app import celery_app

# Configure Celery eagerly for all tests
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True
)

app.main.SessionLocal = dynamic_session_local

make_write_resistant("app.main")
import app.services.tracking_manager
make_write_resistant("app.services.tracking_manager")
try:
    import app.routes.tracking
    make_write_resistant("app.routes.tracking")
except ImportError:
    pass

@pytest.fixture(autouse=True)
def track_current_request(request):
    global _current_request, _last_request_module
    _current_request = request
    if request.module:
        _last_request_module = request.module
    yield
    _current_request = None
