.. _amps:

Applications Monitoring Process
===============================

Thanks to Glances and it AMP module, you can add specific monitoring
to running process. AMP are defined in the Glances configuration file.

You can disable AMP using the --disable-amps option or pressing the `A` shortkey.

Simple AMP
----------

For example, a simple AMP which monitor the CPU/MEM of all Python processes
can be define using:

.. code-block:: ini

    [amp_python]
    enable=true
    regex=.*python.*
    refresh=3

Every 3 seconds (*refresh*) and if the *enable* key is true, Glances will
filter the running processes list thanks to the .*python.* regular
expression (*regex*). The default behavor for an AMP is to display:
the number of matching processes, the CPU and MEM:

.. image:: ../_static/amp-python.png

You can also define the minimum (*countmin*) and/or maximum (*countmax*) process
number. For example:

.. code-block:: ini

    [amp_python]
    enable=true
    regex=.*python.*
    refresh=3
    countmin=1
    countmax=2

With this configuration, if the number of running Python script is higher than 2
then the AMP is display with a purple color (red if < countmin):

.. image:: ../_static/amp-python-warning.png

User define AMP
---------------

If you need to execute a specific command line, you can use the *command* option.
For example, if you want to display the Dropbox process status, you can define the
following section in the Glances configuration file:

.. code-block:: ini

    [amp_dropbox]
    # Use the default AMP (no dedicated AMP Python script)
    enable=true
    regex=.*dropbox.*
    refresh=3
    one_line=false
    command=dropbox status
    countmin=1

The *dropbox status* command line will be executed and displayed in the Glances UI:

.. image:: ../_static/amp-dropbox.png

You can force Glances to display the result in one line setting the *one_line* to true.

Embeded AMP
-----------

Glances provides some specifics AMP scripts (replacing the *command* line) hosted
in the glances/amps folder. You can write your own AMP script to fill yours needs.
AMP scripts are located in the glances/amps folder and should be names glances_*.py.
An AMP script define an Amp class (GlancesAmp) with a mandatory update method.
The update method call the set_result method to set the AMP return string.
The return string is a string with one or more line (\n between lines).

You can write your owns AMP and enable its from the configuration file.
The configuration file section should be named [amp_*].

For example, if you want to enable the Nginx AMP, the following definition
should do the job (NGinx AMP is provided by the Glances team as an example):

.. code-block:: ini

    [amp_nginx]
    enable=true
    regex=\/usr\/sbin\/nginx
    refresh=60
    one_line=false
    status_url=http://localhost/nginx_status

Here is the result:

.. image:: ../_static/amps.png

In client/server mode, the AMP list is defined on the server side.
