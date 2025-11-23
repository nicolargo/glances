import json
from unittest.mock import patch

from fastapi.openapi.utils import get_openapi

from glances.main import GlancesMain

# sys.path.append('./glances/outputs')
from glances.outputs.glances_restful_api import GlancesRestfulApi

# Init Glances core
testargs = ["glances", "-C", "./conf/glances.conf"]
with patch('sys.argv', testargs):
    core = GlancesMain()
test_config = core.get_config()
test_args = core.get_args()

app = GlancesRestfulApi(config=test_config, args=test_args)._app

with open('./docs/api/openapi.json', 'w') as f:
    json.dump(
        get_openapi(
            title=app.title,
            version=app.version,
            # Set the OenAPI version
            # It's an hack to make openapi.json compatible with tools like https://editor.swagger.io/
            # Please read https://fastapi.tiangolo.com/reference/fastapi/?h=openapi#fastapi.FastAPI.openapi_version
            openapi_version="3.0.2",
            description=app.description,
            routes=app.routes,
        ),
        f,
    )
