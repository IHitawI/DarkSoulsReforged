import sys, os, zipfile
src, dst = sys.argv[1], os.path.abspath(sys.argv[2])
prefix = chr(92) * 2 + '?' + chr(92)
zipfile.ZipFile(src).extractall(prefix + dst)
print('ok')
