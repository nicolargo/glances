Building the docs
=================

First install Sphinx:

    pip install sphinx

Then build:

    cd docs && make html

To build the man page:

    make man

Then:

    rm man/glances.1
    cp _build/man/glances.1 man/glances.1
