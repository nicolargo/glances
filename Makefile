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

venv-dev-upgrade: ## Upgrade Python 3 dev dependencies
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install --upgrade -r dev-requirements.txt
	./venv/bin/pip install --upgrade -r doc-requirements.txt

venv: venv-python ## Install Python 3 run-time dependencies
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r optional-requirements.txt

venv-upgrade: ## Upgrade Python 3 run-time dependencies
	./venv/bin/pip install --upgrade -r requirements.txt
	./venv/bin/pip install --upgrade -r optional-requirements.txt

# ===================================================================
# Tests
# ===================================================================

test: ## Run unit tests
	./venv/bin/python ./unitest.py
	./venv/bin/python ./unitest-restful.py
	./venv/bin/python ./unitest-xmlrpc.py
	./venv/bin/python -m black ./glances --check --exclude outputs/static
	./venv/bin/pyright glances

test-with-upgrade: venv-upgrade venv-dev-upgrade ## Run unit tests
	./venv/bin/python ./unitest.py
	./venv/bin/python ./unitest-restful.py
	./venv/bin/python ./unitest-xmlrpc.py
	./venv/bin/python -m black ./glances --check --exclude outputs/static
	./venv/bin/pyright glances

# ===================================================================
# Linters and profilers
# ===================================================================

format: venv-dev-upgrade ## Format the code
	@git ls-files '*.py' | xargs ./venv/bin/python -m autopep8 --in-place --jobs 0 --global-config=.flake8
	@git ls-files '*.py' | xargs ./venv/bin/python -m autoflake --in-place --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --exclude="compat.py,globals.py"
	./venv/bin/python -m black ./glances --exclude outputs/static

flake8: venv-dev-upgrade ## Run flake8 linter.
	@git ls-files '*.py' | xargs ./venv/bin/python -m flake8 --config=.flake8

codespell: venv-dev-upgrade ## Run codespell to fix common misspellings in text files
	./venv/bin/codespell -S .git,./docs/_build,./Glances.egg-info,./venv,./glances/outputs,*.svg -L hart,bu,te,statics

profiling: ## How to start the profiling of the Glances software
	@echo "Please complete and run: sudo ./venv/bin/py-spy record -o ./docs/_static/glances-flame.svg -d 60 -s --pid <GLANCES PID>"

trace-malloc: ## Trace the malloc() calls
	@echo "Malloc test is running, please wait ~30 secondes..."
	./venv/bin/python -m glances -C ./conf/glances.conf --trace-malloc --stop-after 15 --quiet

memory-leak: ## Profile memory leaks
	./venv/bin/python -m glances -C ./conf/glances.conf --memory-leak

memory-profiling: ## Profile memory usage
	@echo "It's a very long test (~4 hours)..."
	rm -f mprofile_*.dat
	@echo "1/2 - Start memory profiling with the history option enable"
	./venv/bin/mprof run -T 1 -C run.py -C ./conf/glances.conf --stop-after 2400 --quiet
	./venv/bin/mprof plot --output ./docs/_static/glances-memory-profiling-with-history.png
	rm -f mprofile_*.dat
	@echo "2/2 - Start memory profiling with the history option disable"
	./venv/bin/mprof run -T 1 -C run.py -C ./conf/glances.conf --disable-history --stop-after 2400 --quiet
	./venv/bin/mprof plot --output ./docs/_static/glances-memory-profiling-without-history.png
	rm -f mprofile_*.dat

# ===================================================================
# Docs
# ===================================================================

docs: venv-dev-upgrade ## Create the documentation
	./venv/bin/python -m glances -C ./conf/glances.conf --api-doc > ./docs/api.rst
	cd docs && ./build.sh && cd ..

docs-server: docs ## Start a Web server to serve the documentation
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && ../../../venv/bin/python -m http.server $(PORT)

release-note: ## Generate release note
	git --no-pager log $(LASTTAG)..HEAD --first-parent --pretty=format:"* %s"
	@echo "\n"
	git --no-pager shortlog -s -n $(LASTTAG)..HEAD

# ===================================================================
# WebUI
# ===================================================================

webui: venv-dev-upgrade ## Build the Web UI
	cd glances/outputs/static/ && npm ci && npm run build

webui-audit: venv-dev-upgrade ## Audit the Web UI
	cd glances/outputs/static/ && npm audit

webui-audit-fix: venv-dev-upgrade ## Fix audit the Web UI
	cd glances/outputs/static/ && npm audit fix && npm ci && npm run build

# ===================================================================
# Packaging
# ===================================================================

flatpak: venv-dev-upgrade ## Generate FlatPack JSON file
	git clone https://github.com/flatpak/flatpak-builder-tools.git
	./venv/bin/python ./flatpak-builder-tools/pip/flatpak-pip-generator glances
	rm -rf ./flatpak-builder-tools
	@echo "Now follow: https://github.com/flathub/flathub/wiki/App-Submission"

# ===================================================================
# Docker
# ===================================================================

docker: docker-alpine ## Generate local docker images

docker-alpine: ## Generate local docker images (Alpine)
	docker build --target full -f ./docker-files/alpine.Dockerfile -t glances:local-alpine-full .
	docker build --target minimal -f ./docker-files/alpine.Dockerfile -t glances:local-alpine-minimal .
	docker build --target dev -f ./docker-files/alpine.Dockerfile -t glances:local-alpine-dev .

# ===================================================================
# Run
# ===================================================================

run: ## Start Glances in console mode (also called standalone)
	./venv/bin/python -m glances -C ./conf/glances.conf

run-debug: ## Start Glances in debug console mode (also called standalone)
	./venv/bin/python -m glances -C ./conf/glances.conf -d

run-local-conf: ## Start Glances in console mode with the system conf file
	./venv/bin/python -m glances

run-docker-alpine-minimal: ## Start Glances Alpine Docker minimal in console mode
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host --network host -it glances:local-alpine-minimal

run-docker-alpine-full: ## Start Glances Alpine Docker full in console mode
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host --network host -it glances:local-alpine-full

run-docker-alpine-dev: ## Start Glances Alpine Docker dev in console mode
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host --network host -it glances:local-alpine-dev

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

.PHONY: test docs docs-server venv
