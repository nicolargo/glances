PORT     ?= 8008
venv_full:= venv/bin
venv_min := venv-min/bin
CONF     := conf/glances.conf
PIP      := $(venv_full)/pip
PYTHON   := $(venv_full)/python
PYTEST   := $(venv_full)/python -m pytest
LASTTAG  = $(shell git describe --tags --abbrev=0)

VENV_TYPES    := full min
VENV_PYTHON   := $(VENV_TYPES:%=venv-%-python)
VENV_UPG      := $(VENV_TYPES:%=venv-%-upgrade)
VENV_DEPS     := $(VENV_TYPES:%=venv-%)
VENV_INST_UPG := $(VENV_DEPS) $(VENV_UPG)

IMAGES_TYPES      := full minimal
DISTROS           := alpine ubuntu
alpine_images     := $(IMAGES_TYPES:%=docker-alpine-%)
ubuntu_images     := $(IMAGES_TYPES:%=docker-ubuntu-%)
DOCKER_IMAGES     := $(alpine_images) $(ubuntu_images)
DOCKER_RUNTIMES   := $(DOCKER_IMAGES:%=run-%)
UNIT_TESTS        := test-core test-restful test-xmlrpc
DOCKER_BUILD      := docker buildx build
DOCKER_RUN        := docker run
PODMAN_SOCK       ?= /run/user/$(shell id -u)/podman/podman.sock
DOCKER_SOCK       ?= /var/run/docker.sock
DOCKER_SOCKS      := -v $(PODMAN_SOCK):$(PODMAN_SOCK):ro -v $(DOCKER_SOCK):$(DOCKER_SOCK):ro
DOCKER_OPTS       := --rm -e TZ="${TZ}" -e GLANCES_OPT="" --pid host --network host

# if the command is only `make`, the default tasks will be the printing of the help.
.DEFAULT_GOAL := help

.PHONY: help test docs docs-server venv venv-min

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

venv-%-upgrade: UPGRADE = --upgrade

define DEFINE_VARS_FOR_TYPE
venv-$(TYPE) venv-$(TYPE)-upgrade: VIRTUAL_ENV = $(venv_$(TYPE))
endef

$(foreach TYPE,$(VENV_TYPES),$(eval $(DEFINE_VARS_FOR_TYPE)))

$(VENV_PYTHON): venv-%-python:
	virtualenv -p python3 $(if $(filter full,$*),venv,venv-$*)

$(VENV_INST_UPG): venv-%:
	$(if $(UPGRADE),$(VIRTUAL_ENV)/pip install --upgrade pip,)
	$(foreach REQ,$(REQS), $(VIRTUAL_ENV)/pip install $(UPGRADE) -r $(REQ);)
	$(if $(PRE_COMMIT),$(VIRTUAL_ENV)/pre-commit install --hook-type pre-commit,)

venv-python: $(VENV_PYTHON) ## Install all Python 3 venv
venv: $(VENV_DEPS) ## Install all Python 3 dependencies
venv-upgrade: $(VENV_UPG) ## Upgrade all Python 3 dependencies

# For full installation (with optional dependencies)

venv-full venv-full-upgrade: REQS = requirements.txt optional-requirements.txt dev-requirements.txt doc-requirements.txt

venv-full-python: ## Install Python 3 venv
venv-full: venv-python ## Install Python 3 run-time
venv-full-upgrade: ## Upgrade Python 3 run-time dependencies
venv-full: PRE_COMMIT = 1

# For minimal installation (without optional dependencies)

venv-min venv-min-upgrade: REQS = requirements.txt dev-requirements.txt doc-requirements.txt

venv-min-python: ## Install Python 3 venv minimal
venv-min: venv-min-python ## Install Python 3 minimal run-time dependencies
venv-min-upgrade: ## Upgrade Python 3 minimal run-time dependencies

# ===================================================================
# Tests
# ===================================================================

test: ## Run All unit tests
	$(PYTEST)

test-core: ## Run Core unit tests
	$(PYTEST) tests/test_core.py

test-memoryleak: ## Run Memory-leak unit tests
	$(PYTEST) tests/test_memoryleak.py

test-perf: ## Run Perf unit tests
	$(PYTEST) tests/test_perf.py

test-restful: ## Run Restful API unit tests
	$(PYTEST) tests/test_restful.py

test-webui: ## Run WebUI unit tests
	$(PYTEST) tests/test_webui.py

test-xmlrpc: ## Run XMLRPC API unit tests
	$(PYTEST) tests/test_xmlrpc.py

test-with-upgrade: venv-upgrade test ## Upgrade deps and run unit tests

test-min: ## Run core unit tests in minimal environment
	$(venv_min)/python -m pytest tests/test_core.py

test-min-with-upgrade: venv-min-upgrade ## Upgrade deps and run unit tests in minimal environment
	$(venv_min)/python -m pytest tests/test_core.py

# ===================================================================
# Linters, profilers and cyber security
# ===================================================================

format: ## Format the code
	$(venv_full)/python -m ruff format .

lint: ## Lint the code.
	$(venv_full)/python -m ruff check . --fix

codespell: ## Run codespell to fix common misspellings in text files
	$(venv_full)/codespell -S .git,./docs/_build,./Glances.egg-info,./venv*,./glances/outputs,*.svg -L hart,bu,te,statics -w

semgrep: ## Run semgrep to find bugs and enforce code standards
	$(venv_full)/semgrep scan --config=auto

profiling-%: SLEEP = 3
profiling-%: TIMES = 30
profiling-%: OUT_DIR = docs/_static

define DISPLAY-BANNER
@echo "Start Glances for $(TIMES) iterations (more or less 1 mins, please do not exit !)"
sleep $(SLEEP)
endef

profiling-gprof: CPROF = glances.cprof
profiling-gprof: ## Callgraph profiling (need "apt install graphviz")
	$(DISPLAY-BANNER)
	$(PYTHON) -m cProfile -o $(CPROF) run-venv.py -C $(CONF) --stop-after $(TIMES)
	$(venv_full)/gprof2dot -f pstats $(CPROF) | dot -Tsvg -o $(OUT_DIR)/glances-cgraph.svg
	rm -f $(CPROF)

profiling-pyinstrument: ## PyInstrument profiling
	$(DISPLAY-BANNER)
	$(PIP) install pyinstrument
	$(PYTHON) -m pyinstrument -r html -o $(OUT_DIR)/glances-pyinstrument.html -m glances -C $(CONF) --stop-after $(TIMES)

profiling-pyspy: ## Flame profiling
	$(DISPLAY-BANNER)
	$(venv_full)/py-spy record -o $(OUT_DIR)/glances-flame.svg -d 60 -s -- $(PYTHON) run-venv.py -C $(CONF) --stop-after $(TIMES)

profiling: profiling-gprof profiling-pyinstrument profiling-pyspy ## Profiling of the Glances software

trace-malloc: ## Trace the malloc() calls
	@echo "Malloc test is running, please wait ~30 secondes..."
	$(PYTHON) -m glances -C $(CONF) --trace-malloc --stop-after 15 --quiet

memory-leak: ## Profile memory leaks
	$(PYTHON) -m glances -C $(CONF) --memory-leak

memory-profiling: TIMES = 2400
memory-profiling: PROFILE = mprofile_*.dat
memory-profiling: OUT_DIR = docs/_static
memory-profiling: ## Profile memory usage
	@echo "It's a very long test (~4 hours)..."
	rm -f $(PROFILE)
	@echo "1/2 - Start memory profiling with the history option enable"
	$(venv_full)/mprof run -T 1 -C run-venv.py -C $(CONF) --stop-after $(TIMES) --quiet
	$(venv_full)/mprof plot --output $(OUT_DIR)/glances-memory-profiling-with-history.png
	rm -f $(PROFILE)
	@echo "2/2 - Start memory profiling with the history option disable"
	$(venv_full)/mprof run -T 1 -C run-venv.py -C $(CONF) --disable-history --stop-after $(TIMES) --quiet
	$(venv_full)/mprof plot --output $(OUT_DIR)/glances-memory-profiling-without-history.png
	rm -f $(PROFILE)

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

webui webui%: DIR = glances/outputs/static/

webui: ## Build the Web UI
	$(PYTHON) -c 'import json; from glances.outputs.glances_curses import _GlancesCurses; print(json.dumps({ "leftMenu": [p for p in _GlancesCurses._left_sidebar if p != "now"]}, indent=4))' > ./glances/outputs/static/js/uiconfig.json
	cd $(DIR) && npm ci && npm run build

webui-audit: ## Audit the Web UI
	cd $(DIR) && npm audit

webui-audit-fix: ## Fix audit the Web UI
	cd $(DIR) && npm audit fix && npm ci && npm run build

# ===================================================================
# Packaging
# ===================================================================

flatpak: venv-upgrade ## Generate FlatPack JSON file
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

define MAKE_DOCKER_BUILD_RULES
$($(DISTRO)_images): docker-$(DISTRO)-%: docker-files/$(DISTRO).Dockerfile
	$(DOCKER_BUILD) --target $$* -f $$< -t glances:local-$(DISTRO)-$$* .
endef

$(foreach DISTRO,$(DISTROS),$(eval $(MAKE_DOCKER_BUILD_RULES)))

docker: docker-alpine docker-ubuntu ## Generate local docker images

docker-alpine: $(alpine_images) ## Generate local docker images (Alpine)
docker-ubuntu: $(ubuntu_images) ## Generate local docker images (Ubuntu)

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
	$(venv_min)/python -m glances -C $(CONF)

run-min-debug: ## Start minimal Glances in debug console mode (also called standalone)
	$(venv_min)/python -m glances -C $(CONF) -d

run-min-local-conf: ## Start minimal Glances in console mode with the system conf file
	$(venv_min)/python -m glances

run-like-htop: ## Start Glances with the same features than Htop
	$(venv_min)/python -m glances --disable-plugin network,ports,wifi,connections,diskio,fs,irq,folders,raid,smart,sensors,vms,containers,ip,amps --disable-left-sidebar

$(DOCKER_RUNTIMES): run-docker-%:
	$(DOCKER_RUN) $(DOCKER_OPTS) $(DOCKER_SOCKS) -it glances:local-$*

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

run-web-browser: ## Start Web Central Browser
	$(PYTHON) -m glances -C $(CONF) -w --browser

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
