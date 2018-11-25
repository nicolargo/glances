Glances profiling
=================

First install Sphinx and the RTD theme:

    apt install graphviz
    pip install gprof2dot

Then generate the profiling diagram:

    cd <Glances source>
    python -m cProfile -o /tmp/glances.pstats ./glances/__main__.py
    gprof2dot -f pstats /tmp/glances.pstats | dot -Tpng -o /tmp/glances-cprofile.png

Example:

.. image:: https://raw.githubusercontent.com/nicolargo/glances/develop/docs/dev/glances-cprofile.png
