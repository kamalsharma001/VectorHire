"""VectorHire Backend Application Package."""

# Compatibility bridge between Starlette 1.x Router and FastAPI 0.115 APIRouter
try:
    import starlette.routing
    _orig_router_init = starlette.routing.Router.__init__

    def _compat_router_init(self, *args, on_startup=None, on_shutdown=None, **kwargs):
        _orig_router_init(self, *args, **kwargs)
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

    starlette.routing.Router.__init__ = _compat_router_init

    from fastapi import FastAPI
    FastAPI.max_body_size = None
except Exception:
    pass
