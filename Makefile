PORT?=8008

install:
	sensible-browser "https://github.com/nicolargo/glances#installation"

test:
	./unitest-all.sh

docs:
	cd docs && ./build.sh

docs-server: docs
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && ./venv/bin/python -m SimpleHTTPServer $(PORT)

webui:
	cd glances/outputs/static/ && npm install && npm audit fix && npm run build

venv:
	virtualenv -p /usr/bin/python3 venv
	./venv/bin/pip install -r ./docs/doc-requirements.txt
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r optional-requirements.txt

venv-upgrade:
	./venv/bin/pip install --upgrade -r ./docs/doc-requirements.txt
	./venv/bin/pip install --upgrade -r requirements.txt
	./venv/bin/pip install --upgrade -r optional-requirements.txt

run: venv
	./venv/bin/python -m glances -C ./conf/glances.conf

run-debug: venv
	./venv/bin/python -m glances -C ./conf/glances.conf -d

run-webserver: venv
	./venv/bin/python -m glances -C ./conf/glances.conf -w

run-server: venv
	./venv/bin/python -m glances -C ./conf/glances.conf -s

run-client: venv
	./venv/bin/python -m glances -C ./conf/glances.conf -c localhost

.PHONY: test docs docs-server
