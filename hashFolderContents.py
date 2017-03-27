import sys
import os
import hashlib
import argparse

# see https://docs.python.org/dev/library/argparse.html
argParser = argparse.ArgumentParser(description='Reads all files in a directory and its subdirectories. It records file paths/sizes/MD5 hashes and writes them to an output file. Each line of the output file is: <hash> <sizeText> <sizeNumber> <path>')
argParser.add_argument('dirToScan', help='The directory to scan')
argParser.add_argument('outFilePath', help='The path to the output file to populate with MD5 hashes')
args = argParser.parse_args()

def getFileHash(filePath):
  hasher = hashlib.md5()
  with open(filePath, "rb") as f:
    for chunk in iter(lambda: f.read(4096), b""):
      hasher.update(chunk)
    return hasher.hexdigest()

def getHumanReadableSize(size):
  for unit in ['-Bytes','-KB','-MB','-GB','-TB','-PB','-EB','-ZB']:
    if abs(size) < 1024.0:
      #return "%3.1f%s%s" % (size, unit, suffix)
      return "%.0f%s" % (size, unit)
    size /= 1024.0
  return "%.0f%s" % (size, '-YB')

with open(args.outFilePath, "w") as outFile:
  # inspect every file in the directory to scan
  for (dirPath, dirNames, fileNames) in os.walk(args.dirToScan):
    for fileName in fileNames:
      # get file size
      filePath = os.path.join(dirPath, fileName)
      fileSize = os.path.getsize(filePath)
      fileSizeForHumes = getHumanReadableSize(fileSize)

      # show which file is being hashed
      sys.stdout.write("reading " + filePath + " " + fileSizeForHumes + " ...");
      sys.stdout.flush();

      # get the file hash
      filehash = getFileHash(filePath)

      # report the file hash
      line = filehash + " " + fileSizeForHumes + " " + str(fileSize) + " " + filePath
      sys.stdout.write("\r");
      print(line)
      outFile.write(line + "\n")

#outFile.close()
