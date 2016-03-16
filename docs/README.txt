Building the docs
=================

First install Sphinx:

    pip install sphinx

or update it if already installed:

    pip install --upgrade sphinx

Go to the docs folder:

    cd docs

Then build the HTML documentation:

    make html

and the man page:

    LC_ALL=C make man
