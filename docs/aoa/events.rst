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
