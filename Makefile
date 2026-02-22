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
UV_RUN		   	  := .venv-uv/bin/uv

# if the command is only `make`, the default tasks will be the printing of the help.
.DEFAULT_GOAL := help

.PHONY: help test docs docs-server venv requirements profiling docker all clean all test

help: ## List all make commands available
	@grep -E '^[\.a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk -F ":" '{print $1}' | \
	grep -v % | sed 's/\\//g' | sort | \
	awk 'BEGIN {FS = ":[^:]*?##"}; {printf "\033[1;34mmake %-50s\033[0m %s\n", $$1, $$2}'

# ===================================================================
# Virtualenv
# ===================================================================

# install-uv: ## Instructions to install the UV tool
# 	@echo "Install the UV tool (https://astral.sh/uv/)"
# 	@echo "Please install the UV tool manually"
# 	@echo "For example with: curl -LsSf https://astral.sh/uv/install.sh | sh"
# 	@echo "Or via a package manager of your distribution"
# 	@echo "For example for Snap: snap install astral-uv"

install-uv: ## Install UV tool in a specific virtualenv
	python3 -m venv .venv-uv
	.venv-uv/bin/pip install uv

upgrade-uv: ## Upgrade the UV tool
	.venv-uv/bin/pip install --upgrade pip
	.venv-uv/bin/pip install --upgrade uv

venv: ## Create the virtualenv with all dependencies
	$(UV_RUN) sync --all-extras --no-group dev

venv-upgrade venv-switch-to-full: ## Upgrade the virtualenv with all dependencies
	$(UV_RUN) sync --upgrade --all-extras

venv-min: ## Create the virtualenv with minimal dependencies
	$(UV_RUN) sync

venv-upgrade-min venv-switch-to-min: ## Upgrade the virtualenv with minimal dependencies
	$(UV_RUN) sync --upgrade

venv-clean: ## Remove the virtualenv
	rm -rf .venv

venv-dev: ## Create the virtualenv with dev dependencies
	$(UV_RUN) sync --dev --all-extras
	$(UV_RUN) run pre-commit install --hook-type pre-commit

# ===================================================================
# Requirements
#
# Note: the --no-hashes option should be used because pip (in CI) has
# issues with hashes.
# ===================================================================

requirements-min: ## Generate the requirements.txt files (minimal dependencies)
	$(UV_RUN) export --no-emit-workspace --no-hashes --no-group dev --output-file requirements.txt

requirements-all: ## Generate the all-requirements.txt files (all dependencies)
	$(UV_RUN) export --no-emit-workspace --no-hashes --all-extras --no-group dev --output-file all-requirements.txt

requirements-docker: ## Generate the docker-requirements.txt files (Docker specific dependencies)
	$(UV_RUN) export --no-emit-workspace --no-hashes --no-group dev --extra containers --extra web --extra mcp --output-file docker-requirements.txt

requirements-dev: ## Generate the dev-requirements.txt files (dev dependencies)
	$(UV_RUN) export --no-hashes --only-dev --output-file dev-requirements.txt

requirements: requirements-min requirements-all requirements-dev requirements-docker  ## Generate all the requirements files

requirements-upgrade: venv-upgrade requirements  ## Upgrade the virtualenv and regenerate all the requirements files

# ===================================================================
# Tests
# ===================================================================

test: ## Run All unit tests
	$(UV_RUN) run pytest

test-core: ## Run Core unit tests
	$(UV_RUN) run pytest tests/test_core.py

test-plugins: ## Run Plugins unit tests
	$(UV_RUN) run pytest tests/test_plugin_*.py

test-api: ## Run API unit tests
	$(UV_RUN) run pytest tests/test_api.py

test-memoryleak: ## Run Memory-leak unit tests
	$(UV_RUN) run pytest tests/test_memoryleak.py

test-perf: ## Run Perf unit tests
	$(UV_RUN) run pytest tests/test_perf.py

test-restful: ## Run Restful API unit tests
	$(UV_RUN) run pytest tests/test_restful.py

test-webui: ## Run WebUI unit tests
	$(UV_RUN) run pytest tests/test_webui.py

test-xmlrpc: ## Run XMLRPC API unit tests
	$(UV_RUN) run pytest tests/test_xmlrpc.py

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

test-export-nats: ## Run interface tests with NATS
	/bin/bash ./tests/test_export_nats.sh

test-exports: ## Tests all exports
	@for f in ./tests/test_export_*.sh; do /bin/bash "$$f"; done

# ===================================================================
# Linters, profilers and cyber security
# ===================================================================

pre-commit: ## Run pre-commit hooks
	$(UV_RUN) run pre-commit run --all-files

find-duplicate-lines: ## Search for duplicate lines in files
	/bin/bash tests-data/tools/find-duplicate-lines.sh

format: ## Format the code
	$(UV_RUN) run ruff format .

lint: ## Lint the code.
	$(UV_RUN) run ruff check . --fix

lint-readme: ## Lint the main README.rst file
	$(UV_RUN) run rstcheck README.rst
	$(UV_RUN) run rstcheck README-pypi.rst

codespell: ## Run codespell to fix common misspellings in text files
	$(UV_RUN) run codespell -S .git,./docs/_build,./Glances.egg-info,./venv*,./glances/outputs,*.svg -L hart,bu,te,statics -w

semgrep: ## Run semgrep to find bugs and enforce code standards
	$(UV_RUN) run semgrep scan --config=auto

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
	$(UV_RUN) run python -m cProfile -o $(CPROF) run-venv.py -C $(CONF) --stop-after $(TIMES)
	$(UV_RUN) run gprof2dot -f pstats $(CPROF) | dot -Tsvg -o $(OUT_DIR)/glances-cgraph.svg
	rm -f $(CPROF)

profiling-pyinstrument: ## PyInstrument profiling
	$(DISPLAY-BANNER)
	$(UV_RUN) add pyinstrument
	$(UV_RUN) run pyinstrument -r html -o $(OUT_DIR)/glances-pyinstrument.html -m glances -C $(CONF) --stop-after $(TIMES)

profiling-pyspy: ## Flame profiling
	$(DISPLAY-BANNER)
	$(UV_RUN) run py-spy record -o $(OUT_DIR)/glances-flame.svg -d 60 -s -- .venv-uv/bin/uvrun python run-venv.py -C $(CONF) --stop-after $(TIMES)

profiling: profiling-gprof profiling-pyinstrument profiling-pyspy ## Profiling of the Glances software

trace-malloc: ## Trace the malloc() calls
	@echo "Malloc test is running, please wait ~30 secondes..."
	$(UV_RUN) run python -m glances -C $(CONF) --trace-malloc --stop-after 15 --quiet

memory-leak: ## Profile memory leaks
	$(UV_RUN) run python -m glances -C $(CONF) --memory-leak

memory-profiling: TIMES = 2400
memory-profiling: PROFILE = mprofile_*.dat
memory-profiling: OUT_DIR = docs/_static
memory-profiling: ## Profile memory usage
	@echo "It's a very long test (~4 hours)..."
	rm -f $(PROFILE)
	@echo "1/2 - Start memory profiling with the history option enable"
	$(UV_RUN) run mprof run -T 1 -C run-venv.py -C $(CONF) --stop-after $(TIMES) --quiet
	$(UV_RUN) run mprof plot --output $(OUT_DIR)/glances-memory-profiling-with-history.png
	rm -f $(PROFILE)
	@echo "2/2 - Start memory profiling with the history option disable"
	$(UV_RUN) run mprof run -T 1 -C run-venv.py -C $(CONF) --disable-history --stop-after $(TIMES) --quiet
	$(UV_RUN) run mprof plot --output $(OUT_DIR)/glances-memory-profiling-without-history.png
	rm -f $(PROFILE)

# Trivy installation: https://aquasecurity.github.io/trivy/latest/getting-started/installation/
trivy: ## Run Trivy to find vulnerabilities
	$(UV_RUN) run trivy fs ./glances/

bandit: ## Run Bandit to find vulnerabilities
	$(UV_RUN) run bandit glances -r

# ===================================================================
# Docs
# ===================================================================

docs: ## Create the documentation
	$(UV_RUN) run python -m glances -C $(CONF) --api-doc > ./docs/api/python.rst
	$(UV_RUN) run python ./generate_openapi.py
	$(UV_RUN) run python -m glances -C $(CONF) --api-restful-doc > ./docs/api/restful.rst
	cd docs && ./build.sh && cd ..

docs-server: docs ## Start a Web server to serve the documentation
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && .venv-uv/bin/uvrun python -m http.server $(PORT)

docs-jupyter:  ## Start Jupyter Notebook
	$(UV_RUN) run --with jupyter jupyter lab

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
	$(UV_RUN) run python ./generate_webui_conf.py > ./glances/outputs/static/js/uiconfig.json

webui: webui-gen-config ## Build the Web UI
	cd $(DIR) && npm ci && npm run build

webui-audit: ## Audit the Web UI
	cd $(DIR) && npm audit

webui-audit-fix: webui-gen-config ## Fix audit the Web UI
	cd $(DIR) && npm ci && npm audit fix && npm run build

webui-update: webui-gen-config ## Update JS dependencies
	cd $(DIR) && npm update --save && npm ci && npm run build

# ===================================================================
# Packaging
# ===================================================================

flatpak: venv-upgrade ## Generate FlatPack JSON file
	git clone https://github.com/flatpak/flatpak-builder-tools.git
	$(UV_RUN) run python ./flatpak-builder-tools/pip/flatpak-pip-generator glances
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

trivy-docker: ## Run Trivy to find vulnerabilities in Docker images
	$(UV_RUN) run trivy image glances:local-alpine-full
	$(UV_RUN) run trivy image glances:local-alpine-minimal
	$(UV_RUN) run trivy image glances:local-ubuntu-full
	$(UV_RUN) run trivy image glances:local-ubuntu-minimal

# ===================================================================
# Run
# ===================================================================

run: ## Start Glances in console mode (also called standalone)
	$(UV_RUN) run python -m glances -C $(CONF)

run-debug: ## Start Glances in debug console mode (also called standalone)
	$(UV_RUN) run python -m glances -C $(CONF) -d

run-local-conf: ## Start Glances in console mode with the system conf file
	$(UV_RUN) run python -m glances

run-local-conf-hide-public: ## Start Glances in console mode with the system conf file and hide public information
	$(UV_RUN) run python -m glances --hide-public-info

run-like-htop: ## Start Glances with the same features than Htop
	$(UV_RUN) run python -m glances --disable-plugin network,ports,wifi,connections,diskio,fs,irq,folders,raid,smart,sensors,vms,containers,ip,amps --disable-left-sidebar

run-fetch: ## Start Glances in fetch mode
	$(UV_RUN) run python -m glances --fetch

$(DOCKER_RUNTIMES): run-docker-%:
	$(DOCKER_RUN) $(DOCKER_OPTS) $(DOCKER_SOCKS) -it glances:local-$*

run-docker-alpine-minimal: ## Start Glances Alpine Docker minimal in console mode
run-docker-alpine-full: ## Start Glances Alpine Docker full in console mode
run-docker-alpine-dev: ## Start Glances Alpine Docker dev in console mode
run-docker-ubuntu-minimal: ## Start Glances Ubuntu Docker minimal in console mode
run-docker-ubuntu-full: ## Start Glances Ubuntu Docker full in console mode
run-docker-ubuntu-dev: ## Start Glances Ubuntu Docker dev in console mode

generate-ssl: ## Generate local and sel signed SSL certificates for dev (need mkcert)
	mkcert glances.local localhost 120.0.0.1 0.0.0.0

run-webserver: ## Start Glances in Web server mode
	$(UV_RUN) run python -m glances -C $(CONF) -w

run-webserver-mcp: ## Start Glances in Web server mode with MCP
	$(UV_RUN) run python -m glances -C $(CONF) -w --enable-mcp

run-webserver-local-conf: ## Start Glances in Web server mode with the system conf file
	$(UV_RUN) run python -m glances -w

run-webserver-mcp-local-conf: ## Start Glances in Web server mode with MCP and the system conf file
	$(UV_RUN) run python -m glances -w --enable-mcp

run-webserver-local-conf-hide-public: ## Start Glances in Web server mode with the system conf file and hide public info
	$(UV_RUN) run python -m glances -w --hide-public-info

run-webui: un-webserver  ## Start Glances in Web server mode

run-restapiserver: ## Start Glances in REST API server mode
	$(UV_RUN) run python -m glances -C $(CONF) -w --disable-webui

run-server: ## Start Glances in server mode (RPC)
	$(UV_RUN) run python -m glances -C $(CONF) -s

run-client: ## Start Glances in client mode (RPC)
	$(UV_RUN) run python -m glances -C $(CONF) -c localhost

run-browser: ## Start Glances in browser mode (RPC)
	$(UV_RUN) run python -m glances -C $(CONF) --browser

run-web-browser: ## Start Web Central Browser
	$(UV_RUN) run python -m glances -C $(CONF) -w --browser

run-issue: ## Start Glances in issue mode
	$(UV_RUN) run python -m glances -C $(CONF) --issue

run-multipass: ## Install and start Glances in a VM (only available on Ubuntu with multipass already installed)
	multipass launch -n glances-on-lts lts
	multipass exec glances-on-lts -- sudo snap install glances
	multipass exec glances-on-lts -- glances
	multipass stop glances-on-lts
	multipass delete glances-on-lts

show-version: ## Show Glances version number
	$(UV_RUN) run python -m glances -C $(CONF) -V
