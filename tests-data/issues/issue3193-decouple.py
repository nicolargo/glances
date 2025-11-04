# Test python-decouple
# https://github.com/HBNetwork/python-decouple

import os

from decouple import Config, RepositoryIni

GLANCES_CONFIG_FILE = os.environ.get("GLANCES_CONFIG_FILE", "../../conf/glances.conf")
print(f"Using config file: {GLANCES_CONFIG_FILE}")

config = Config(RepositoryIni(GLANCES_CONFIG_FILE))

print(config.get('refresh', cast=int))

# 👉 Python-decouple does not support multiple sections in .ini files natively...
