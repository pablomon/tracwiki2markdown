#!/usr/bin/env python
#
# Trac Wiki to Markdown converter
#
# This is a revamped version of the original work of Keisuke MORI (keisuike.mori+ha@gmail.com)
# made by Pablo Monteserín (https://pablomon.github.io/)
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

inputFile = parser.parse_args().inputFile
currentDir = parser.parse_args().currentDir

raw = False
table = False
raw_indent = '  '

list_level = -1
list_indent = [-1]

definition_list_item_indent = '&nbsp;&nbsp;&nbsp;'
is_definition_list_item = False

lines = []

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

def do_tracwiki(lineIdx, lines):
    global raw, table, is_definition_list_item, definition_list_item_indent
    line = lines[lineIdx]
    next_line = lines[lineIdx + 1] if lineIdx + 1 < len(lines) else ''

    line = re.sub(r'\\\\', '', line)

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
        line = re.sub(r', ?\d\d% ?\) ?\]\]', r')]]', line) # remove size info ( unsupported )
        line = re.sub(r'\[\[Image\(([^)]+)\)\]\]', r'![\1](/\1)', line)
        line = re.sub(r'\[\[Image\(', r'[[Image\\', line)
        line = re.sub(r'!\[(.*?)\]\(([^)]+)\)', lambda match: f'![{match.group(1).replace(":", "/")}]({match.group(2).replace(":", "/")})', line)
        line = line.replace('(/', "(/" + currentDir + '/')
        line = line.lower()

    # internal links
    line, count = re.subn(r'\[([^\s\[\]]+)\s([^\[\]]+)\]', r'[\2](\1)', line)
    if count > 0:
        line = line.replace('./', '/' + currentDir + '/')
        line = line.replace('(wiki:', "(/")

    # external links
    line = re.sub(r'\[(https?://[^\[\s\]]+)\s([^\[\]]+)\]', r'[\2](\1)', line)

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
            # find largest number of columns
            max_columns = count1
            countingIdx = lineIdx + 1
            while countingIdx < lineIdx + 50 and countingIdx < len(lines):
                temp, seps = re.subn(r'\|\|', r'|', lines[countingIdx])
                if seps == 0:
                    break
                max_columns = max(max_columns, seps)
                countingIdx += 1

            line += ' | ' * (max_columns - count1)
            if max_columns > 0:
                header = '|' + '-|' * (max_columns-1)
                line = line + '\n' + header
                table = True
    else:
        chunks = line.split('||')
        if len(chunks) == 1:
            table = False
        else:
            line = '| '
            for i in range(1,len(chunks)-1):
                line += do_tracwiki(i, chunks) + '|'
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

    ## Downloads
    #line = re.sub(r'\[download:([^\s|\]]+)\s+([^\]]*)\]',r'[\2](\\Downloads\\\1)', line) # with description
    # line = re.sub(r'\[download:([^\]]*)\]',r'[\1](\\Downloads\\\1)', line) # without description

    # italic
    # line = re.sub(r'(?<!_)(\w+)(?!_)', r'*\1*' , line)
    # bold line
    line = re.sub(r'^\*\*(.*?)', r'- \1' , line)
    # underline
    line = re.sub(r'__(.*?)__', r'<u>\1</u>' , line)
    line = re.sub(r'\/\/([A-zÀ-ú]+)\/\/', r'<u>\1</u>', line)

    # clean up
    line = re.sub(r'\\\\\s+\\\\', r'', line)
    line = re.sub(r'#!div style=".*"\s?>?', r'', line)

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
    lines.append(line.rstrip())

for i in range(len(lines) - 1):
    line = lines[i].rstrip()
    if raw:
        line = do_raw(line)
    else:
        line = do_tracwiki(i, lines)
    print(line)