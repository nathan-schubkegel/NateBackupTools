import sys
import os
import argparse
import csv
import datetime
import shutil
import subprocess
import difflib
import filecmp

# see https://docs.python.org/dev/library/argparse.html
argParser = argparse.ArgumentParser(description=
"""Runs unit tests on the scripts in this repo.""")

#argParser.add_argument('dirToScan', help='The directory to scan')

#argParser.add_argument('outFilePath', 
#  help='The path to the output file to populate with MD5 hashes')

args = argParser.parse_args()

# set stuff up
pythonPath = sys.executable

def deleteFolderContents(folderPath):
  for o in os.listdir(folderPath):
    p = os.path.join(folderPath, o)
    if os.path.isfile(p):
      os.unlink(p)
    else:
      shutil.rmtree(p)

if not os.path.exists('stuff'):
  os.mkdir('stuff')

if not os.path.exists('testResults_actual'):
  os.mkdir('testResults_actual')
deleteFolderContents('testResults_actual')

# test something
sys.stdout.write("testing findDuplicateFolders.py... ")
with open(os.devnull, "w") as fnull:
  subprocess.check_call([pythonPath,
                         'hashFolderContents.py',
                         'testData_findDuplicateFolders',
                         'stuff/testData_findDuplicateFolders_hashes.txt'],
                         stdout=fnull,
                         stderr=fnull)
  subprocess.check_call([pythonPath,
                         'findDuplicateFolders.py',
                         'stuff/testData_findDuplicateFolders_hashes.txt',
                         'testResults_actual/folders.txt'],
                         stdout=fnull,
                         stderr=fnull)
if filecmp.cmp('testResults_actual/folders.txt', 'testResults_expected/folders.txt'):
  sys.stdout.write(" ok\n")
else:
  sys.stdout.write(" failed\n")
  with open('testResults_actual/folders.txt') as f:
    actual = f.read().splitlines()
  with open('testResults_expected/folders.txt') as f:
    expected = f.read().splitlines()
  for line in difflib.unified_diff(expected, actual, fromfile='expected', tofile='actual', n=3):
    print line.rstrip("\r\n")
  sys.exit(1)
