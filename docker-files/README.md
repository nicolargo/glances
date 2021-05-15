# Dockerfiles

The Dockerfiles used here are using multi-staged builds.
For building a specific stage locally docker needs to know the target stage with `--target`.

## Examples
For the dev image:
``bash
docker build --target dev -f docker-files/debian.Dockerfile -t glances .
``

For the minimal image:
``bash
docker build --target minimal -f docker-files/debian.Dockerfile -t glances .
``

For the full image:
``bash
docker build --target full -f docker-files/debian.Dockerfile -t glances .
``
