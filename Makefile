PORT     	  ?= 8008
CONF     	  := conf/glances.conf
LASTTAG  	   = $(shell git describe --tags --abbrev=0)

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

# User-friendly check for uv
ifeq ($(shell which uv >/dev/null 2>&1; echo $$?), 1)
$(error The 'uv' command was not found. Make sure you have Astral Uv installed, then set the UV environment variable to point to the full path of the 'uv' executable. Alternatively more information with make install-uv)
endif

# if the command is only `make`, the default tasks will be the printing of the help.
.DEFAULT_GOAL := help

.PHONY: help test docs docs-server venv

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

install-uv:
	@echo "Install the UV tool (https://astral.sh/uv/)"
	@echo "Please install the UV tool manually"
	@echo "For example with: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo "Or via a package manager of your distribution"
	@echo "For example for Snap: snap install astral-uv"

venv:
	uv sync --all-extras --no-group dev

venv-upgrade venv-switch-to-full:
	uv sync --upgrade --all-extras

venv-min:
	uv sync

venv-upgrade-min venv-switch-to-min:
	uv sync --upgrade

venv-clean:
	rm -rf .venv

venv-dev:
	uv sync --dev --all-extras
	uv run pre-commit install --hook-type pre-commit

# ===================================================================
# Requirements
#
# Note: the --no-hashes option should be used because pip (in CI) has
# issues with hashes.
# ===================================================================

requirements-min: ## Generate the requirements.txt files (minimal dependencies)
	uv export --no-emit-workspace --no-hashes --no-group dev --output-file requirements.txt

requirements-all: ## Generate the all-requirements.txt files (all dependencies)
	uv export --no-emit-workspace --no-hashes --all-extras --no-group dev --output-file all-requirements.txt

requirements-docker: ## Generate the docker-requirements.txt files (Docker specific dependencies)
	uv export --no-emit-workspace --no-hashes --no-group dev --extra containers --extra web --output-file docker-requirements.txt

requirements-dev: ## Generate the dev-requirements.txt files (dev dependencies)
	uv export --no-hashes --only-dev --output-file dev-requirements.txt

requirements: requirements-min requirements-all requirements-dev requirements-docker  ## Generate all the requirements files

requirements-upgrade: venv-upgrade requirements  ## Upgrade the virtualenv and regenerate all the requirements files

# ===================================================================
# Tests
# ===================================================================

test: ## Run All unit tests
	uv run pytest

test-core: ## Run Core unit tests
	uv run pytest tests/test_core.py

test-api: ## Run API unit tests
	uv run pytest tests/test_api.py

test-memoryleak: ## Run Memory-leak unit tests
	uv run pytest tests/test_memoryleak.py

test-perf: ## Run Perf unit tests
	uv run pytest tests/test_perf.py

test-restful: ## Run Restful API unit tests
	uv run pytest tests/test_restful.py

test-webui: ## Run WebUI unit tests
	uv run pytest tests/test_webui.py

test-xmlrpc: ## Run XMLRPC API unit tests
	uv run pytest tests/test_xmlrpc.py

test-with-upgrade: venv-upgrade test ## Upgrade deps and run unit tests

test-export-csv: ## Run interface tests with CSV
	/bin/bash ./tests/test_export_csv.sh

test-export-json: ## Run interface tests with JSON
	/bin/bash ./tests/test_export_json.sh

test-export-influxdb-v1: ## Run interface tests with InfluxDB version 1 (Legacy)
	/bin/bash ./tests/test_export_influxdb_v1.sh

test-export-influxdb-v3: ## Run interface tests with InfluxDB version 3 (Core)
	/bin/bash ./tests/test_export_influxdb_v3.sh

test-export-timescaledb: ## Run interface tests with TimescaleDB
	/bin/bash ./tests/test_export_timescaledb.sh

test-exports: test-export-csv test-export-json test-export-influxdb-v1 test-export-influxdb-v3 test-export-timescaledb ## Tests all exports

# ===================================================================
# Linters, profilers and cyber security
# ===================================================================

find-duplicate-lines:
	/bin/bash tests-data/tools/find-duplicate-lines.sh

format: ## Format the code
	uv run ruff format .

lint: ## Lint the code.
	uv run ruff check . --fix

lint-readme: ## Lint the main README.rst file
	uv run rstcheck README.rst

codespell: ## Run codespell to fix common misspellings in text files
	uv run codespell -S .git,./docs/_build,./Glances.egg-info,./venv*,./glances/outputs,*.svg -L hart,bu,te,statics -w

semgrep: ## Run semgrep to find bugs and enforce code standards
	uv run semgrep scan --config=auto

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
	uv run python -m cProfile -o $(CPROF) run-venv.py -C $(CONF) --stop-after $(TIMES)
	uv run gprof2dot -f pstats $(CPROF) | dot -Tsvg -o $(OUT_DIR)/glances-cgraph.svg
	rm -f $(CPROF)

profiling-pyinstrument: ## PyInstrument profiling
	$(DISPLAY-BANNER)
	uv add pyinstrument
	uv run pyinstrument -r html -o $(OUT_DIR)/glances-pyinstrument.html -m glances -C $(CONF) --stop-after $(TIMES)

profiling-pyspy: ## Flame profiling
	$(DISPLAY-BANNER)
	uv run py-spy record -o $(OUT_DIR)/glances-flame.svg -d 60 -s -- uv run python run-venv.py -C $(CONF) --stop-after $(TIMES)

profiling: profiling-gprof profiling-pyinstrument profiling-pyspy ## Profiling of the Glances software

trace-malloc: ## Trace the malloc() calls
	@echo "Malloc test is running, please wait ~30 secondes..."
	uv run python -m glances -C $(CONF) --trace-malloc --stop-after 15 --quiet

memory-leak: ## Profile memory leaks
	uv run python -m glances -C $(CONF) --memory-leak

memory-profiling: TIMES = 2400
memory-profiling: PROFILE = mprofile_*.dat
memory-profiling: OUT_DIR = docs/_static
memory-profiling: ## Profile memory usage
	@echo "It's a very long test (~4 hours)..."
	rm -f $(PROFILE)
	@echo "1/2 - Start memory profiling with the history option enable"
	uv run mprof run -T 1 -C run-venv.py -C $(CONF) --stop-after $(TIMES) --quiet
	uv run mprof plot --output $(OUT_DIR)/glances-memory-profiling-with-history.png
	rm -f $(PROFILE)
	@echo "2/2 - Start memory profiling with the history option disable"
	uv run mprof run -T 1 -C run-venv.py -C $(CONF) --disable-history --stop-after $(TIMES) --quiet
	uv run mprof plot --output $(OUT_DIR)/glances-memory-profiling-without-history.png
	rm -f $(PROFILE)

# Trivy installation: https://aquasecurity.github.io/trivy/latest/getting-started/installation/
trivy: ## Run Trivy to find vulnerabilities in container images
	uv run trivy fs .

# ===================================================================
# Docs
# ===================================================================

docs: ## Create the documentation
	uv run python -m glances -C $(CONF) --api-doc > ./docs/api/python.rst
	uv run python ./generate_openapi.py
	uv run python -m glances -C $(CONF) --api-restful-doc > ./docs/api/restful.rst
	cd docs && ./build.sh && cd ..

docs-server: docs ## Start a Web server to serve the documentation
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && uv run python -m http.server $(PORT)

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

webui-gen-config: ## Generate the Web UI config file
	uv run python ./generate_webui_conf.py > ./glances/outputs/static/js/uiconfig.json

webui: webui-gen-config ## Build the Web UI
	cd $(DIR) && npm ci && npm run build

webui-audit: ## Audit the Web UI
	cd $(DIR) && npm audit

webui-audit-fix: webui-gen-config ## Fix audit the Web UI
	cd $(DIR) && npm audit fix && npm ci && npm run build

webui-update: webui-gen-config ## Update JS dependencies
	cd $(DIR) && npm update --save && npm ci && npm run build

# ===================================================================
# Packaging
# ===================================================================

flatpak: venv-upgrade ## Generate FlatPack JSON file
	git clone https://github.com/flatpak/flatpak-builder-tools.git
	uv run python ./flatpak-builder-tools/pip/flatpak-pip-generator glances
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
	uv run python -m glances -C $(CONF)

run-debug: ## Start Glances in debug console mode (also called standalone)
	uv run python -m glances -C $(CONF) -d

run-local-conf: ## Start Glances in console mode with the system conf file
	uv run python -m glances

run-local-conf-hide-public: ## Start Glances in console mode with the system conf file and hide public information
	uv run python -m glances --hide-public-info

run-like-htop: ## Start Glances with the same features than Htop
	uv run python -m glances --disable-plugin network,ports,wifi,connections,diskio,fs,irq,folders,raid,smart,sensors,vms,containers,ip,amps --disable-left-sidebar

run-fetch: ## Start Glances in fetch mode
	uv run python -m glances --fetch

$(DOCKER_RUNTIMES): run-docker-%:
	$(DOCKER_RUN) $(DOCKER_OPTS) $(DOCKER_SOCKS) -it glances:local-$*

run-docker-alpine-minimal: ## Start Glances Alpine Docker minimal in console mode
run-docker-alpine-full: ## Start Glances Alpine Docker full in console mode
run-docker-alpine-dev: ## Start Glances Alpine Docker dev in console mode
run-docker-ubuntu-minimal: ## Start Glances Ubuntu Docker minimal in console mode
run-docker-ubuntu-full: ## Start Glances Ubuntu Docker full in console mode
run-docker-ubuntu-dev: ## Start Glances Ubuntu Docker dev in console mode

run-webserver: ## Start Glances in Web server mode
	uv run python -m glances -C $(CONF) -w

run-webserver-local-conf: ## Start Glances in Web server mode with the system conf file
	uv run python -m glances -w

run-webserver-local-conf-hide-public: ## Start Glances in Web server mode with the system conf file and hide public info
	uv run python -m glances -w --hide-public-info

run-restapiserver: ## Start Glances in REST API server mode
	uv run python -m glances -C $(CONF) -w --disable-webui

run-server: ## Start Glances in server mode (RPC)
	uv run python -m glances -C $(CONF) -s

run-client: ## Start Glances in client mode (RPC)
	uv run python -m glances -C $(CONF) -c localhost

run-browser: ## Start Glances in browser mode (RPC)
	uv run python -m glances -C $(CONF) --browser

run-web-browser: ## Start Web Central Browser
	uv run python -m glances -C $(CONF) -w --browser

run-issue: ## Start Glances in issue mode
	uv run python -m glances -C $(CONF) --issue

run-multipass: ## Install and start Glances in a VM (only available on Ubuntu with multipass already installed)
	multipass launch -n glances-on-lts lts
	multipass exec glances-on-lts -- sudo snap install glances
	multipass exec glances-on-lts -- glances
	multipass stop glances-on-lts
	multipass delete glances-on-lts

show-version: ## Show Glances version number
	uv run python -m glances -C $(CONF) -V
