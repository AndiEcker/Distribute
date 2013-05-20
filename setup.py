#!/usr/bin/env python
import os, sys, glob
from distutils.core import setup
import py2exe

# If run without args, build executables, in quiet mode.
if len(sys.argv) == 1:
  sys.argv.append("py2exe")
  #sys.argv.append("-q")

def files(folder):
  for path in glob.glob(folder+'/*'):
    if os.path.isfile(path):
      yield path

## changed from Pmw to Tix (because Pmw was never working with Py2Exe
## .. and also ported from Python 2.4 to 2.5.
#data_files=[
#  ('pmw', files(sys.prefix+'/lib/site-packages/pmw')),
#  ('pmw/pwm_1_2', files(sys.prefix+'/lib/site-packages/pmw/pmw_1_2')),
#  ('pmw/pwm_1_2/bin', files(sys.prefix+'/lib/site-packages/pmw/pmw_1_2/bin')),
#  ('pmw/pwm_1_2/contrib', files(sys.prefix+'/lib/site-packages/pmw/pmw_1_2/contrib')),
#  ('pmw/pwm_1_2/bin', files(sys.prefix+'/lib/site-packages/pmw/pmw_1_2/lib')),
#  ],
#
#opts = { "py2exe": { "optimize": 1, } }

# for old Tix 8.1 coming with ActivePython 2.4
#data_files=[
#    ('.', glob.glob(sys.prefix+'/DLLs/tix81*.dll')),
#    ('tcl/tix8.1', files(sys.prefix+'/tcl/tix8.1')),
#    ('tcl/tix8.1/bitmaps', files(sys.prefix+'/tcl/tix8.1/bitmaps')),
#    ('tcl/tix8.1/pref', files(sys.prefix+'/tcl/tix8.1/pref')),
#]

# pathes set for ActivePython 2.5
data_files=[
    ('.', glob.glob(sys.prefix+'/DLLs/tix84*.dll')),
    ('tcl/tix8.4.3', files(sys.prefix+'/tcl/tix8.4.3')),
    ('tcl/tix8.4.3/bitmaps', files(sys.prefix+'/tcl/tix8.4.3/bitmaps')),
    ('tcl/tix8.4.3/pref', files(sys.prefix+'/tcl/tix8.4.3/pref'))
]

opts = {'py2exe': {'packages': ['encodings', 'Tix', 'Tkinter'],
                   'bundle_files':3,}}      # not works bundled (1), set back to default (3)

# build the end user version 
setup(name='Distribute',
      version='5.0',
      data_files = data_files,
      #script_args=['py2exe'],
      windows=["Distribute.py"],
      options = opts,
      #CRASHES with: zipfile = None,     # use with bundle_files==1 for single exe (quick app startup)
     )
