PORT     ?= 8008
VENV     := venv/bin
VENV_DEV := venv-dev/bin
VENV_MIN := venv-min/bin
CONF     := conf/glances.conf
PIP      := $(VENV)/pip
PYTHON   := $(VENV)/python
LASTTAG  = $(shell git describe --tags --abbrev=0)

IMAGES_TYPES      := full minimal dev
ALPINE_IMAGES     := $(IMAGES_TYPES:%=docker-alpine-%)
UBUNTU_IMAGES     := $(IMAGES_TYPES:%=docker-ubuntu-%)
DOCKER_IMAGES     := $(ALPINE_IMAGES) $(UBUNTU_IMAGES)
DOCKER_RUNTIMES   := $(DOCKER_IMAGES:%=run-%)
UNIT_TESTS        := test-core test-restful test-xmlrpc
DOCKER_BUILD      := docker buildx build
DOCKER_RUN        := docker run
PODMAN_SOCK       ?= /run/user/$(shell id -u)/podman/podman.sock
DOCKER_SOCK       ?= /var/run/docker.sock
DOCKER_SOCKS      := -v $(PODMAN_SOCK):$(PODMAN_SOCK):ro -v $(DOCKER_SOCK):$(DOCKER_SOCK):ro
DOCKER_OPTS       := --rm -e TZ="${TZ}" -e GLANCES_OPT="" --pid host --network host

define DOCKER_TAG
glances:local-$*
endef

# if the command is only `make`, the default tasks will be the printing of the help.
.DEFAULT_GOAL := help

.PHONY: help test docs docs-server venv venv-min venv-dev

help: ## List all make commands available
	@grep -E '^[\.a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk -F ":" '{print $1}' | \
	grep -v % | \
	sed 's/\\//g' | \
	sort | \
	awk 'BEGIN {FS = ":[^:]*?##"}; {printf "\033[1;34mmake %-50s\033[0m %s\n", $$1, $$2}'

# ===================================================================
# Virtualenv
# ===================================================================

venv-python: venv-full-python venv-min-python venv-dev-python ## Install all Python 3 venv

venv: venv-full venv-min venv-dev ## Install all Python 3 dependencies

venv-upgrade: venv-full-upgrade venv-min-upgrade venv-dev-upgrade ## Upgrade all Python 3 dependencies

# For full installation (with optional dependencies)

venv-full-python: ## Install Python 3 venv
	virtualenv -p /usr/bin/python3 venv

venv-full: venv-python ## Install Python 3 run-time dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install -r optional-requirements.txt

venv-full-upgrade: ## Upgrade Python 3 run-time dependencies
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements.txt
	$(PIP) install --upgrade -r optional-requirements.txt

# For minimal installation (without optional dependencies)

venv-min-python: ## Install Python 3 venv minimal
	virtualenv -p /usr/bin/python3 venv-min

venv-min: venv-min-python ## Install Python 3 minimal run-time dependencies
	$(VENV_MIN)/pip install -r requirements.txt

venv-min-upgrade: ## Upgrade Python 3 minimal run-time dependencies
	$(VENV_MIN)/pip install --upgrade pip
	$(VENV_MIN)/pip install --upgrade -r requirements.txt

# For development

venv-dev-python: ## Install Python 3 venv
	virtualenv -p /usr/bin/python3 venv-dev

venv-dev: venv-python ## Install Python 3 dev dependencies
	$(VENV_DEV)/pip install -r dev-requirements.txt
	$(VENV_DEV)/pip install -r doc-requirements.txt
	$(VENV_DEV)/pre-commit install --hook-type pre-commit

venv-dev-upgrade: ## Upgrade Python 3 dev dependencies
	$(VENV_DEV)/pip install --upgrade pip
	$(VENV_DEV)/pip install --upgrade -r dev-requirements.txt
	$(VENV_DEV)/pip install --upgrade -r doc-requirements.txt

# ===================================================================
# Tests
# ===================================================================

$(UNIT_TESTS): test-%: unittest-%.py
	$(PYTHON) $<

test-core: ## Run core unit tests
test-restful: ## Run Restful unit tests
test-xmlrpc: ## Run XMLRPC unit tests

test: $(UNIT_TESTS) ## Run unit tests

test-with-upgrade: venv-upgrade venv-dev-upgrade test ## Upgrade deps and run unit tests

test-min: ## Run core unit tests in minimal environment
	$(VENV_MIN)/python unittest-core.py

test-min-with-upgrade: venv-min-upgrade ## Upgrade deps and run unit tests in minimal environment
	$(VENV_MIN)/python unittest-core.py

# ===================================================================
# Linters, profilers and cyber security
# ===================================================================

format: ## Format the code
	$(VENV_DEV)/python -m ruff format .

lint: ## Lint the code.
	$(VENV_DEV)/python -m ruff check . --fix

codespell: ## Run codespell to fix common misspellings in text files
	$(VENV_DEV)/codespell -S .git,./docs/_build,./Glances.egg-info,./venv*,./glances/outputs,*.svg -L hart,bu,te,statics -w

semgrep: ## Run semgrep to find bugs and enforce code standards
	$(VENV_DEV)/semgrep scan --config=auto

profiling-gprof: ## Callgraph profiling (need "apt install graphviz")
	@echo "Start Glances for 30 iterations (more or less 1 mins, please do not exit !)"
	sleep 3
	$(PYTHON) -m cProfile -o ./glances.cprof ./run.py --stop-after 30
	$(VENV_DEV)/gprof2dot -f pstats ./glances.cprof | dot -Tsvg -o ./docs/_static/glances-cgraph.svg
	rm -f ./glances.cprof

profiling-pyinstrument: ## PyInstrument profiling
	@echo "Start Glances for 30 iterations (more or less 1 mins, please do not exit !)"
	sleep 3
	$(PIP) install pyinstrument
	$(PYTHON) -m pyinstrument -r html -o ./docs/_static/glances-pyinstrument.html -m glances --stop-after 30

profiling-pyspy: ## Flame profiling (currently not compatible with Python 3.12)
	@echo "Start Glances for 30 iterations (more or less 1 mins, please do not exit !)"
	sleep 3
	$(VENV_DEV)/py-spy record -o ./docs/_static/glances-flame.svg -d 60 -s -- $(PYTHON) ./run.py --stop-after 30

profiling: profiling-gprof profiling-pyinstrument profiling-pyspy ## Profiling of the Glances software

trace-malloc: ## Trace the malloc() calls
	@echo "Malloc test is running, please wait ~30 secondes..."
	$(PYTHON) -m glances -C $(CONF) --trace-malloc --stop-after 15 --quiet

memory-leak: ## Profile memory leaks
	$(PYTHON) -m glances -C $(CONF) --memory-leak

memory-profiling: ## Profile memory usage
	@echo "It's a very long test (~4 hours)..."
	rm -f mprofile_*.dat
	@echo "1/2 - Start memory profiling with the history option enable"
	$(VENV_DEV)/mprof run -T 1 -C run.py -C $(CONF) --stop-after 2400 --quiet
	$(VENV_DEV)/mprof plot --output ./docs/_static/glances-memory-profiling-with-history.png
	rm -f mprofile_*.dat
	@echo "2/2 - Start memory profiling with the history option disable"
	$(VENV_DEV)/mprof run -T 1 -C run.py -C $(CONF) --disable-history --stop-after 2400 --quiet
	$(VENV_DEV)/mprof plot --output ./docs/_static/glances-memory-profiling-without-history.png
	rm -f mprofile_*.dat

# Trivy installation: https://aquasecurity.github.io/trivy/latest/getting-started/installation/
trivy: ## Run Trivy to find vulnerabilities in container images
	trivy fs .

# ===================================================================
# Docs
# ===================================================================

docs: ## Create the documentation
	$(PYTHON) -m glances -C $(CONF) --api-doc > ./docs/api.rst
	cd docs && ./build.sh && cd ..

docs-server: docs ## Start a Web server to serve the documentation
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && ../../../venv/bin/python -m http.server $(PORT)

release-note: ## Generate release note
	git --no-pager log $(LASTTAG)..HEAD --first-parent --pretty=format:"* %s"
	@echo "\n"
	git --no-pager shortlog -s -n $(LASTTAG)..HEAD

install: ## Open a Web Browser to the installation procedure
	sensible-browser "https://github.com/nicolargo/glances#installation"

# ===================================================================
# WebUI
# Follow ./glances/outputs/static/README.md for more information
# ===================================================================

webui: ## Build the Web UI
	cd glances/outputs/static/ && npm ci && npm run build

webui-audit: ## Audit the Web UI
	cd glances/outputs/static/ && npm audit

webui-audit-fix: ## Fix audit the Web UI
	cd glances/outputs/static/ && npm audit fix && npm ci && npm run build

# ===================================================================
# Packaging
# ===================================================================

flatpak: venv-dev-upgrade ## Generate FlatPack JSON file
	git clone https://github.com/flatpak/flatpak-builder-tools.git
	$(PYTHON) ./flatpak-builder-tools/pip/flatpak-pip-generator glances
	rm -rf ./flatpak-builder-tools
	@echo "Now follow: https://github.com/flathub/flathub/wiki/App-Submission"

# Snap package is automatically build on the Snapcraft.io platform
# https://snapcraft.io/glances
# But you can try an offline build with the following command
snapcraft:
	snapcraft

# ===================================================================
# Docker
# Need Docker Buildx package (apt install docker-buildx on Ubuntu)
# ===================================================================

define DOCKERFILE
docker-files/$(word 1,$(subst -, ,$*)).Dockerfile
endef

define TARGET
$(word 2,$(subst -, ,$*))
endef

$(DOCKER_IMAGES): docker-%:
	$(DOCKER_BUILD) --target $(TARGET) -f $(DOCKERFILE) -t $(DOCKER_TAG) .

docker: docker-alpine docker-ubuntu ## Generate local docker images

docker-alpine: $(ALPINE_IMAGES) ## Generate local docker images (Alpine)
docker-ubuntu: $(UBUNTU_IMAGES) ## Generate local docker images (Ubuntu)

docker-alpine-full: ## Generate local docker image (Alpine full)
docker-alpine-minimal: ## Generate local docker image (Alpine minimal)
docker-alpine-dev: ## Generate local docker image (Alpine dev)
docker-ubuntu-full: ## Generate local docker image (Ubuntu full)
docker-ubuntu-minimal: ## Generate local docker image (Ubuntu minimal)
docker-ubuntu-dev: ## Generate local docker image (Ubuntu dev)

# ===================================================================
# Run
# ===================================================================

run: ## Start Glances in console mode (also called standalone)
	$(PYTHON) -m glances -C $(CONF)

run-debug: ## Start Glances in debug console mode (also called standalone)
	$(PYTHON) -m glances -C $(CONF) -d

run-local-conf: ## Start Glances in console mode with the system conf file
	$(PYTHON) -m glances

run-local-conf-hide-public: ## Start Glances in console mode with the system conf file and hide public information
	$(PYTHON) -m glances --hide-public-info

run-min: ## Start minimal Glances in console mode (also called standalone)
	$(VENV_MIN)/python -m glances -C $(CONF)

run-min-debug: ## Start minimal Glances in debug console mode (also called standalone)
	$(VENV_MIN)/python -m glances -C $(CONF) -d

run-min-local-conf: ## Start minimal Glances in console mode with the system conf file
	$(VENV_MIN)/python -m glances

$(DOCKER_RUNTIMES): run-docker-%:
	$(DOCKER_RUN) $(DOCKER_OPTS) $(DOCKER_SOCKS) -it $(DOCKER_TAG)

run-docker-alpine-minimal: ## Start Glances Alpine Docker minimal in console mode
run-docker-alpine-full: ## Start Glances Alpine Docker full in console mode
run-docker-alpine-dev: ## Start Glances Alpine Docker dev in console mode
run-docker-ubuntu-minimal: ## Start Glances Ubuntu Docker minimal in console mode
run-docker-ubuntu-full: ## Start Glances Ubuntu Docker full in console mode
run-docker-ubuntu-dev: ## Start Glances Ubuntu Docker dev in console mode

run-webserver: ## Start Glances in Web server mode
	$(PYTHON) -m glances -C $(CONF) -w

run-webserver-local-conf: ## Start Glances in Web server mode with the system conf file
	$(PYTHON) -m glances -w

run-webserver-local-conf-hide-public: ## Start Glances in Web server mode with the system conf file and hide public info
	$(PYTHON) -m glances -w --hide-public-info

run-restapiserver: ## Start Glances in REST API server mode
	$(PYTHON) -m glances -C $(CONF) -w --disable-webui

run-server: ## Start Glances in server mode (RPC)
	$(PYTHON) -m glances -C $(CONF) -s

run-client: ## Start Glances in client mode (RPC)
	$(PYTHON) -m glances -C $(CONF) -c localhost

run-browser: ## Start Glances in browser mode (RPC)
	$(PYTHON) -m glances -C $(CONF) --browser

run-issue: ## Start Glances in issue mode
	$(PYTHON) -m glances -C $(CONF) --issue

run-multipass: ## Install and start Glances in a VM (only available on Ubuntu with multipass already installed)
	multipass launch -n glances-on-lts lts
	multipass exec glances-on-lts -- sudo snap install glances
	multipass exec glances-on-lts -- glances
	multipass stop glances-on-lts
	multipass delete glances-on-lts

show-version: ## Show Glances version number
	$(PYTHON) -m glances -C $(CONF) -V
