Pre-requisites:
- Docker needs to be installed on your system
- https://www.home-assistant.io/installation/linux/#install-home-assistant-container

Start Docker:

    cd ./tests-data/issues/issue3333-homeassistant/
    sh ./run-homeassistant.sh

Access to the interface:

    firefox http://localhost:8123/

And install the Glances plugin.

    Parameters / Services / + Add / Glances

Stats will be refreshed every 5 minutes.
