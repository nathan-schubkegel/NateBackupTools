import argparse
import csv

# see https://docs.python.org/dev/library/argparse.html
argParser = argparse.ArgumentParser(description=
"""Upgrades the output of \'hashFolderContents.py\' from
its original format (lines of space-concatenated fields)
to its more recent format (lines of space-delimited CSV fields)""")

argParser.add_argument('hashFilePath', 
  help='The path to the input file (which was generated by the original \'hashFolderContents.py\'')

argParser.add_argument('outFilePath', 
  help='The path to the output file (which looks like it\'s generated by the more recent \'hashFolderContents.py\'')

args = argParser.parse_args()

rows = []
with open(args.hashFilePath, "rb") as inFile:
  for line in inFile:
    # stupid python and its newlines
    line = line.rstrip("\r\n")

    # parse line data
    (fileHash, fileSizeForHumes, fileSize, filePath) = line.split(None, 3)

    # save reordered line data
    rows.append([fileHash, fileSize.rstrip('b'), fileSizeForHumes, filePath])

with open(args.outFilePath, "wb") as outFile:
  csvOut = csv.writer(outFile, delimiter=' ', strict=True)
  for row in rows:
    # write a row with file size and all unique file names 
    csvOut.writerow(row)
