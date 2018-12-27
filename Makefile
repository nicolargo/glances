PORT?=8008

install:
	sensible-browser "https://github.com/nicolargo/glances#installation"

test:
	./unitest-all.sh

docs:
	cd docs && ./build.sh

docs-server: docs
	(sleep 2 && sensible-browser "http://localhost:$(PORT)") &
	cd docs/_build/html/ && python -m SimpleHTTPServer $(PORT)

.PHONY: test docs docs-server
