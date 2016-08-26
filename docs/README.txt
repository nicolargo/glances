Building the docs
=================

First install Sphinx and the RTD theme:

    pip install sphinx sphinx_rtd_theme

or update it if already installed:

    pip install --upgrade sphinx sphinx_rtd_theme

Go to the docs folder:

    cd docs

Then build the HTML documentation:

    make html

and the man page:

    LC_ALL=C make man
