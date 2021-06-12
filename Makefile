PORT?=8008
LASTTAG = $(shell git describe --tags --abbrev=0)

install:
	sensible-browser "https://github.com/nicolargo/glances#installation"

venv-python:
	virtualenv -p /usr/bin/python3 venv

venv-dev:
	./venv/bin/pip install -r dev-requirements.txt
	./venv/bin/pip install -r doc-requirements.txt

venv-dev-upgrade:
	./venv/bin/pip install --upgrade -r dev-requirements.txt
	./venv/bin/pip install --upgrade -r doc-requirements.txt

venv:
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r optional-requirements.txt

venv-upgrade:
	./venv/bin/pip install --upgrade -r dev-requirements.txt
	./venv/bin/pip install --upgrade -r requirements.txt
	./venv/bin/pip install --upgrade -r optional-requirements.txt

test: venv
	./venv/bin/python ./unitest.py
	./venv/bin/python ./unitest-restful.py
	./venv/bin/python ./unitest-xmlrpc.py

docs: venv-dev
	cd docs && ./build.sh

docs-server: docs
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && ./venv/bin/python -m SimpleHTTPServer $(PORT)

webui: venv-dev
	cd glances/outputs/static/ && npm install && npm audit fix && npm run build

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

profiling: venv venv-dev
	@echo "Please complete and run: sudo ./venv/bin/py-spy record -o ./docs/_static/glances-flame.svg -d 60 -s --pid <GLANCES PID>"

release-note:
	git --no-pager log $(LASTTAG)..HEAD --first-parent --pretty=format:"* %s (by %an)"

.PHONY: test docs docs-server
