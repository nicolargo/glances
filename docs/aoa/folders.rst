.. _folders:

Folders
=======

The folders plugin allows user, through the configuration file, to
monitor size of a predefined folders list.

.. image:: ../_static/folders.png

Each item is defined by:

- ``path``: absolute path to monitor (mandatory)
- ``careful``: optional careful threshold (in MB)
- ``warning``: optional warning threshold (in MB)
- ``critical``: optional critical threshold (in MB)

Up to ``10`` items can be defined.

For example, if you want to monitor the ``/tmp`` folder, the following
definition should do the job:

.. code-block:: ini

    [folders]
    folder_1_path=/tmp
    folder_1_careful=2500
    folder_1_warning=3000
    folder_1_critical=3500

In client/server mode, the list is defined on the ``server`` side.

.. warning::
    Do **NOT** define folders containing lot of files and subfolders.
