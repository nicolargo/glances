import json

from fastapi.openapi.utils import get_openapi

from glances.config_v5 import GlancesConfigV5
from glances.main_v5 import assemble, build_parser

# Build the Glances server app without running it
args = build_parser().parse_args(["-s", "--disable-autodiscover", "-C", "./conf/glances.conf"])
app = assemble(args, GlancesConfigV5(cli_config_path="./conf/glances.conf"))[0]

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
