from .bootstrap import Runtime
from .transport.api.application import create_app

app = create_app(Runtime())
