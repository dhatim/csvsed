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
A stream-oriented CSV modification tool. Like a stripped-down "sed"
command, but for tabular data.
'''

import re, string, types, subprocess, csvkit, csv
from csvkit.exceptions import ColumnIdentifierError

#------------------------------------------------------------------------------
class InvalidModifier(Exception):

  def __init__(self, message):
    if isinstance(message, unicode):
        super(InvalidModifier, self).__init__(message.encode('utf-8'))
        self.message = message
    elif isinstance(message, str):
        super(InvalidModifier, self).__init__(message)
        self.message = message.decode('utf-8')
    else:
        raise TypeError

  def __unicode__(self):
    return 'Invalid modifier: %s' % self.message

#------------------------------------------------------------------------------
class CsvFilter(object):
  def __init__(self, reader, modifiers, header=True):
    '''
    On-the-fly modifies CSV records coming from a csvkit reader object.

    :Parameters:

    reader : iter

      The CSV record source - must support the `next()` call, which
      should return a list of values.

    modifiers : { list, dict }

      Specifies a set of modifiers to apply to the `reader`, which can
      be either a sequence or dictionary of a modifiers to apply. If
      it is a sequence, then the modifiers are applied to the
      equivalently positioned cells in the input records. If it is a
      dictionary, the keys can be integers (column position) or
      strings (column name). In all cases, the modifiers can be one of
      the following:

      * function : takes a single string argument and returns a string
      * string : a sed-like modifier.

      Currently supported modification modifiers:

      * Substitution: "s/REGEX/REPL/FLAGS"

        Replaces regular expression `REGEX` with replacement string
        `REPL`, which can use back references. Supports the following
        flags:

        * i: case-insensitive
        * g: global replacement (otherwise only the first is replaced)
        * l: uses locale-dependent character classes
        * m: enables multiline matching for "^" and "$"
        * s: "." also matches the newline character
        * u: enables unicode escape sequences
        * x: `REGEX` uses verbose descriptors & comments

      * Transliteration: "y/SRC/DST/FLAGS"

        (This is a slightly modified version of sed's "y" command.)

        Each character in `SRC` is replaced with the corresponding
        character in `DST`. The dash character ("-") indicates a range
        of characters (e.g. "a-z" for all alphabetic characters).  If
        the dash is needed literally, then it must be the first or
        last character, or escaped with "\". The "\" character escapes
        itself. Only the "i" flag, indicating case-insensitive
        matching of `SRC`, is supported.

      Note that the "/" character can be any character as long as it
      is used consistently and not used within the modifier,
      e.g. ``s|a|b|`` is equivalent to ``s/a/b/``.

    header : bool, optional, default: true

      If truthy (the default), then the first row will not be modified.
    '''
    self.reader    = reader
    self.header    = header
    self.column_names    = None if not header else reader.next()
    self.modifiers = standardize_modifiers(self.column_names, modifiers)

  #----------------------------------------------------------------------------
  def __iter__(self):
    return self

  #----------------------------------------------------------------------------
  def next(self):
    if self.header:
      self.header = False
      return self.column_names
    row = self.reader.next()
    for col, mod in self.modifiers.items():
      row[col] = mod(row[col])
    return row

#------------------------------------------------------------------------------
def standardize_modifiers(column_names, modifiers):
  """
  Given modifiers in any of the permitted input forms, return a dict whose keys
  are column indices and whose values are functions which return a modified value.
  If modifiers is a dictionary and any of its keys are values in column_names, the
  returned dictionary will have those keys replaced with the integer position of
  that value in column_names
  """
  try:
    # Dictionary of modifiers
    modifiers = dict((k, modifier_as_function(v)) for k, v in modifiers.items() if v)
    if not column_names:
      return modifiers
    p2 = {}
    for k in modifiers:
      if k in column_names:
        idx = column_names.index(k)
        if idx in modifiers:
          raise ColumnIdentifierError("Column %s has index %i which already has a pattern." % (k, idx))
        p2[idx] = modifiers[k]
      else:
        p2[k] = modifiers[k]
    return p2
  except AttributeError:
    # Sequence of modifiers
    return dict((i, modifier_as_function(x)) for i, x in enumerate(modifiers))

#------------------------------------------------------------------------------
def modifier_as_function(modifier):
  # modifier is modifier function
  if hasattr(modifier, '__call__'):
    return modifier
  # modifier is a modifier string
  return eval(modifier[0].upper() + '_modifier')(modifier)


#------------------------------------------------------------------------------
class S_modifier(object):
  'The "substitution" modifier ("s/REGEX/REPL/FLAGS").'
  def __init__(self, modifier):
    super(S_modifier, self).__init__()
    if not modifier or len(modifier) < 4 or modifier[0] != 's':
      raise InvalidModifier(modifier)
    s_modifier = modifier.split(modifier[1])
    if len(s_modifier) != 4:
      raise InvalidModifier(modifier)
    flags = 0
    for flag in s_modifier[3].upper():
      flags |= getattr(re, flag, 0)
    self.regex = re.compile(s_modifier[1], flags)
    self.repl  = s_modifier[2]
    self.count = 0 if 'g' in s_modifier[3].lower() else 1
  def __call__(self, value):
    return self.regex.sub(self.repl, value, count=self.count)

#------------------------------------------------------------------------------
def cranges(modifier):
  # todo: there must be a better way...
  ret = ''
  idx = 0
  while idx < len(modifier):
    c = modifier[idx]
    idx += 1
    if c == '-' and len(ret) > 0 and len(modifier) > idx:
      for i in range(ord(ret[-1]) + 1, ord(modifier[idx]) + 1):
        ret += chr(i)
      idx += 1
      continue
    if c == '\\' and len(modifier) > idx:
      c = modifier[idx]
      idx += 1
    ret += c
  return ret

#------------------------------------------------------------------------------
class Y_modifier(object):
  'The "transliterate" modifier ("y/SOURCE/DESTINATION/FLAGS").'

  def __init__(self, modifier):
    super(Y_modifier, self).__init__()
    if not modifier or len(modifier) < 4 or modifier[0] != 'y':
      raise InvalidModifier(modifier)
    y_modifier = modifier.split(modifier[1])
    if len(y_modifier) != 4:
      raise InvalidModifier(modifier)
    src = cranges(y_modifier[1])
    dst = cranges(y_modifier[2])
    flags = y_modifier[3]
    if len(src) != len(dst):
      raise InvalidModifier(modifier)
    if 'i' in flags.lower():
      src = src.lower() + src.upper()
      dst = 2 * dst
    self.src = src
    self.dst = dst

  def __call__(self, value):
    if isinstance(value, unicode):
      table = {ord(src_char) : ord(dst_char) for src_char, dst_char in zip(self.src, self.dst)}
    else:
      assert(isinstance(value, str))
      table = string.maketrans(self.src, self.dst)
    return value.translate(table)

#------------------------------------------------------------------------------
class ReadlineIterator(object):
  'An iterator that calls readline() to get its next value.'
  # NOTE: this is a hack to make csv.reader not read-ahead.
  def __init__(self, f): self.f = f
  def __iter__(self): return self
  def next(self):
    line = self.f.readline()
    if not line: raise StopIteration
    return line

#------------------------------------------------------------------------------
class E_modifier(object):
  'The "execute" external program modifier ("e/PROGRAM+OPTIONS/FLAGS").'
  def __init__(self, modifier):
    super(E_modifier, self).__init__()
    if not modifier or len(modifier) < 3 or modifier[0] != 'e':
      raise InvalidModifier(modifier)
    emodifier = modifier.split(modifier[1])
    if len(emodifier) != 3:
      raise InvalidModifier(modifier)
    emodifier[2] = emodifier[2].lower()
    self.command = emodifier[1]
    self.index   = 1 if 'i' in emodifier[2] else None
    self.csv     = 'c' in emodifier[2]
    if not self.csv:
      return
    self.proc = subprocess.Popen(
      self.command, shell=True, bufsize=0,
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    self.writer = csvkit.CSVKitWriter(self.proc.stdin)
    # note: not using csvkit's reader because there is no easy way of
    # making it not read-ahead (which breaks the "continuous" mode).
    # self.reader = csvkit.CSVKitReader(self.proc.stdout)
    # todo: fix csvkit so that it can be used in non-read-ahead mode.
    self.reader = csv.reader(ReadlineIterator(self.proc.stdout))
  def __call__(self, value):
    if not self.csv:
      return self.execOnce(value)
    self.writer.writerow([value])
    return self.reader.next()[0].decode('utf-8')
  def execOnce(self, value):
    p = subprocess.Popen(
      self.command, shell=True,
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errput = p.communicate(value)
    if p.returncode != 0:
      raise Exception('command "%s" failed: %s' % (self.command, errput))
    if output[-1] == '\n':
      output = output[:-1]
    return output

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
