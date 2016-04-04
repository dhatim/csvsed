======
csvmod
======

A stream-oriented CSV modification tool. Like a stripped-down "sed"
command, but for tabular data.


TL;DR
=====

Install:

.. code-block:: bash

  $ pip install csvsed

Use:

.. code-block:: bash

  # given a sample CSV
  $ cat sample.csv

  Employee ID,Age,Wage,Status
  8783,47,"104,343,873.83","All good, but nowhere to go."
  2003,32,"98,878,784.00",A-OK

  # modify that data with a series of `csvsed` pipes
  $ cat sample.csv \
    | csvsed -c Wage -m s/,//g \                              # remove commas from the Wage column
    | csvsed -c Status -m 'y/A-Z/a-z/' \                      # convert Status to all lowercase
    | csvsed -c Status -m 's/.*(ok|good).*/\1/' \             # restrict to keywords 'ok' & 'good'
    | csvsed -c Age -m 'e/^[0-9]+$/xargs -I {} echo "{}*2" | bc/'      # double the Age column

  Employee ID,Age,Wage,Status
  8783,94,104343873.83,good
  2003,64,98878784.00,ok


Installation
============

.. code-block:: bash

  $ pip install csvsed


Usage and Examples
==================

Installation of the `csvsed` python package also installs the
``csvsed`` command-line tool. Use ``csvsed --help`` for all command
line options, but here are some examples to get you going. Given the
input file ``sample.csv``:

.. code-block:: text

  Employee ID,Age,Wage,Status
  8783,47,"104,343,873.83","All good, but nowhere to go."
  2003,32,"98,878,784.00",A-OK

Removing thousands-separators from the "Wage" column using the "s"
(substitute) modifier:

.. code-block:: bash

  $ cat sample.csv | csvsed -c Wage -m s/,//g
  Employee ID,Age,Wage,Status
  8783,47,104343873.83,"All good, but nowhere to go."
  2003,32,98878784.00,A-OK

Convert/extract some text using the "s" (substitute) and "y"
(transliterate) modifiers:

.. code-block:: bash

  $ cat sample.csv | csvsed -c Status -m 's/^All (.*),.*/\1/' \
    | csvsed -c Status -m 's/^A-(.*)/\1/' \
    | csvsed -c Status -m 'y/a-z/A-Z/'
  Employee ID,Age,Wage,Status
  8783,47,"104,343,873.83",GOOD
  2003,32,"98,878,784.00",OK

Square the "Age" column using the "e" (execute) modifier:

.. code-block:: bash

  $ cat sample.csv | csvsed -c Age -m 'e/^[0-9]+$/xargs -I {} echo "{}^2" | bc/'
  Employee ID,Age,Wage,Status
  8783,2209,"104,343,873.83","All good, but nowhere to go."
  2003,1024,"98,878,784.00",A-OK