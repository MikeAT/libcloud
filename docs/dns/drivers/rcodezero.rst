RcodeZero Driver Documentation
==============================

.. figure:: /_static/images/provider_logos/rcodezero.png
    :align: center
    :width: 300
    :target: https://www.rcodezero.at/en

`RcodeZero`_ is a European Anycast DNS service provided by nic.at. 

Nameservers are arranged in two seperate clouds of more than 35 nodes.
RcodeZero supports primary as well as secondary DNS, DNSSEC signing,
ANAME(ALIAS) records, and provides extensive statistics. Domains and
records are managed via a web interface or a REST based API.

Read more at https://www.rcodezero.at/en or get the API documentation
at https://my.rcodezero.at/api-doc

Instantiating the driver
------------------------

To instantiate the driver you need to pass the API key, hostname, and webserver
HTTP port to the driver constructor as shown below.

.. literalinclude:: /examples/dns/rcodezero/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.rcodezero.RcodeZeroDNSDriver
    :members:
    :inherited-members:

.. _`RcodeZero`: https://my.rcodezero.at/en
