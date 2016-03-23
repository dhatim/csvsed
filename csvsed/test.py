# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@metagriffin.net>
# date: 2011/04/08
# copy: (C) Copyright 2011-EOT metagriffin -- see LICENSE.txt
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

import agate
import unittest, StringIO, csvkit
from . import sed

#------------------------------------------------------------------------------
def run(source, modifiers, header=True):
  src = StringIO.StringIO(source)
  dst = StringIO.StringIO()
  reader = agate.csv.reader(src)
  reader = sed.CsvFilter(reader, modifiers, header=header)
  writer = agate.csv.writer(dst)
  for row in reader:
    writer.writerow(row)
  return dst.getvalue()

#------------------------------------------------------------------------------
class TestSed(unittest.TestCase):

  baseCsv = '''\
header 1,header 2,header 3,header 4,header 5
field 1.1,field 1.2,field 1.3,field 1.4,field 1.5
field 2.1,field 2.2,field 2.3,field 2.4,field 2.5
field 3.1,field 3.2,field 3.3,field 3.4,field 3.5
'''

  baseCsvUnicode = '''\
latin_lower,latin_upper,latin_full,greek_lower,greek_upper,greek_full
a,A,alpha,α,Α,άλφα
b,B,beta,β,Β,βήτα
g,G,gamma,γ,Γ,γάμμα
'''

  #----------------------------------------------------------------------------
  def test_charRanges(self):
    self.assertEqual(sed.cranges(u'a-f'), u'abcdef')
    self.assertEqual(sed.cranges(u'a\-f'), u'a-f')
    self.assertEqual(sed.cranges(u'abc-'), u'abc-')
    self.assertEqual(sed.cranges(u'-abc'), u'-abc')
    self.assertEqual(sed.cranges(u'a\\\\-_z'), u'a\]^_z')
    self.assertEqual(sed.cranges(u'a-c-e-g'), u'abcdefg')

  #----------------------------------------------------------------------------
  def test_modifier_y_directcall(self):
    self.assertEqual(sed.modifier_as_function(u'y/abc/def/')(u'b,a,c'), u'e,d,f')
    self.assertEqual(sed.modifier_as_function(u'y/abc/def/')(u'b,A,C'), u'e,A,C')
    self.assertEqual(sed.modifier_as_function(u'y/abc/def/i')(u'b,A,C'), u'e,d,f')
    self.assertEqual(sed.modifier_as_function(u'y/a-z/A-Z/')(u'Back-Up'), u'BACK-UP')
    self.assertEqual(sed.modifier_as_function(u'y/a\-z/A~Z/')(u'Back-Up'), u'BAck~Up')

  def test_modifier_y_directcall_unicode(self):
    self.assertEqual(sed.modifier_as_function(u'y/abc/def/')(u'b,a,c'), u'e,d,f')
    self.assertEqual(sed.modifier_as_function(u'y/abc/def/')(u'b,a,c'), u'e,d,f')
    self.assertEqual(sed.modifier_as_function(u'y/αβγ/abg/')(u'β,α,γ'), u'b,a,g')
    self.assertEqual(sed.modifier_as_function(u'y/abg/αβγ/')(u'b,a,g'), u'β,α,γ')
    self.assertEqual(sed.modifier_as_function(u'y/αβγ/γαβ/')(u'β,α,γ'), u'α,γ,β')

  #----------------------------------------------------------------------------
  def test_modifier_y_toupper(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
field 1.1,field 1.2,FIELD 1.3,field 1.4,field 1.5
field 2.1,field 2.2,FIELD 2.3,field 2.4,field 2.5
field 3.1,field 3.2,FIELD 3.3,field 3.4,field 3.5
'''
    self.assertEqual(run(self.baseCsv, {2: u'y/a-z/A-Z/'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_directcall(self):
    self.assertEqual(sed.modifier_as_function(u's/a/b/')(u'abcabc'), u'bbcabc')
    self.assertEqual(sed.modifier_as_function(u's/a/b/g')(u'abcabc'), u'bbcbbc')
    self.assertEqual(sed.modifier_as_function(u's/a/b/g')(u'abcABC'), u'bbcABC')
    self.assertEqual(sed.modifier_as_function(u's/a/b/gi')(u'abcABC'), u'bbcbBC')

  def test_modifier_s_directcall_unicode(self):
    self.assertEqual(sed.modifier_as_function(u's/π/p/')(u'κάππα'), u'κάpπα')
    self.assertEqual(sed.modifier_as_function(u's/π/p/g')(u'κάππα'), u'κάppα')
    self.assertEqual(sed.modifier_as_function(u's/π/Π/')(u'κάππα'), u'κάΠπα')
    self.assertEqual(sed.modifier_as_function(u's/π/Π/g')(u'κάππα'), u'κάΠΠα')

  #----------------------------------------------------------------------------
  def test_modifier_s_noflags(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
xield 1.1,field 1.2,field 1.3,field 1.4,field 1.5
xield 2.1,field 2.2,field 2.3,field 2.4,field 2.5
xield 3.1,field 3.2,field 3.3,field 3.4,field 3.5
'''
    self.assertMultiLineEqual(run(self.baseCsv, {0: u's/./x/'}), chk)

  def test_modifier_s_noflags_unicode(self):
    chk = '''\
latin_lower,latin_upper,latin_full,greek_lower,greek_upper,greek_full
a,A,alpha,α,Α,*λφα
b,B,beta,β,Β,*ήτα
g,G,gamma,γ,Γ,*άμμα
'''
    self.assertMultiLineEqual(run(self.baseCsvUnicode, {5: u's/./*/'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_gflag(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
xxxxxxxxx,field 1.2,field 1.3,field 1.4,field 1.5
xxxxxxxxx,field 2.2,field 2.3,field 2.4,field 2.5
xxxxxxxxx,field 3.2,field 3.3,field 3.4,field 3.5
'''
    self.assertMultiLineEqual(run(self.baseCsv, {0: u's/./x/g'}), chk)

  def test_modifier_s_gflag_unicode(self):
    chk = '''\
latin_lower,latin_upper,latin_full,greek_lower,greek_upper,greek_full
a,A,alpha,α,Α,****
b,B,beta,β,Β,****
g,G,gamma,γ,Γ,*****
'''
    self.assertMultiLineEqual(run(self.baseCsvUnicode, {5: u's/./*/g'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_multicol(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
xxxxxxxxx,field 1.2,yyyyyyyyy,field 1.4,field 1.5
xxxxxxxxx,field 2.2,yyyyyyyyy,field 2.4,field 2.5
xxxxxxxxx,field 3.2,yyyyyyyyy,field 3.4,field 3.5
'''
    self.assertMultiLineEqual(run(self.baseCsv, {0: u's/./x/g', 2: u's/./y/g'}), chk)

  def test_modifier_s_multicol_unicode(self):
    chk = '''\
latin_lower,latin_upper,latin_full,greek_lower,greek_upper,greek_full
a,A,alpha,_,Α,****
b,B,beta,_,Β,****
g,G,gamma,_,Γ,*****
'''
    self.assertMultiLineEqual(run(self.baseCsvUnicode, {3: u's/./_/g', 5: u's/./*/g'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_colbyname(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
xxxxxxxxx,field 1.2,yyyyyyyyy,field 1.4,field 1.5
xxxxxxxxx,field 2.2,yyyyyyyyy,field 2.4,field 2.5
xxxxxxxxx,field 3.2,yyyyyyyyy,field 3.4,field 3.5
'''
    self.assertMultiLineEqual(
      run(self.baseCsv, {'header 1': u's/./x/g', 'header 3': u's/./y/g'}), chk)

  def test_modifier_s_colbyname_unicode(self):
    chk = '''\
latin_lower,latin_upper,latin_full,greek_lower,greek_upper,greek_full
a,A,alpha,_,Α,****
b,B,beta,_,Β,****
g,G,gamma,_,Γ,*****
'''
    self.assertMultiLineEqual(run(self.baseCsvUnicode, {'greek_lower': u's/./_/g', 'greek_full': u's/./*/g'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_nomatch(self):
    chk = self.baseCsv
    self.assertMultiLineEqual(run(self.baseCsv, {0: u's/[IE]/../'}), chk)

  def test_modifier_s_nomatch_unicode(self):
    chk = self.baseCsvUnicode
    self.assertMultiLineEqual(run(self.baseCsvUnicode, {5: u's/[a-zA-Z0-9€]/../'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_iflag(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
f..eld 1.1,field 1.2,field 1.3,field 1.4,field 1.5
f..eld 2.1,field 2.2,field 2.3,field 2.4,field 2.5
f..eld 3.1,field 3.2,field 3.3,field 3.4,field 3.5
'''
    self.assertMultiLineEqual(run(self.baseCsv, {0: u's/[IE]/../i'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_multiflag(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
f....ld 1.1,field 1.2,field 1.3,field 1.4,field 1.5
f....ld 2.1,field 2.2,field 2.3,field 2.4,field 2.5
f....ld 3.1,field 3.2,field 3.3,field 3.4,field 3.5
'''
    self.assertMultiLineEqual(run(self.baseCsv, {0: u's/[IE]/../ig'}), chk)

  #----------------------------------------------------------------------------
  def test_modifier_s_remove(self):
    src = 'cell 1,"123,456,789.0"\n'
    chk = 'cell 1,123456789.0\n'
    self.assertMultiLineEqual(run(src, {1: u's/,//g'}, header=False), chk)

  def test_modifier_s_remove_unicode(self):
    src = 'cell 1,"άλφα,βήτα,γάμμα"\n'
    chk = 'cell 1,άααάα\n'
    self.assertMultiLineEqual(run(src, {1: u's/(,|[^άα])//g'}, header=False), chk)

  #----------------------------------------------------------------------------
  def test_modifier_e_directcall(self):
    self.assertEqual(sed.modifier_as_function('e/tr ab xy/')('b,a,c'), 'y,x,c')
    self.assertEqual(sed.modifier_as_function('e/xargs -I {} echo "{}^2" | bc/')('4'), '16')

  #----------------------------------------------------------------------------
  def test_modifier_e_multipipe(self):
    chk = '''\
header 1,header 2,header 3,header 4,header 5
field 1.1,field 1.2,field 1.3,1.96,field 1.5
field 2.1,field 2.2,field 2.3,5.76,field 2.5
field 3.1,field 3.2,field 3.3,11.56,field 3.5
'''
    self.assertMultiLineEqual(
      run(self.baseCsv, {3: 'e/cut -f2 -d" " | xargs -I {} echo "scale=3;{}^2" | bc/'}), chk)

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
