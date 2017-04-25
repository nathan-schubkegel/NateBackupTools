import sys
import os
import argparse
import nateBackupToolsCommon as common
import csv
import datetime

# see https://docs.python.org/dev/library/argparse.html
argParser = argparse.ArgumentParser(description=
"""Reads all files in a directory and its subdirectories.
It records file paths/sizes/MD5 hashes and writes them to an output file.
The output file format is csv with space as the delimiter for the following
fields: <hash> <sizeNumber> <sizeHumanReadableText> <path>""")

argParser.add_argument('dirToScan', help='The directory to scan')

argParser.add_argument('outFilePath', 
  help='The path to the output file to populate with MD5 hashes')

args = argParser.parse_args()

# write binary because CSV writer requires that
with open(args.outFilePath, "wb") as outFile:
  csvOut = csv.writer(outFile, delimiter=' ', strict=True)

  # inspect every file in the directory to scan
  for (dirPath, dirNames, fileNames) in os.walk(args.dirToScan):
    for fileName in fileNames:
      # get file size
      filePath = os.path.join(dirPath, fileName)
      fileSize = os.path.getsize(filePath)
      fileSizeForHumes = common.getHumanReadableSize(fileSize)

      # show which file is being hashed
      sys.stdout.write("reading " + filePath + ", " + fileSizeForHumes)
      sys.stdout.flush()

      # get the file hash
      startTime = datetime.datetime.now()
      fileHash = common.getFileHash(filePath)
      endTime = datetime.datetime.now()

      # report the file hash
      csvOut.writerow([fileHash, fileSize, fileSizeForHumes, filePath])

      # report how long it took
      totalSeconds = int((endTime - startTime).total_seconds())
      (hours, remainder) = divmod(totalSeconds, 3600)
      (minutes, seconds) = divmod(remainder, 60)
      sys.stdout.write(", %sh:%sm:%ss\n" % (hours, minutes, seconds))
