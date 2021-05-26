Building the docs
=================

First install Sphinx and the RTD theme:

    make venv

or update it if already installed:

    make venv-upgrade

Go to the docs folder:

    cd docs

Then build the HTML documentation:

    make html

and the man page:

    LC_ALL=C make man
