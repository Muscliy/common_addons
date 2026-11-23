from contextlib import contextmanager
from contextvars import ContextVar

_active = ContextVar("workflow_project_sync", default=frozenset())


def _key(link):
    return link.env.cr.dbname, id(link.env.cr), link.id


def is_syncing(link) -> bool:
    return _key(link) in _active.get()


@contextmanager
def syncing(link):
    token = _active.set(_active.get() | {_key(link)})
    try:
        yield
    finally:
        _active.reset(token)
