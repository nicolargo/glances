# Test Dynaconf
# https://www.dynaconf.com/

import os

from dynaconf import Dynaconf, Validator

GLANCES_CONFIG_FILE = os.environ.get("GLANCES_CONFIG_FILE", "../../conf/glances.conf")
print(f"Using config file: {GLANCES_CONFIG_FILE}")

settings = Dynaconf(settings_files=[GLANCES_CONFIG_FILE])

# Cast and validate settings
settings.validators.register(Validator("global.refresh", cast=int, gte=1))
settings.validators.validate()


# print(settings.global.refresh) <== global is a Python keyword so error
# read as a string from ini file
assert settings.get('global').get('refresh') == 2
assert settings.GLOBAL.refresh == 2
assert settings['global']['refresh'] == 2
assert settings['global.refresh'] == 2
