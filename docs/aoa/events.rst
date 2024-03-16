.. _events:

events
======

.. image:: ../_static/events.png

Events list is displayed in the bottom of the screen if and only if:

- at least one ``WARNING`` or ``CRITICAL`` alert was occurred
- space is available in the bottom of the console/terminal

Each event message displays the following information:

1. start datetime
2. duration if alert is terminated or `ongoing` if the alert is still in
   progress
3. alert name
4. {min,avg,max} values or number of running processes for monitored
   processes list alerts

The configuration should be done in the ``[alert]`` section of the
Glances configuration file:

.. code-block:: ini

   [alert]
   disable=False
   # Maximum number of events to display (default is 10 events)
   max_events=10
   # Minimum duration for an event to be taken into account (default is 6 seconds)
   min_duration=6
   # Minimum time between two events of the same type (default is 6 seconds)
   # This is used to avoid too many alerts for the same event
   # Events will be merged
   min_interval=6

