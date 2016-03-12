Building the docs
=================

First install Sphinx:

    pip install sphinx

or update it if already installed:

    pip install --upgrade shpinx

Go to the docs folder:

    cd docs

Edit the Makefile (line 5):

    SPHINXOPTS    = -D version=2.6 -D release=2.6_RC1

Then build the HTML documentation:

    make html

and the man page:

    make man
