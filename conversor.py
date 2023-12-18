#!/usr/bin/env python
#
# Trac Wiki to Markdown converter
#
# Copyright(c) 2019 Keisuke MORI (keisuike.mori+ha@gmail.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

### for Python 2/3 compatible code in Python 3 style
#    https://stackoverflow.com/questions/5868506/backwards-compatible-input-calls-in-python
##   print
from __future__ import print_function
##   raw_input/input
if hasattr(__builtins__, 'raw_input'):
    input = raw_input
## urllib
#   'urllib is the hardest module to use from Python 2/3 compatible code.'
#    - from https://python-future.org/compatible_idioms.html
try:
    # Python 3
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    # Python 2.7
    from urllib2 import urlopen, Request, HTTPError

import sys
import re

import ssl
import getpass
import base64
import io

import argparse

parser = argparse.ArgumentParser(description='Translator from Trac Wiki to Markdown')
parser.add_argument('--inputFile', type=str, help='The file to translate')
parser.add_argument('--currentDir', type=str, default='.', help='Directory of the current page')
# parser.add_argument('--lang', type=str, default='', help='Language root for wikijs')

# Parsea los argumentos de la línea de comandos
inputFile = parser.parse_args().inputFile
currentDir = parser.parse_args().currentDir
# lang = parser.parse_args().lang

raw = False
table = False
raw_indent = '  '

list_level = -1
list_indent = [-1]

definition_list_item_indent = '&nbsp;&nbsp;&nbsp;'
is_definition_list_item = False

def list_adjust_indent(m):
    global list_level, list_indent
    num_spaces = len(m.group(1))

    while num_spaces < list_indent[-1]:
        list_level -= 1
        list_indent = list_indent[:-1]
    if num_spaces > list_indent[-1]:
        list_level += 1
        list_indent.append(num_spaces)

    return (' ' * (1 + list_level * 2)) + '* '

def do_raw(line):
    global raw
    line, count = re.subn(r'^}}}$', r'```', line)
    if count > 0:
        raw = False
    line = raw_indent + line
    return line

def do_tracwiki(line, next_line):
    global raw, table, is_definition_list_item, definition_list_item_indent

    # list
    line = re.sub(r'^(\s*)\* ', list_adjust_indent, line)
    line = re.sub(r'^(\s*)\- ', list_adjust_indent, line)

    # remove leading spaces
    line = re.sub(r'^(\s*)', r'', line)

    # section
    line = re.sub(r'^====\s+(.*?)(\s+====)?$', r'#### \1', line)
    line = re.sub(r'^===\s+(.*?)(\s+===)?$', r'### \1', line)
    line = re.sub(r'^==\s+(.*?)(\s+==)?$', r'## \1', line)
    line = re.sub(r'^=\s+(.*?)(\s+=)?$', r'# \1', line)

    # text
    line = re.sub(r'\'\'\'(.*?)\'\'\'', r'*\1*', line)
    line = re.sub(r'\'\'(.*?)\'\'', r'_\1_', line)

    # code
    line = re.sub(r'{{{#!sh(.*?)}}}', r'`\1`', line)
    line = re.sub(r'{{{(.*?)}}}', r'`\1`', line)

    # images
    if re.match(r'^\[\[Image\(', line):
        line = re.sub(r', ?\d\d% ?\) ?\]\]', r')]]', line) # size is not supported
        line = re.sub(r'\[\[Image\(([^)]+)\)\]\]', r'![\1](/\1)', line)
        line = re.sub(r'\[\[Image\(', r'[[Image\\', line)
        line = re.sub(r'!\[(.*?)\]\(([^)]+)\)', lambda match: f'![{match.group(1).replace(":", "/")}]({match.group(2).replace(":", "/")})', line)
        line = line.replace('(/', "(/" + currentDir + '/')
        line = line.lower()

    # external links
    line = re.sub(r'\[(https?://[^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](\1)', line)

    # internal links
    line, count = re.subn(r'\[([^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](\1)', line)
    if count > 0:
        line = line.replace('./', '/' + currentDir + '/')
        line = line.replace('(wiki:', "(/")

    # section link
    line = re.sub(r'\[(#[^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](\1)', line)
    # section anchor
    line = re.sub(r'\s#([^\s\[\]]+)', r' <a id="\1"></a>', line)

    # links like !text= are not supported
    line = re.sub(r'!(.*?)=', lambda match: match.group(1), line)

    # table
    if not table:
        line, count1 = re.subn(r'\|\|', r'|', line)
        if count1 > 0:
            temp, count2 = re.subn(r'\|\|', r'|', next_line)
            line += ' | ' * (count2 - count1)
            if count2 > 0:
                header = '|' + '-|' * (count2-1)
                line = line + '\n' + header
                table = True
    else:
        chunks = line.split('||')
        if len(chunks) == 1:
            table = False
        else:
            line = '|'
            for chunk in chunks:
                line += do_tracwiki(chunk, '') + '|'
            table = True

    # macro
    line = re.sub(r'(?i)\[\[BR\]\]', r'<br />', line)
    #  TOC is not supported - use other tools
    line = re.sub(r'\[\[PageOutline.*\]\]', r'', line)

    # translated pages - not supported
    line = re.sub(r'\[\[TranslatedPages\]\]', r'', line)
    
    # raw
    line = line.replace('{{{#!sh', '{{{')
    line, count = re.subn(r'\s*{{{$', r'```', line)
    if count > 0:
        raw = True
        line = raw_indent + line

    # definition list
    if line == '':
        is_definition_list_item = False
    if is_definition_list_item:
        # si empieza por *,- o + 
        if re.match(r'^\s*[\*\-\+]', line):
            line = re.sub(r'^\s*[\*\-\+]', r'', line)
            line = "- " + definition_list_item_indent + line
        if re.match(r'^\s*[a-zA-Z]+\.', line):
            line = definition_list_item_indent + line
    
    if re.match(r'.*::$', line):
        line = re.sub(r'::$', r'', line)
        line = re.sub(r'^\s+', r'', line)
        line = "**" + line + "**"
        is_definition_list_item = True

    # source code
    line = re.sub(r'\[source:(.*?)\]', r'\1', line)

    # italic
    # line = re.sub(r'_(\w+)_', r'*\1*' , line)
    # bold line
    line = re.sub(r'^\*\*(.*?)', r'- \1' , line)
    # underline
    line = re.sub(r'__(.*?)__', r'<u>\1</u>' , line)

    return line

###

def get_from_url(url):
    # redirect prompts to stderr to allow to redirect the converted output
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    user = input('Trac username: ') # raw_input() in Python 2
    password = getpass.getpass('Trac Password: ')
    sys.stdout = old_stdout

    headers = {}
    headers['Authorization'] = 'Basic ' + base64.b64encode((user + ':' + password).encode('utf-8')).decode('utf-8') # Python3 compatible
#    headers['Authorization'] = 'Basic ' + (user + ':' + password).encode('base64')[:-1] # Python 2 only

    # WARN: it's to disable SSL Certificate Verification
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    req = Request(url=url + '?format=txt', headers=headers)
    response = urlopen(req, context=ctx)
    return io.BytesIO(response.read())


######################

if len(sys.argv) > 1:
    if inputFile.startswith(('http://', 'https://')):
        trac_input = get_from_url(inputFile)
    else:
        trac_input = open(inputFile)
else:
    trac_input = sys.stdin

lines = []
for line in trac_input:
    lines.append(line)

for i in range(len(lines) - 1):
    line = lines[i].rstrip()
    next_line = ''
    if (i + 1) < len(lines):
        next_line = lines[i + 1].rstrip()
    if raw:
        line = do_raw(line)
    else:
        line = do_tracwiki(line, next_line)

    print(line)