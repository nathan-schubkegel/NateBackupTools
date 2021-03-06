import sys
import argparse
import nateBackupToolsCommon as common
import csv
import itertools

# see https://docs.python.org/dev/library/argparse.html
argParser = argparse.ArgumentParser(description=
"""Examines the output of \'hashFolderContents.py\' and reports duplicate
folders (those with mostly same file contents), writing them to an output file.

The output file format is csv with space as the delimiter. 

A series of rows whose first field is "parent" identifies folders
that contain mostly-matching contents. The remaining fields in the rows are:
<sizeHumanReadableText> <path>.

A series of rows whose first field is "folder" or "file" identifies the child
folders and files of all the matched "parent" folders. The remaining fields
in the rows are: <index> <sizeHumanReadableText> <similarity> <path>.
index indicates which other "folder" or "file" rows are correlated.
similarity is one of "same", "like", or "diff".

Empty rows are added between duplicate folders for human readability.""")

argParser.add_argument('hashFilePath', 
  help='The path to the input file (which was generated by \'hashFolderContents.py\'')

argParser.add_argument('outFilePath', 
  help='The path to the output file to populate with detected duplicates')

args = argParser.parse_args()

memRootDir = common.MemDirectory(name="", parentDir=None)
filesByHash = {}
progress = common.ProgressPrinter("\rReading record {0}...")
with open(args.hashFilePath, "rb") as inFile:
  csvIn = csv.reader(inFile, delimiter=' ', strict=True)
  for row in csvIn:
    # report progress once in a while
    progress.report()

    # parse line data
    (fileHash, fileSize, fileSizeForHumes, filePath) = [row[0], row[1], row[2], row[3]]
    fileSize = long(fileSize)
    (drive, leadingSlashes, reversePathParts) = common.splitFilePath(filePath)
    common.deduplicate(reversePathParts)

    # build an in-memory tree of the filesystem
    newFile = memRootDir.add(fileHash, fileSize, reversePathParts)

    # associate all files by hash
    if newFile.hash in filesByHash:
      likeFiles = filesByHash[newFile.hash]
    else:
      likeFiles = []
      filesByHash[newFile.hash] = likeFiles
    likeFiles.append(newFile)

    # sanity check for hash collisions
    if not likeFiles[0].size == newFile.size:
      raise ValueError('Files with same hash had different size!')

progress.reportDone()

class LikeDirStat:
  def __init__(self, aDir, bDir):
    if aDir is bDir:
      self.InitSingleDir(aDir)
    else:
      self.InitDifferentDirs(aDir, bDir)

  def InitSingleDir(self, aDir):
    # public fields
    self.likeFileCount = 0
    self.likeFileSize = 0
    self.dirs = sorted([aDir, aDir])
    self.dirs = (self.dirs[0], self.dirs[1])

    # determine like file count and size
    for aFileHash in aDir.filesByHash:
      aFiles = aDir.filesByHash[aFileHash]
      if len(aFiles) > 1:
        self.likeFileCount += len(aFiles)
        # size calculation assumes all files with same hash have the same size... 
        # which is true until we want to survive hash collisions =)
        self.likeFileSize += aFiles[0].size * len(aFiles)

  def InitDifferentDirs(self, aDir, bDir):
    # public fields
    self.likeFileCount = 0
    self.likeFileSize = 0
    self.dirs = sorted([aDir, bDir])
    self.dirs = (self.dirs[0], self.dirs[1])

    # determine like file count and size
    for bFileHash in bDir.filesByHash:
      bFiles = bDir.filesByHash[bFileHash]
      aFiles = aDir.filesByHash.get(bFileHash)
      if aFiles is not None:
        sharedFileCount = min(len(aFiles), len(bFiles))
        self.likeFileCount += sharedFileCount
        # size calculation assumes all files with same hash have the same size... 
        # which is true until we want to survive hash collisions =)
        self.likeFileSize += aFiles[0].size * sharedFileCount

dirPairsToIgnore = {} # key = sorted list of [dir1, dir2], value = same (not used)
bestStatsByDir = {} # key = dir, value = LikeDirStat

progress = common.ProgressPrinter("\rProcessing folder {0}...")

dirNamesToIgnore = { 
  '.git': True, 
  '.svn': True,
  'dsbudget-source-archive': True
  }

def lookForDuplicateFolders(memDir):
  # ignore anything in .git directories (or whatever directories I want to ignore)
  if memDir.name in dirNamesToIgnore:
    return

  # recurse into child directories first
  for dirName in memDir.dirs:
    childDir = memDir.dirs[dirName]
    lookForDuplicateFolders(childDir)

  # report progress once in a while
  progress.report()

  # consider each file in this directory
  for fileName in memDir.files:
    file = memDir.files[fileName]

    # consider all other identical files (across all directories)
    likeFiles = filesByHash[file.hash]
    for otherFile in likeFiles:
      likeDir = otherFile.dir

      # WACKY BUT EFFECTIVE!
      # let directories be compared against themselves, to search for duplicate files within a single directory

      # else, uncomment this block
      # ignore other files in the original directory
      #if otherFile.dir == memDir:
      #  continue

      # I'm pretty sure this never happens
      if otherFile.dir is None:
        raise ValueError('isn\'t the root directory the only thing with nil dir?')

      # serious performance boost: don't compare directories that have already been compared
      dirPair = sorted([memDir, likeDir])
      dirPair = (dirPair[0], dirPair[1])
      if dirPair in dirPairsToIgnore:
        continue

      # ok, after this point, don't compare these two directories again
      dirPairsToIgnore[dirPair] = dirPair

      # determine how similar the directories are
      stat = LikeDirStat(memDir, likeDir)

      # Reasonable matching limiter:
      # only retain paired directories if the size of their matching files is
      # at least 50% of either of their total file sizes
      if stat.likeFileCount == 0:
        continue
      if (stat.likeFileSize < memDir.sizeImmediateFilesOnly / 2) and \
         (stat.likeFileSize < likeDir.sizeImmediateFilesOnly / 2):
        # then we ignore it forever
        continue

      # Serious noise limiter: (but also prevents me from seeing when a folder is duplicated 5 times)
      # associate the directory pair with the directories only if the pair is more impressive
      # than the previous directory pair associated the directories
      bestMemDirStat = bestStatsByDir.get(memDir)
      if (bestMemDirStat is None) or (bestMemDirStat.likeFileSize < stat.likeFileSize):
        bestStatsByDir[memDir] = stat

      bestStat = bestStatsByDir.get(likeDir)
      if (bestStat is None) or (bestStat.likeFileSize < stat.likeFileSize):
        bestStatsByDir[likeDir] = stat

# enumerate all folders looking for similar ones
lookForDuplicateFolders(memRootDir)
progress.reportDone()

print "Sorting similar folders..."
# get all unique folder pair stats
allStats = {}
for stat in bestStatsByDir.itervalues():
  allStats[stat] = stat

# sort by size, and since it matters to get predictable output, which matters for tests,
# secondarily sort by paths too
sortedStats = sorted(allStats, key=lambda s: (-s.likeFileSize, \
                                              sorted([s.dirs[0].getPath(), s.dirs[1].getPath()])[0], \
                                              sorted([s.dirs[0].getPath(), s.dirs[1].getPath()])[1]))

progress = common.ProgressPrinter("\rWriting duplicate folder data {0}...")
with open(args.outFilePath, "wb") as outFile:
  csvOut = csv.writer(outFile, delimiter=' ', strict=True)
  for stat in sortedStats:
    #csvOut.writerow(["stat", "likesize", stat.likeFileSize]);
    #csvOut.writerow(["stat", "likecount", stat.likeFileCount]);

    # report progress once in a while
    progress.report()

    aDir = stat.dirs[0]
    bDir = stat.dirs[1]

    # write rows indicating the parent folder sizes and paths
    if aDir is bDir:
      csvOut.writerow(["parent", "compared against itself", common.getHumanReadableSize(aDir.size), aDir.getPath()])
    else:
      csvOut.writerow(["parent", "left", common.getHumanReadableSize(aDir.size), aDir.getPath()])
      csvOut.writerow(["parent", "right", common.getHumanReadableSize(bDir.size), bDir.getPath()])

    # plan the rows to write out
    # (because we need to write summary rows first)
    rows = []
    summarySameFilesCount = 0
    summarySameFilesSize = 0
    summaryDifferentFilesCount = 0
    summaryDifferentFilesSize = 0
    summaryChangedFilesCount = 0
    summaryChangedFilesSize = 0
    summaryLeftOnlyFilesCount = 0
    summaryLeftOnlyFilesSize = 0
    summaryRightOnlyFilesCount = 0
    summaryRightOnlyFilesSize = 0

    if aDir is bDir:
      # write rows indicating duplicated files
      hashesDuplicated = set([aHash for aHash in aDir.filesByHash if len(aDir.filesByHash[aHash]) > 1])
      # order the rows by size
      for h in sorted(hashesDuplicated, key=lambda h: -aDir.filesByHash[h][0].size):
        aFiles = aDir.filesByHash[h]
        
        summarySameFilesSize += aFiles[0].size * len(aFiles)
        summarySameFilesCount += len(aFiles)

        # write as multiple rows
        size = aFiles[0].size
        rows.append(["files", "same", common.getHumanReadableSize(size * len(aFiles))])

        # write rows sorted by file name
        aNames = set([f.name for f in aFiles])
        for n in sorted(aNames):
          rows.append(["  ", "file", common.getHumanReadableSize(size), n])

      # write all other files, sorted by size
      hashesNotDuplicated = set([aHash for aHash in aDir.filesByHash if len(aDir.filesByHash[aHash]) == 1])
      if len(hashesNotDuplicated) > 0:
        myRows = []
        mySize = 0
        for h in sorted(hashesNotDuplicated, key=lambda h: -aDir.filesByHash[h][0].size):
          aFile = aDir.filesByHash[h][0]

          mySize += aFile.size
          summaryDifferentFilesSize += aFile.size
          summaryDifferentFilesCount += 1

          myRows.append(["  ", "file", common.getHumanReadableSize(aFile.size), aFile.name])

        rows.append(["files", "different", common.getHumanReadableSize(mySize)])
        for r in myRows:
          rows.append(r)

    else: # aDir != bDir

      # write rows indicating duplicated files (whether the file appears on both sides or just 1 side)
      hashesOnBothSides = set().intersection(aDir.filesByHash, bDir.filesByHash)
      hashesDuplicatedOnSingleSide = set() \
          .union([aHash for aHash in aDir.filesByHash if len(aDir.filesByHash[aHash]) > 1], \
                 [bHash for bHash in bDir.filesByHash if len(bDir.filesByHash[bHash]) > 1])
      hashesDuplicated = hashesOnBothSides.union(hashesDuplicatedOnSingleSide)
      # order the rows by size
      for h in sorted(hashesDuplicated, key=lambda h: -aDir.filesByHash.get(h, bDir.filesByHash.get(h))[0].size):
        aFiles = aDir.filesByHash.get(h, [])
        bFiles = bDir.filesByHash.get(h, [])

        if len(aFiles) > 0:
          summarySameFilesSize += aFiles[0].size * len(aFiles)
          summarySameFilesCount += len(aFiles)
        if len(bFiles) > 0:
          summarySameFilesSize += bFiles[0].size * len(bFiles)
          summarySameFilesCount += len(bFiles)

        # if possible, write as 1 row
        #if len(aFiles) == 1 and len(bFiles) == 1 and aFiles[0].name == bFiles[0].name:
        #  rows.append(["files", "same", common.getHumanReadableSize(aFiles[0].size), aFiles[0].name])
        #  continue

        # else, write as multiple rows
        count = 0
        if len(aFiles) > 0:
          size = aFiles[0].size
          count += len(aFiles)
        if len(bFiles) > 0:
          size = bFiles[0].size
          count += len(bFiles)
        rows.append(["files", "same", common.getHumanReadableSize(size * count)])

        # write rows sorted by file name
        aNames = set([f.name for f in aFiles])
        bNames = set([f.name for f in bFiles])
        for n in sorted(set().union(aNames).union(bNames)):
          presence = "both" if (n in aNames and n in bNames) else ("left" if n in aNames else "right")
          rows.append(["  ", presence, common.getHumanReadableSize(size), n])

      # get hashes indicating non-duplicated files
      aOnlyHashes = set(aDir.filesByHash).difference(hashesDuplicated)
      aOnlyHashesByName = {aDir.filesByHash[h][0].name: h for h in aOnlyHashes}
      #aOnlyHashesSorted = sorted(aOnlyHashes, key=lambda h: (-aDir.filesByHash[h][0].size, aDir.filesByHash[h][0].name))

      bOnlyHashes = set(bDir.filesByHash).difference(hashesDuplicated)
      bOnlyHashesByName = {bDir.filesByHash[h][0].name: h for h in bOnlyHashes}
      #bOnlyHashesSorted = sorted(bOnlyHashes, key=lambda h: (-bDir.filesByHash[h][0].size, bDir.filesByHash[h][0].name))

      # get hashes of non-duplicated files on opposite sides with the same name
      sharedNameFilePairs = {}
      sharedNameHashes = set()
      for n in aOnlyHashesByName:
        aHash = aOnlyHashesByName[n]
        if n in bOnlyHashesByName:
          bHash = bOnlyHashesByName[n]
          sharedNameFilePairs[n] = (aDir.filesByHash[aHash][0], bDir.filesByHash[bHash][0])
          sharedNameHashes.add(aHash)
          sharedNameHashes.add(bHash)

      # write all "same name, different contents" files, sorted by size (then by name for maximally sorted output)
      aSharedNameRows = []
      aSharedNameSize = 0
      aSharedNameCount = 0;
      for name in sorted(sharedNameFilePairs, \
                         key=lambda n: ( -max(sharedNameFilePairs[n][0].size, sharedNameFilePairs[n][1].size), n )):
        files = sharedNameFilePairs[name]
        aSharedNameRows.append(["  ", "left", common.getHumanReadableSize(files[0].size), files[0].name])
        aSharedNameRows.append(["  ", "right", common.getHumanReadableSize(files[1].size), files[1].name])
        aSharedNameSize += files[0].size + files[1].size
        aSharedNameCount += 2

      summaryChangedFilesSize += aSharedNameSize
      summaryChangedFilesCount += aSharedNameCount

      if len(aSharedNameRows) > 0:
        rows.append(["files", "changed", common.getHumanReadableSize(summaryChangedFilesSize)])
        for r in aSharedNameRows:
          rows.append(r)

      # write all "different names, different contents" files, sorted first by side then by size
      aOtherRows = []
      bOtherRows = []
      aOnlySummarySize = 0
      aOnlySummaryCount = 0
      bOnlySummarySize = 0
      bOnlySummaryCount = 0
      for h in sorted(aOnlyHashes.difference(sharedNameHashes), \
                      key=lambda h: ( -aDir.filesByHash[h][0].size, aDir.filesByHash[h][0].name)):
        f = aDir.filesByHash[h][0]
        aOtherRows.append(["  ", "left", common.getHumanReadableSize(f.size), f.name])
        aOnlySummarySize += f.size
        aOnlySummaryCount += 1
      for h in sorted(bOnlyHashes.difference(sharedNameHashes), \
                      key=lambda h: ( -bDir.filesByHash[h][0].size, bDir.filesByHash[h][0].name)):
        f = bDir.filesByHash[h][0]
        bOtherRows.append(["  ", "right", common.getHumanReadableSize(f.size), f.name])
        bOnlySummarySize += f.size
        bOnlySummaryCount += 1

      if len(aOtherRows) > 0:
        rows.append(["files", "left-only", common.getHumanReadableSize(aOnlySummarySize)])
        for r in aOtherRows:
          rows.append(r)
      if len(bOtherRows) > 0:
        rows.append(["files", "right-only", common.getHumanReadableSize(bOnlySummarySize)])
        for r in bOtherRows:
          rows.append(r)

      summaryLeftOnlyFilesSize += aOnlySummarySize
      summaryLeftOnlyFilesCount += aOnlySummaryCount
      summaryRightOnlyFilesSize += bOnlySummarySize
      summaryRightOnlyFilesCount += bOnlySummaryCount

    # write the summary rows
    if summarySameFilesCount > 0:
      csvOut.writerow(["summary", "same", "files", common.getHumanReadableSize(summarySameFilesSize)])
    if summaryDifferentFilesCount > 0:
      csvOut.writerow(["summary", "different", "files", common.getHumanReadableSize(summaryDifferentFilesSize)])
    if summaryChangedFilesCount > 0:
      csvOut.writerow(["summary", "changed", "files", common.getHumanReadableSize(summaryChangedFilesSize)])
    if summaryLeftOnlyFilesCount > 0:
      csvOut.writerow(["summary", "left-only", "files", common.getHumanReadableSize(summaryLeftOnlyFilesSize)])
    if summaryRightOnlyFilesCount > 0:
      csvOut.writerow(["summary", "right-only", "files", common.getHumanReadableSize(summaryRightOnlyFilesSize)])

    # write the detail rows
    for r in rows:
      csvOut.writerow(r)

    # write a blank row for readability
    csvOut.writerow([])

progress.reportDone()
print 'done'
