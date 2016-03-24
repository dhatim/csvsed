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
    super(InvalidModifier, self).__init__('Invalid modifier: %s' % message)

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
      be either a sequence or dictionary of modifiers to apply. If
      it is a sequence, then the modifiers are applied to the
      equivalently positioned cells in the input records. If it is a
      dictionary, the keys can be integers (column position) or
      strings (column name). In all cases, the modifiers can be one of
      the following:

      * function : takes a single string argument and returns a string
      * string : a sed-like modifier

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
    self.column_names    = reader.next() if header else None
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
    modifiers = dict((k, modifier_as_function(v)) for k, v in modifiers.items())
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
    return dict((idx, modifier_as_function(x)) for idx, x in enumerate(modifiers.values()))

#------------------------------------------------------------------------------
def modifier_as_function(modifier):
  """
  Given a modifier (string or callable), return a callable modifier. If the modifier is a string, return the
  appropriate callable modifier by examinating the modifier type (first character).
  """

  # modifier is a callable modifier
  if hasattr(modifier, '__call__'):
    callable_modifier = modifier

  # modifier is a string modifier
  else:
    supported_modifier_types = ['s', 'y', 'e']
    if not modifier:
      raise InvalidModifier('empty modifier')
    modifier_type = modifier[0]
    if modifier_type not in supported_modifier_types:
      raise InvalidModifier('unsupported type `%s` in modifier `%s`; supported modifier types are %s' % (modifier_type, modifier, ', '.join(supported_modifier_types)))
    # perform dispatch
    callable_modifier = eval('%s_modifier' % modifier_type.upper())(modifier)

  return callable_modifier

#------------------------------------------------------------------------------
class Modifier(object):
  """
  Abstract modifier class, from which all modifier classes shall inherit. Perform common checks on the supplied modifier,
  to ease the subsequent operations in subclasses.
  """

  def __init__(self, modifier):
    modifier_length = self.modifier_form.count('/') + 1

    if len(modifier) < modifier_length:
      raise InvalidModifier('modifier is too short: `%s`' % modifier)

    modifier_type = modifier[0]
    modifier_sep = modifier[1]
    modifier_parts = modifier.split(modifier_sep)
    if len(modifier_parts) != modifier_length:
      modifier_form = self.modifier_form.replace('/', modifier_sep)
      raise InvalidModifier('expected modifier of the form `%s`, got `%s`' % (modifier_form, modifier))

    modifier_lhs = modifier_parts[1]
    if not modifier_lhs:
      raise InvalidModifier('%s: no previous regular expression' % modifier)
    self.modifier_lhs = modifier_lhs

    modifier_rhs = modifier_parts[2] if modifier_type != 'e' else ''
    self.modifier_rhs = modifier_rhs

    flags = modifier_parts[3] if modifier_type != 'e' else modifier_parts[2]
    for flag in flags:
      if flag not in self.supported_flags:
        message = 'invalid flag `%s` in `%s`' % (flag, modifier)
        if len(self.supported_flags) == 0:
          message += '; no flag is supported for type `%s`' % modifier_type
        if len(self.supported_flags) == 1:
          message += '; the only supported flag for type `%s` is %s' % (modifier_type, self.supported_flags[0])
        if len(self.supported_flags) > 1:
          message += '; supported flags for type `%s` are %s' % (modifier_type, ', '.join(self.supported_flags))
        raise InvalidModifier(message)
    self.modifier_flags = flags

#------------------------------------------------------------------------------
class S_modifier(Modifier):
  """
  The "substitution" modifier ("s/REGEX/REPL/FLAGS").

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

  Note that the "/" character can be any character as long as it
    is used consistently and not used within the modifier,
    e.g. ``s|a|b|`` is equivalent to ``s/a/b/``.
  """

  def __init__(self, modifier):
    self.modifier_form = 's/EXPR/REPL/FLAGS'
    self.supported_flags = ['i', 'g', 'l', 'm', 's', 'u', 'x']

    super(S_modifier, self).__init__(modifier)

    self.repl = self.modifier_rhs

    re_flags = 0
    for flag in self.modifier_flags:
      re_flags |= getattr(re, flag.upper(), 0)

    try:
      self.regex = re.compile(self.modifier_lhs, re_flags)
    except re.error, e:
      raise InvalidModifier('%s in `%s`' % (e.message, modifier))

    self.count = 0 if 'g' in self.modifier_flags else 1

  def __call__(self, value):
    return self.regex.sub(self.repl, value, count=self.count)

#------------------------------------------------------------------------------
def cranges(pattern):
  """
  Given a pattern, expands it to a range of characters (crange).

  The dash character ("-") indicates a range
  of characters (e.g. "a-z" for all alphabetic characters).  If
  the dash is needed literally, then it must be the first or
  last character, or escaped with "\". The "\" character escapes
  itself. Only the "i" flag, indicating case-insensitive
  matching of `SRC`, is supported.

  Examples:
    [pattern]  -> [crange]
    'a-f'      -> 'abcdef'
    'a\-f'     -> 'a-f'
    'abc-'     -> 'abc-'
    '-abc'     -> '-abc')
    'a-c-e-g'  -> 'abcdefg'
  """
  ret = ''
  idx = 0
  while idx < len(pattern):
    c = pattern[idx]
    idx += 1
    if c == '-' and len(ret) > 0 and len(pattern) > idx:
      for i in range(ord(ret[-1]) + 1, ord(pattern[idx]) + 1):
        ret += chr(i)
      idx += 1
      continue
    if c == '\\' and len(pattern) > idx:
      c = pattern[idx]
      idx += 1
    ret += c
  return ret

#------------------------------------------------------------------------------
class Y_modifier(Modifier):
  """
  The "transliterate" modifier ("y/SRC/DST/FLAGS").

  (This is a slightly modified version of sed's "y" command.)

  Each character in `SRC` is replaced with the corresponding character in `DST`.
  Character ranges are supported in SRC and DST for the "transliterate" modifier.

  Note that the "/" character can be any character as long as it
    is used consistently and not used within the modifier,
    e.g. ``s|a|b|`` is equivalent to ``s/a/b/``.
  """

  def __init__(self, modifier):
    self.modifier_form = 's/SRC/DST/FLAGS'
    self.supported_flags = ['i']
    super(Y_modifier, self).__init__(modifier)

    src = cranges(self.modifier_lhs)
    dst = cranges(self.modifier_rhs)

    if len(src) != len(dst):
      raise InvalidModifier('expecting source and destination to have the same length, but %i != %i, got `%s`' % (src, dst, modifier))

    if 'i' in self.modifier_flags:
      src = src.lower() + src.upper()
      dst = 2 * dst

    self.table = {ord(src_char) : ord(dst_char) for src_char, dst_char in zip(src, dst)}

  def __call__(self, value):
    return value.translate(self.table)

#------------------------------------------------------------------------------
class E_modifier(Modifier):
  """
  The "execute" external program modifier ("e/PROGRAM+OPTIONS/")
  """

  def __init__(self, modifier):
    self.modifier_form = 's/PROGRAM+OPTIONS/'
    self.supported_flags = []
    super(E_modifier, self).__init__(modifier)
    self.command = self.modifier_lhs

  def __call__(self, value):
    proc = subprocess.Popen(
      self.command, shell=True,
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(value)

    if proc.returncode != 0:
      raise Exception('command `%s` failed: %s' % (self.command, err))

    out = out.rstrip('\n')
    return out

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
