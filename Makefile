PORT?=8008
LASTTAG = $(shell git describe --tags --abbrev=0)

# if the command is only `make`, the default tasks will be the printing of the help.
.DEFAULT_GOAL := help

.PHONY: help
help: ## List all make commands available
	@grep -E '^[\.a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk -F ":" '{print $1}' | grep -v % | sed 's/\\//g' | sort | awk 'BEGIN {FS = ":[^:]*?##"}; {printf "\033[1;34mmake %-50s\033[0m %s\n", $$1, $$2}'

install: ## Open a Web Browser to the installation procedure
	sensible-browser "https://github.com/nicolargo/glances#installation"

venv-python: ## Install Python 3 venv
	virtualenv -p /usr/bin/python3 venv

venv-dev: venv-python ## Install Python 3 dev dependencies
	./venv/bin/pip install -r dev-requirements.txt
	./venv/bin/pip install -r doc-requirements.txt

venv-dev-upgrade: venv-dev ## Upgrade Python 3 dev dependencies
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install --upgrade -r dev-requirements.txt
	./venv/bin/pip install --upgrade -r doc-requirements.txt

venv: venv-python ## Install Python 3 run-time dependencies
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r optional-requirements.txt

venv-upgrade: venv ## Upgrade Python 3 run-time dependencies
	./venv/bin/pip install --upgrade -r dev-requirements.txt
	./venv/bin/pip install --upgrade -r requirements.txt
	./venv/bin/pip install --upgrade -r optional-requirements.txt

test: venv-upgrade venv-dev-upgrade ## Run unit tests
	./venv/bin/python ./unitest.py
	./venv/bin/python ./unitest-restful.py
	./venv/bin/python ./unitest-xmlrpc.py
	./venv/bin/python -m black ./glances --check --exclude outputs/static
	./venv/bin/pyright glances

format: venv-dev-upgrade ## Format the code
	./venv/bin/python -m black ./glances --exclude outputs/static

docs: venv-dev-upgrade ## Create the documentation
	./venv/bin/python -m glances -C ./conf/glances.conf --api-doc > ./docs/api.rst
	cd docs && ./build.sh && cd ..

docs-server: docs ## Start a Web server to serve the documentation
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && ../../../venv/bin/python -m http.server $(PORT)

webui: venv-dev-upgrade ## Build the Web UI
	cd glances/outputs/static/ && npm ci && npm run build

webui-audit: venv-dev-upgrade ## Audit the Web UI
	cd glances/outputs/static/ && npm audit

run: ## Start Glances in console mode (also called standalone)
	./venv/bin/python -m glances -C ./conf/glances.conf

run-debug: ## Start Glances in debug console mode (also called standalone)
	./venv/bin/python -m glances -C ./conf/glances.conf -d

run-webserver: ## Start Glances in Web server mode
	./venv/bin/python -m glances -C ./conf/glances.conf -w

run-restapiserver: ## Start Glances in REST API server mode
	./venv/bin/python -m glances -C ./conf/glances.conf -w --disable-webui

run-server: ## Start Glances in server mode (RPC)
	./venv/bin/python -m glances -C ./conf/glances.conf -s

run-client: ## Start Glances in client mode (RPC)
	./venv/bin/python -m glances -C ./conf/glances.conf -c localhost

run-browser: ## Start Glances in browser mode (RPC)
	./venv/bin/python -m glances -C ./conf/glances.conf --browser

show-version: ## Show Glances version number
	./venv/bin/python -m glances -C ./conf/glances.conf -V

show-issue: ## Generate output for a new issue
	./venv/bin/python -m glances -C ./conf/glances.conf --issue

profiling: ## How to start the profiling of the Glances software
	@echo "Please complete and run: sudo ./venv/bin/py-spy record -o ./docs/_static/glances-flame.svg -d 60 -s --pid <GLANCES PID>"

trace-malloc: ## Trace the malloc() calls
	@echo "Malloc test is running, please wait ~30 secondes..."
	./venv/bin/python -m glances -C ./conf/glances.conf --trace-malloc --stop-after 15 --quiet

memory-leak: ## Profile memory leaks
	./venv/bin/python -m glances -C ./conf/glances.conf --memory-leak

release-note: ## Generate release note
	git --no-pager log $(LASTTAG)..HEAD --first-parent --pretty=format:"* %s"
	@echo "\n"
	git --no-pager shortlog -s -n $(LASTTAG)..HEAD

flatpak: venv-dev-upgrade ## Generate FlatPack JSON file
	git clone https://github.com/flatpak/flatpak-builder-tools.git
	./venv/bin/python ./flatpak-builder-tools/pip/flatpak-pip-generator glances
	rm -rf ./flatpak-builder-tools
	@echo "Now follow: https://github.com/flathub/flathub/wiki/App-Submission"

.PHONY: test docs docs-server venv
