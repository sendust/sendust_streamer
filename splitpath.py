#  path splitter  with AHK style..
#  Code managed by sendust.. 2024/1/25
#


import os


def splitpath(infile):
    path, filename = os.path.split(infile)
    name, ext = os.path.splitext(filename)
    drive, path2 = os.path.splitdrive(infile)
    return path, filename, name, ext, drive

   
    
def filegetattrib(infile):
    if os.path.exists(infile):
        return os.stat(infile)
    else:
        return 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

def get_filesize(infile):
    if os.path.exists(infile):
        mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime = os.stat(infile)
        return size
        
    else:
        return 0


    
if __name__ == "__main__":
    path, filename, name, ext, drive = splitpath("c:/temp/c.bin")
    print(path, filename, name, ext, drive)
    mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime = filegetattrib("c:/temp/test5.cpp")
    print(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)

    

