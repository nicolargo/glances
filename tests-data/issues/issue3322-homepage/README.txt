Pre-requisites:
- Docker needs to be installed on your system
- https://gethomepage.dev/installation/docker/

Start Docker:

    cd ./tests-data/issues/issue3322-homepage/
    sh ./run-homepage.sh

Access to the interface:

    firefox http://localhost:3000/

Edit the ./config/widgets.yaml file and add (replace 192.168.1.26 by your local IP @):

- glances:
    url: http://192.168.1.26:61208
    # username: user # optional if auth enabled in Glances
    # password: pass # optional if auth enabled in Glances
    version: 4 # required only if running glances v4 or higher, defaults to 3
    cpu: true # optional, enabled by default, disable by setting to false
    mem: true # optional, enabled by default, disable by setting to false
    cputemp: true # disabled by default
    uptime: true # disabled by default
    disk: / # disabled by default, use mount point of disk(s) in glances. Can also be a list (see below)
    diskUnits: bytes # optional, bytes (default) or bbytes. Only applies to disk
    expanded: true # show the expanded view
    label: MyMachine # optional

And the ./config/services.yaml (replace 192.168.1.26 by your local IP @):

- Glances:
    - CPU Usage:
        widget:
            type: glances
            url: http://192.168.1.26:61208
            version: 4 # required only if running glances v4 or higher, defaults to 3
            metric: cpu

    - MEM Usage:
        widget:
            type: glances
            url: http://192.168.1.26:61208
            version: 4 # required only if running glances v4 or higher, defaults to 3
            metric: memory

    - Network Usage:
        widget:
            type: glances
            url: http://192.168.1.26:61208
            version: 4 # required only if running glances v4 or higher, defaults to 3
            metric: network:wlp0s20f3
