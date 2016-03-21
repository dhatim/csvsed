# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2009/08/04
# copy: (C) Copyright 2009-EOT metagriffin -- see LICENSE.txt
#------------------------------------------------------------------------------
# This software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#------------------------------------------------------------------------------

'''
Command-line interface to `csvsed.sed`.
'''

import agate

from csvkit.cli import CSVKitUtility
from csvsed import sed

#------------------------------------------------------------------------------
class CsvSed(CSVKitUtility):

  description = 'A stream-oriented CSV modification tool. Like a ' \
                ' stripped-down "sed" command, but for tabular data.'

  #----------------------------------------------------------------------------
  def add_arguments(self):
    self.argparser.add_argument(
      '-c', '--columns',
      dest='columns',
      help='A comma separated list of column indices or names to be modified.')
    # todo: support in-place file modification
    # todo: make sure that it supports backup spec, eg '-i.orig'
    # self.argparser.add_argument(
    #   '-i', '--in-place',
    #   dest='inplace',
    #   help='Modify a file in-place (with a value, specifies that the original'
    #   ' should be renamed first, e.g. "-i.orig")')
    self.argparser.add_argument('-r', '--expr', dest='expr', nargs='?',
                                help='If specified, he "sed" expression to evaluate: currently supports substitution '
                                ' (s/REGEX/EXPR/FLAGS) and transliteration (y/SRC/DEST/FLAGS)')

  #----------------------------------------------------------------------------
  def main(self):
    reader_kwargs = self.reader_kwargs
    writer_kwargs = self.writer_kwargs
    if writer_kwargs.pop('line_numbers', False):
      reader_kwargs = {'line_numbers': True}

    rows, column_names, column_ids = self.get_rows_and_column_names_and_column_ids(**reader_kwargs)

    mods   = {idx: self.args.expr for idx in column_ids}
    reader = sed.CsvFilter(rows, mods, header=False)

    output = agate.csv.writer(self.output_file, **writer_kwargs)
    output.writerow(column_names)

    for row in reader:
      output.writerow(row)

#------------------------------------------------------------------------------
def launch_instance():
  utility = CsvSed()
  utility.main()

if __name__ == '__main__':
  launch_instance()

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
