
import sys
import os
import ntpath
import hashlib
import re
import datetime
import argparse

def getFileHash(filePath):
  hasher = hashlib.md5()
  with open(filePath, "rb") as f:
    for chunk in iter(lambda: f.read(4096), b""):
      hasher.update(chunk)
    return hasher.hexdigest()

def getHumanReadableSize(size):
  for unit in ['Bytes','KB','MB','GB','TB','PB','EB','ZB']:
    if abs(size) < 1024.0:
      return "%.0f %s" % (size, unit)
    size /= 1024.0
  return "%.0f %s" % (size, 'YB')

def splitFilePath(filePath):
  # use ntpath rather than os.path because it treats both kinds 
  # of slashes as path separators

  # drive indicators are annoying, so handle them separately
  (drive, remainingPath) = ntpath.splitdrive(filePath)
   
  # os.path.split is weird about leading slashes, so capture them separately
  leadingSlashes = ""
  poo = re.search("^([\\/]+)(.*)$", remainingPath)
  if poo:
    leadingSlashes = poo.group(1)
    remainingPath = poo.group(2)

  # split dirs and filename
  reversePathParts = []
  while True:
    (base, name) = ntpath.split(remainingPath)
    if base == "":
      if name == "":
        raise ValueError("the file path was empty - not supported")
      else:
        reversePathParts.append(name)
        break
    else:
      if name != "":
        reversePathParts.append(name)
        remainingPath = base
      else:
        raise ValueError("file path ends in a slash - not supported")

  return (drive, leadingSlashes, reversePathParts)

class MemFile:
  def __init__(self, name, fileHash, fileSize, parentDir):
    self.name = name
    self.hash = fileHash
    self.size = fileSize
    self.dir = parentDir

  def getPath(self):
    return self.dir.getPath() + '/' + self.name

class MemDirectory:
  def __init__(self, name, parentDir):
    self.files = {}
    self.dirs = {}
    self.name = name
    self.dir = parentDir

  def getPath(self):
    if self.dir == None:
      return self.name
    return self.dir.getPath() + '/' + self.name

  def add(self, fileHash, fileSize, reversePathParts):
    name = reversePathParts[-1]
    remainingParts = reversePathParts[:-1]
    if len(reversePathParts) == 1:
      newFile = MemFile(name, fileHash, fileSize, self)
      self.files[name] = newFile
      return newFile
    else:
      if name in self.dirs:
        myDir = self.dirs[name]
      else:
        myDir = MemDirectory(name, self)
        self.dirs[name] = myDir
      return myDir.add(fileHash, fileSize, remainingParts)

deduplicatedStrings = {}
def deduplicate(parts):
  i = 0
  count = len(parts)
  while i < count:
    part = parts[i]
    if part in deduplicatedStrings:
      parts[i] = deduplicatedStrings[part]
    else:
      deduplicatedStrings[part] = part
    i = i + 1

class ProgressPrinter:
  def __init__(self, messageFormat=None, countBeforeUpdate=500):
    self.number = 0
    self.timeOfLastUpdate = datetime.datetime.now()
    if messageFormat is None:
      self.messageFormat = "\rDoing thing {0}..."
    else:
      self.messageFormat = messageFormat
    self.countBeforeUpdate = countBeforeUpdate

  def report(self):
    self.number += 1
    if ( \
        self.number % self.countBeforeUpdate == 0 and \
        (datetime.datetime.now() - self.timeOfLastUpdate) > datetime.timedelta(microseconds=500000) \
       ) or (self.number == 1):
      sys.stdout.write(self.messageFormat.format(str(self.number)))
      sys.stdout.flush()
      self.timeOfLastUpdate = datetime.datetime.now()

  def reportDone(self):
    sys.stdout.write(self.messageFormat.format(str(self.number)))
    sys.stdout.write("\n")
    sys.stdout.flush()
