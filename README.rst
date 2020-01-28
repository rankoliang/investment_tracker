==================
Investment Tracker
==================


.. image:: https://img.shields.io/travis/com/rankoliang/investment_tracker.svg
        :target: https://travis-ci.com/rankoliang/investment_tracker

.. image:: https://readthedocs.org/projects/investment-tracker/badge/?version=latest
        :target: https://investment-tracker.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Tracks investments by pulling investment data from the web and storing your transaction data locally on your machine.


* Free software: MIT license
* Documentation: https://investment-tracker.readthedocs.io.


Features
--------

* Completed
    - SQLAlchemy models with relationships
    - Storing data offline in a portable file using sqlite
    - Logging stock transactions for different users
    - Manual tracking of stock prices and some stock metadata in a database
* TODO
    - Command line interface with click
    - IEXFinance API integration to retrieve stock data from the web
    - Aggregate overview of investment statistics and plot generation using Matplotlib
    - Proper tests with PyTest and CI with Travis CI
    - Complete documentation

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
