""" Distribute omnis libs
    (c) 2005 aecker@resortp.com
    - V0.2 adds string table distribution, renamed variables.
    - V0.3 adds GUI.
    - V0.4 adds error checking and distribution check (Master and Client libs).
    - V0.5 added checkboxes for to close O$4-dev and for to check XL/RP separately.
    - V0.6 added user settings (distribute.cfg),
           added TabPane for to separate Distributor from Checker,
           added Cancel of CheckDistribution,
           added single machine CheckDistribution (txtMachine),
           added code for to distribute a new (not yet distributed) library.
    - V0.7 added MsOmnis4Exe1/2 for Brett's spanish windows.
    - V0.8 disabled the checkboxes of recently distributed libs and added
           a default user section in the cfg file for new users.
    - V0.9 CheckDistribution now checks several O$ installations on
           the same machine (for reservation machines).
    - V1.0 updated the machine names of Resortp
    - V1.1 added machines *GOB* for the housekeepers and the new folder
           'OS401 RT2' (for the second O$ installation for Resv.staff)
    - V2.0 removed the conversion of distributed libs into O$4.
    - V2.1 added some XLTLA machines for the distribution checker.
    - V2.2 changed //fserver/ResortP/ into R:/
    - V2.3 added new file distribution checker tab
    - V2.4 changed RP distribution folder from oraclerp to tldc1
    - V2.5 changed distribution checker path from ResortProperties to Acumen
    - V2.6 added new Omnis 4.2 folders
    - V2.7 added non-unicode sub-folder (nonuni) to C:\buildfolder path
    - V2.8 changed MsSrcPath to unicode buildfolder path
    - V2.9 split MsSrcPath into two new vars: MsLibSrcPath and MsStbSrcPath.
    - V3.0 changed buildfolder path back to nonuni and finally removed MsStbSrcPath.
    - V3.1 changed MasterLibs MsDistPath* variables into list - needed for to
           add ARGOS server to distribution (and to remove APOLO later)  AND
           removed in MlsClientPaths the old Omnis321 installation check paths  AND
           replaced Pmw with Tix to be easier compiled into EXE file  AND  created py2exe setup script  AND
           started to update Omnis machine name lists (had to stop because currently running renaming process
           - possibly finished in February 2009 by Ruben).
    - V3.2 added UAT distribution (quick+dirty, still need to refactored global M variables)  AND
           possibility to reset Base A/B/C to current live libraries (MasterLibs4).
    - V3.3 added logging and fixed bug with STB roll out (from OS42).
    - V3.4 added two more test bases/slots D and E.
    - V3.5 fixed bug with logging (shutdown() was missing to close and reopen file on distribution destination change).
    - V3.6 extended live distribution with path \\tldc2.resortp.com\masterlibs4.
    - V3.7 removed tldc1 live distribution path.
    - V3.8 changed public network paths to fit new infrastructure/environment (using net the drive letters
           R: and U: where possible - already not M: and N: for masterlibs folders).
    - V3.9 changed TLDC2 into M: drive.
    - V4.0 Added LAUNCHER.INI setup and rearranged distribution tab controls.
    - V4.1 Prepared for the usage in Malta: migrated most of the hard-coded path names into CFG file.
    - V4.2 Added new local libs folders: C:/acumen and also for all other Omnis developer installations
           AND added combo box for to select the TNS name
           AND fixed widget state bugs (set to 'active' instead of 'normal').
    - V4.3 Added silverpoint/tensel machine names (and changed RP to SP).
    - V4.4 Changed LIVE distribution folders to point to new Silverpoint MasterLibs5 folders (still using Omnis 4.2).
    - V4.5 Excluded DfsrPrivate folder from copying from LIVE libraries command.
    - V4.6 Extended to 7 test bases (and refactored to be dynamically even further extensible by changing UATDestCount
           config/ini variable). Now is preparing the DEBUG environment (if IS_DEBUG is True). Also done some
           cosmetic changes (variable names, ...).
    - V4.7 added new ACUMENAPP distribution source path and automatic search of OS*/Acumen sub dirs.
    - V5.0 Migrated to handle Omnis 5 libraries only (paths).
    - V5.1 replaced U: drive with //acumen.es/files/Test_Libraries
"""
VERSION = '5.1'  # CHANGE ALSO IN setup.py !!!

import zipfile
import glob, os, sys
import datetime
from datetime import timedelta
import shutil
from stat import ST_MTIME
from time import ctime

import Tkinter
from Tkinter import *
import Tix

# import win32con, win32api, win32gui
import win32api
import ConfigParser
import filecmp
import logging
logging.raiseExceptions = False

#######################
# general constants
#######################
IS_DEBUG  = False # True                        # CHANGE TO FALSE before compile for distributing

TODAY_DATETIME = datetime.datetime.today()
EXT_LBS = ".LBS"
EXT_STB = ".STB"
EXT_ZIP = ".ZIP"
PATH_BUILD_LIBS = "C:/BuildFolder/"     # used as default path and for debug root path for debug mode
PATHS_DEV_LIBS = [ "C:/ACUMENAPP/"
                  ,"C:/Program Files/TigerLogic/"
                  ,"C:/Program Files (x86)/TigerLogic/"
                  ,"C:/Acumen/"
                 ]

PATH_PREFIX_UAT = "//acumen.es/files/Test_Libraries/UAT_Libs"
NEW_LIB_PREFIX = 'NEW: '
NEW_LIB_VERSION_LIVE = '0.99'   # will distribute as V1.00, only for live distribution
NEW_LIB_VERSION_UAT = '0.9'     # .. as V1.0 for UAT distribution
FOLDER_IGNORE_ON_COPY = 'DfsrPrivate'

CHKLIB_MAXROWS = 5              # number of rows reserved for the lib check boxes in the distribution tab grid

# configurable constants (could be overwritten from CFG file)
# .. first prepare environment for it
def ConfigInitAndLoad():
    global MoConfig, MsMainSection, MsUserSection
    MoConfig = ConfigParser.RawConfigParser()
    fp = ConfigOpen('r')
    MoConfig.readfp(fp)
    fp.close()
    MsMainSection = '__default_user__'   # CFG file default section (also keeps general settings)
    MsUserSection = win32api.GetUserName()
    
def ConfigOpen(sOpenMode):
    path = sys.argv[0]
    path = os.path.dirname(path)
    path = os.path.abspath(path)
    return open(path + '/distribute.cfg', sOpenMode)    # 'w' needed for add_section/set/...

def ConfigSavePrepare():
    # prepare config settings saving (also check if user using the app the first time)
    global MoConfig, MsUserSection
    if not MoConfig.has_section(MsUserSection):
        # default settings (if there is already no user cfg section)
        MoConfig.add_section(MsUserSection)

def ConfigSaveComplete():
    # do the cfg file update (save current users settings)
    global MoConfig
    fp = ConfigOpen('w') # open for write to rewrite all with changes
    MoConfig.write(fp)
    fp.close()

def ConfigBool(sItem, bDefault = False):
    global MoConfig, MsMainSection, MsUserSection
    if MoConfig.has_option(MsUserSection, sItem):
        bRet = MoConfig.getboolean(MsUserSection, sItem)
    elif MoConfig.has_option(MsMainSection, sItem):
        bRet = MoConfig.getboolean(MsMainSection, sItem)
    else:
        bRet = bDefault
    return bRet

def ConfigNumber(sItem, nDefault = 0):
    global MoConfig, MsMainSection, MsUserSection
    if MoConfig.has_option(MsUserSection, sItem):
        nRet = MoConfig.getfloat(MsUserSection, sItem)
    elif MoConfig.has_option(MsMainSection, sItem):
        nRet = MoConfig.getfloat(MsMainSection, sItem)
    else:
        nRet = nDefault
    return nRet

def ConfigString(sItem, sDefault = ''):
    global MoConfig, MsMainSection, MsUserSection
    if MoConfig.has_option(MsUserSection, sItem):
        sRet = MoConfig.get(MsUserSection, sItem)
    elif MoConfig.has_option(MsMainSection, sItem):
        sRet = MoConfig.get(MsMainSection, sItem)
    else:
        sRet = sDefault
    return sRet

def ConfigList(sCountItem, sListItemPrefix, lDefault):
    global MoConfig, MsMainSection, MsUserSection
    if MoConfig.has_option(MsUserSection, sCountItem):
        lRet = [ MoConfig.get(MsUserSection, sListItemPrefix + str(nI + 1))
                 for nI in range(MoConfig.getint(MsUserSection, sCountItem)) ]
    elif MoConfig.has_option(MsMainSection, sCountItem):
        lRet = [ MoConfig.get(MsMainSection, sListItemPrefix + str(nI + 1))
                 for nI in range(MoConfig.getint(MsMainSection, sCountItem)) ]
    else:
        lRet = lDefault
    return lRet
    

# .. now init MoConfig and MsUserSection and load cfg file
ConfigInitAndLoad()

# init. UAT slot/base count (used also as radio button IDs): UAT bases/slots=0...(MnUATDestCount-1), LIVE=MnUATDestCount
MnUATDestCount = ConfigNumber('UATDestCount', 7)   # should be odd number (to totally result in a pair number including the LIVE distribution destination)
MnLiveDestID = MnUATDestCount
DEST_UAT_A_CHR_ORD = ord('A') 


# determine once on startup the available source lib pathes (1st one is always the omnis buildfolder)
MlsSrcLibPaths = [ ConfigString('ClientBuildPath', PATH_BUILD_LIBS) ]
for srcPath in PATHS_DEV_LIBS:
    if os.path.exists(srcPath):
        if srcPath[-8:] != '/Acumen/':
            for subdir in os.listdir(srcPath):
                fulldir = os.path.join(srcPath, subdir + '/', 'Acumen/')
                if subdir[:3] == 'OS5' and os.path.exists(fulldir) and fulldir not in MlsSrcLibPaths:
                    MlsSrcLibPaths.append(fulldir)
        elif srcPath not in MlsSrcLibPaths:
            MlsSrcLibPaths.append(srcPath)

# determine log, zip/backup, build-default and distribution paths
# .. in TF: "//MINERVA.acumen.es/resortp/ADMINISTRATORS/" or "R:/ADMINISTRATORS/"
MsLogRootPath = ConfigString('LogRootPath', "//acumen.es/files/Test_Libraries/DistToolLog/")
# .. in TF: "NewSalesSys/Backup/"
MsZipPath = MsLogRootPath + ConfigString('ZipFolder', "Backup/")
MsBuildDefPath = MsLogRootPath + ConfigString('BuildFolder', "Build/")
# .. get distribution destination paths - 1st is master path
MlsLiveDistPaths = ConfigList('DistPathCount', 'DistPath', [ "//acumen.es/files/Masterlibs/", "//argos.xlresorts.corp/masterlibs/" ])
                # was [ "//MINERVA.acumen.es/masterlibs4/", "//Argos/MasterLibs4/" ]  
if IS_DEBUG:
    # tweak global vars for debug/test run (and create copy of masterlibs, build and backup/zip folders underneath test log path)
    MsLogRootPath = PATH_BUILD_LIBS + "test/"
    ## using tweaked shutil.copytree from Python 2.6 -- replace with original when upgraded to 2.7/3.1 -- used to prepare debug env.
    def ignore_path(sSrcPath, lNames):
        #if sSrcPath[-len(FOLDER_IGNORE_ON_COPY):] == FOLDER_IGNORE_ON_COPY:  # this will try at least to create the DfsrPrivate folder
        #    return lNames
        if FOLDER_IGNORE_ON_COPY in lNames:
            return [FOLDER_IGNORE_ON_COPY]
        else:
            return []
    class Error(EnvironmentError):
        pass
    def copytree_V6(src, dst, symlinks=False, ignore=None):
        names = os.listdir(src)
        if ignore is not None:
            ignored_names = ignore(src, names)
        else:
            ignored_names = set()
    
        os.makedirs(dst)
        errors = []
        for name in names:
            if name in ignored_names:
                continue
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    os.symlink(linkto, dstname)
                elif os.path.isdir(srcname):
                    copytree_V6(srcname, dstname, symlinks, ignore)
                else:
                    shutil.copy2(srcname, dstname)
                # XXX What about devices, sockets etc.?
            except (IOError, os.error), why:
                errors.append((srcname, dstname, str(why)))
            # catch the Error from the recursive copytree so that we can
            # continue with other files
            except Error, err:
                errors.extend(err.args[0])
        try:
            shutil.copystat(src, dst)
        except WindowsError:
            # can't copy file access times on Windows
            pass
        except OSError, why:
            if WindowsError is not None and isinstance(why, WindowsError):
                # Copying file access times may fail on Windows
                pass
            else:
                errors.extend((src, dst, str(why)))
        if errors:
            raise Error(errors)
    # preparing debug environment by ...:
    # .. copy (at least the first two) MasterLibs folder to local machine (def=c:/BuildFolder/nonuni/test/MstLibs1|2)
    lTestLiveDistPaths = []
    for nI in range(min(len(MlsLiveDistPaths),2)):
        sPath = MsLogRootPath + 'MstLibs' + str(nI)
        if os.path.exists(sPath):
            shutil.rmtree(sPath)
        ##shutil.copytree(MlsLiveDistPaths[nI], sPath, ignore=shutil.ignore_patterns(FOLDER_IGNORE_ON_COPY))  
        ## .. before Python 2.6 there is no ignore parameter, so copies silly DfsrPrivate folders (if accessible)
        copytree_V6(MlsLiveDistPaths[nI], sPath, ignore=ignore_path)
        lTestLiveDistPaths.append(sPath)
    MlsLiveDistPaths = lTestLiveDistPaths
    # .. create the zip/backup and build folders (def=c:/BuildFolder/nonuni/test/Backup and c:/BuildFolder/nonuni/test/Build)
    MsZipPath = MsLogRootPath + "Backup/"
    if not os.path.exists(MsZipPath):
        os.mkdir(MsZipPath)
    MsBuildPath = MsLogRootPath + "Build/"   # UAT and LIVE builds go together!
    if not os.path.exists(MsBuildPath):
        # .. create path by copying the files from S:/ADMINISTRATORS/Omnis Builds into test build path
        shutil.copytree('S:/ADMINISTRATORS/Omnis builds', MsBuildPath)
    MsLogPath = MsBuildPath + "Log/"


# global variables that change (needed since V3.2/UAT extension)
# changed q&d - needs refactoring into configuration/settings class?!?!?
MoLogger = None
MlsDistPaths = []    # init. later on first call of DistInitPaths()
def DistInitPaths(srcLibIndex, distDest):
    global MlsDistPaths, MsBuildPath, MsBuildDefPath, MsLibSrcPath, MlsSrcLibPaths, MsLogPath, MoLogger
    if distDest == MnLiveDestID:
        MlsDistPaths = MlsLiveDistPaths
    else:
        MlsDistPaths = [ PATH_PREFIX_UAT + unichr(DEST_UAT_A_CHR_ORD + distDest) + "/" ]
    
    if IS_DEBUG:
        # on debug MsBuildPath and MsLogPath are setup once on startup
        loglevel = logging.DEBUG
    else:
        if distDest == MnLiveDestID:
            MsBuildPath = MsBuildDefPath
        else:
            MsBuildPath = MsBuildDefPath + "UAT_builds/"
        MsLogPath = MsBuildPath + "Log/"
        loglevel = logging.INFO
    # (re)configuring logging
    if MoLogger:
        logging.shutdown(logging.root.handlers)   # closes file handler, prepare for basicConfig()
        logging.root.handlers = []  ## needed for basicConfig() to reinit the logging package 
    logging.basicConfig(level = loglevel,
                        datefmt='%d %b %Y %H:%M:%S', 
                        filename = MsLogPath + "DistLog" + str(TODAY_DATETIME.year) + ".log",
                        format = '%(asctime)s %(levelname)-8s %(message)s')
    MoLogger = logging.getLogger()
        
    MsLibSrcPath = MlsSrcLibPaths[srcLibIndex]
    
# company machines
MsMachinesXL = ['hmcresv01'] + ['hmcgob01', 'hmcgob02'] \
             + ['hmcrec0' + str(nI) for nI in range(1,8)] \
             + ['bhcresv01'] + ['bhcgob01'] \
             + ['bhcrec0' + str(nI) for nI in range(1,6)] \
             + ['bhhgob01'] \
             + ['bhhrec01', 'bhhrec02'] \
             + ['pbcresv01'] + ['pbcgob01', 'pbcgob02'] \
             + ['pbcrec0' + str(nI) for nI in range(1,6)] \
             + ['parresv01'] \
             + ['parrec01', 'parrec02'] \
             + ['xltla01', 'xltla02', 'xltla03', 'xltla06', 'xltla07']
# silverpoint includes also Core system machines (like wallboards etc.)
MsMachinesSP = ['tlacc'  + ('0' + str(nI))[-2:] for nI in range(1,10)] \
             + ['tladm'  + ('0' + str(nI))[-2:] for nI in range(1,3)] \
             + ['tlco'   + ('0' + str(nI))[-2:] for nI in range(1,2)] \
             + ['tlcomp' + ('0' + str(nI))[-2:] for nI in range(1,13)] \
             + ['tlcon'  + ('0' + str(nI))[-2:] for nI in range(1,7)] \
             + ['tlhr'   + ('0' + str(nI))[-2:] for nI in range(1,2)] \
             + ['tlmar'  + ('0' + str(nI))[-2:] for nI in range(1,13)] \
             + ['tlrec'  + ('0' + str(nI))[-2:] for nI in range(1,3)] \
             + ['tlres'  + ('0' + str(nI))[-2:] for nI in range(1,6)] \
             + ['tlresv' + ('0' + str(nI))[-2:] for nI in range(1,7)] \
             + ['tlsal'  + ('0' + str(nI))[-2:] for nI in range(1,8)] \
             + ['tltele' + ('00' + str(nI))[-3:] for nI in range(1,42)] \
             + ['tltele' + ('0' + str(nI))[-2:] for nI in range(2,4)] \
             + ['tltele' + ('0' + str(nI))[-2:] for nI in range(1,25)] \
             + ['TLTELE27', 'TLTELE30', 'TLTELE32', \
                'TLTELE39V', 'TLTELE53', 'TLTELEBOARD', 
                'TLTELETRAINING', 'TLTRA01', 'TLTRA02']
MsMachinesSP = [name + '.tensel.es' for name in MsMachinesSP]


"""
MsMachinesNewButStillNotFullyRenamed_askRuben = [] \
            + ['ACUITS69'] + ['ACUITS0' + str(nI) for nI in range(3,7)] \
            + ['BHCCTAB0' + str(nI) for nI in range(1,3)] \
            + ['BHCDIR0' + str(nI) for nI in range(1,3)] \
            + ['BHCGOB0' + str(nI) for nI in range(1,2)] \
            + ['BHCMAN01', 'BHCMANT02'] \
            + ['BHCREC0' + str(nI) for nI in range(1,5)] \
            + ['BHCRESV01'] \
            + ['BHHREC01', 'BHHREC02'] \
            + ['HMCCTAB0' + str(nI) for nI in range(1,3)] + ['HMCCTAB05'] \
            + ['HMCDIR02'] \
            + ['HMCGOB01', 'HMCGOB02'] \
            + ['HMCMAN01'] \
            + ['HMCREC0' + str(nI) for nI in range(1,7)] \
            + ['HMCRESV01'] \
            + ['PARDIR01'] \
            + ['PARGOB01'] \
            + ['PARREC01', 'PARREC02'] \
            + ['PARRESV01'] \
            + ['PBCCTAB01', 'PBCCTAB03', 'PBCCTAB04'] \
            + ['PBCDIR01', 'PBCDIR02', 'PBCDIR03'] \
            + ['PBCGOB01', 'PBCGOB02NEW'] \
            + ['PBCMAN01'] \
            + ['PBCREC0' + str(nI) for nI in [1,2,4,5,6]] \
            + ['PBCRESV01'] \
            + ['pbcsc01'] \
            + ['TLACC0' + str(nI) for nI in range(1,8)] \
            + ['TLCOM0' + str(nI) for nI in range(1,18)] \  -- GAPS: 4 8 13 14 16
            + ['TLCON0' + str(nI) for nI in range(1,8)] + ['TLCON11', 'TLCON50'] \
            + ['TLDC' + str(nI) for nI in range(0,3)] \
            + ['TLITS01'] \
            + ['TLMAR05', 'TLMAR08', 'TLMAR080', 'TLMAR13', 'TLMAR16', 'TLMAR73'] \
            + ['TLMS01', 'TLMS02'] \
            + ['TLREC02'] \
            + ['TLRES0' + str(nI) for nI in [1,3,4,6]] + ['TLRESCSC', 'TLRES001'] \
            + ['TLRESV01', 'TLRESV02', 'TLRESV10', 'TLRESV11', 'tlresv12'] \
            + ['TLSAL0' + str(nI) for nI in range(2,5)] + ['tlsal08', 'TLSAL10', 'TLSAL11', 'tlsal16', 'TLSAL18PB', 'TLSAL25MS', 'TLSALPBC08'] \
            + ['TLTELE03', 'TLTELE04', 'TLTELE05', 'TLTELE06', 'TLTELE07', 'TLTELE08', 'TLTELE09', 'TLTELE10', 'TLTELE11', 'TLTELE12', 'TLTELE13', 'TLTELE14', 'TLTELE15', 'TLTELE16', 'TLTELE17', 'TLTELE18', 'TLTELE19', 'TLTELE20', 'TLTELE21', 'TLTELE22', 'TLTELE24', 'TLTELE26', 'TLTELE27', 'TLTELE28', 'TLTELE29', 'TLTELE30', 'TLTELE31', 'TLTELE32', 'TLTELE33', 'TLTELE34', 'TLTELE35', 'TLTELE36', 'TLTELE37', 'TLTELE38', 'TLTELE39D', 'TLTELE39V', 'TLTELE41', 'TLTELE42', 'TLTELE43', 'TLTELE45', 'TLTELE46', 'TLTELE47', 'TLTELE48', 'TLTELE50', 'TLTELE51', 'TLTELE52', 'TLTELE53', 'TLTELE54', 'TLTELE55', 'TLTELE56', 'TLTELE59', 'TLTELE61', 'TLTELE62'] \
            + ['towallboardhmc'] \
            + ['TPV-BARPAR', 'TPV-BARPATIO', 'TPV-BEAUTYHMC', 'TPV-CASTLESP1', 'TPV-CASTLESP2', 'TPV-LOBBYBAR', 'TPV-RESTPLAZA', 'TPVSNACKBARII', 'TPV-SPORTBHC', 'TPV-SPORTCENHMC', 'TPV-SUPERBHCNEW', 'TPV-SUPERHMC', 'TPV-SUPERPBC'] \
            + ['XLCTAB05', 'XLCTAB06'] \
            + ['XLDIR0' + str(nI) for nI in range(1,4)] + ['XLDIR07', 'XLDIR08'] \
            + ['XLECO04', 'XLECO05'] \
            + ['XLFE02NEW'] \
            + ['XLITS02', 'XLITS05'] \
            + ['XLMAN02', 'XLMAR01'] \
            + ['XLMFE0' + str(nI) for nI in [1,2,3,5,6]] \
            + ['XLREC01'] \
            + ['XLRH02', 'XLRH03', 'XLRH1'] \
            + ['XLSQL01', 'XLSQL02', 'XLSQL04'] \
            + ['XLTLA06']
"""

MlsClientPaths = [
                 "ACUMENAPP/OS51/Acumen/",
                 "ACUMENAPP/OS51 RT/Acumen/",
                 "ACUMENAPP/OS51 RT2/Acumen/",
                 "Archivos de programa/TigerLogic/OS51/Acumen/",
                 "Archivos de programa/TigerLogic/OS51 RT/Acumen/",
                 "Archivos de programa/TigerLogic/OS51 RT2/Acumen/",
                 "Program Files/Tigerlogic/OS51/Acumen/",
                 "Program Files/Tigerlogic/OS51 RT/Acumen/",
                 "Program Files/TigerLogic/OS51 RT2/Acumen/"
                 ]



# helper class for to pass parameters into a widget event proc
class Command:
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return apply(self.callback, self.args, self.kwargs)


class DistWin:
    # construct method
    def __init__(self, root):
        self.RootWin = root
        self.sBreakMode = ''        # used for breakable dist. check
        
        ### Widget Initialization
        self._tabNoteBook = Tix.NoteBook(root, name='nb', ipadx=6, ipady=6) # was Pmw.NoteBook(root)
        self._cmdClose = Tkinter.Button(root,
                                         text = 'Close',
                                         command = self._cmdClose_command)
        root.bind("<Escape>", self._cmdClose_command)
        self._txtStatus = Tkinter.Text(root, height = '0', width = '0', wrap = 'none')

        # Geometry Management for root page
        self._tabNoteBook.grid(in_ = root, columnspan = '3', sticky = 'news')
        self._txtStatus.grid(in_ = root, row = 1, columnspan = '3', sticky = 'news')
        self._cmdClose.grid(in_ = root, row = 2, column = 2, sticky = 'we')

        root.grid_rowconfigure(0, weight = 2, minsize = 300)   # Notebook
        root.grid_rowconfigure(1, weight = 1, minsize = 120)   # txtStatus
        root.grid_rowconfigure(2, weight = 0, minsize = 20, pad = 9)    # cmdClose
        root.grid_columnconfigure(0, weight = 1)
        root.grid_columnconfigure(1, weight = 1)
        root.grid_columnconfigure(2, weight = 1)

        ## first page for distributing
        self._pageDist = self._tabNoteBook.add('_pageDist', label='O$ Distribute', underline=0)
        #self._tabNoteBook.tab('O$ Distribute').focus_set()
        
        self._lblDistTitle = Tkinter.Label(self._pageDist,
            text = "Please only select/check the libraries you really want to distribute\n" \
                 + "and don't forget to choose the right distribution destination. Recent\n" \
                 + "builded libaries are automatically selected/checked.\n\n" \
                 + "For unbuild distributions (from your local OS51 folder, not from your Buildfolder) you have\n"
                 + "to close your main Omnis application and uncheck the Distribute Build checkbox.\n\n"
                 + "Click on the 'Distribute' button to copy the libraries and the default\n"
                 + "TNS name to the selected distribution destination.\n\n",
            justify = 'left')
        
        self._lblDistDest = Tkinter.Label(self._pageDist, text = "Destination", justify = 'left')

        self.rbDistDest = IntVar()
        self.rbDistDest.set(MnUATDestCount-1)   # default to last UAT slot/base
        for nI in range(MnUATDestCount):
            cCh = unichr(DEST_UAT_A_CHR_ORD + nI)
            setattr( self, '_rbDistUAT_' + cCh,
                     Tkinter.Radiobutton(self._pageDist, text = "Test Base/Slot " + cCh, variable = self.rbDistDest,
                                                   value = nI, command = self._setupLibs) )
        self._rbDistLIVE = Tkinter.Radiobutton(self._pageDist, text = "LIVE DISTRIBUTION", variable = self.rbDistDest,
                                               value = MnLiveDestID, command = self._setupLibs)

        self.cboDefTNS = StringVar()
        self._cboDefTNS = Tix.ComboBox(self._pageDist, variable = self.cboDefTNS,
                                        label = "Def. TNS Name", selectmode = 'immediate')

        self.chkUseBuild = IntVar()
        self.chkUseBuild.set(1)
        self._chkUseBuild = Tkinter.Checkbutton(self._pageDist, text = "Distribute Build",
                                                variable = self.chkUseBuild,
                                                command = self._setupLibs) # use same callback for reInit.
        self.cboSrcLibPaths = StringVar()
        self.cboSrcLibPaths.set(MlsSrcLibPaths[0])
        self._cboSrcLibPaths = Tix.ComboBox(self._pageDist, variable = self.cboSrcLibPaths,
                                            command = self._setupLibs, label = "Source Path", #listwidth = 300,
                                            selectmode = 'immediate')
        nI = 0
        for srcPath in MlsSrcLibPaths:
            self._cboSrcLibPaths.insert(nI, srcPath)
            nI += 1

        self._cmdUATReset = Tkinter.Button(self._pageDist, text = "Reset To Live Libraries", command = self._cmdUATReset_command)
        self._cmdDist = Tkinter.Button(self._pageDist, text = 'Distribute', command = self._cmdDist_command)

        # Geometry and Resize Management for Dist notebook page
        nRow = 0
        self._lblDistTitle.grid(in_ = self._pageDist, columnspan = 3, sticky = 'wn')
        self._pageDist.grid_rowconfigure(nRow, weight = 0)
        nRow = nRow + 1
        self._lblDistDest.grid(in_ = self._pageDist, column = 0, row = nRow, sticky = 'w')
        for nI in range(MnUATDestCount):
            cCh = unichr(DEST_UAT_A_CHR_ORD + nI)
            colI = (nI % 2) + 1
            getattr(self, '_rbDistUAT_' + cCh).grid(in_ = self._pageDist, column = colI, row = nRow, sticky = 'w')
            if colI == 2:
                self._pageDist.grid_rowconfigure(nRow, weight = 0)
                nRow = nRow + 1
        self._rbDistLIVE.grid(in_ = self._pageDist, column = 2, row = nRow, sticky = 'w')
        self._pageDist.grid_rowconfigure(nRow, weight = 0)
        
        nRow = nRow + 1
        self._cboDefTNS.grid(in_ = self._pageDist, column = 2, row = nRow, sticky = 'w')
        self._pageDist.grid_rowconfigure(nRow, weight = 0, pad = 33)
        nRow = nRow + 1
        self._chkUseBuild.grid(in_ = self._pageDist, column = 0, row = nRow, sticky = 'w')
        self._cboSrcLibPaths.grid(in_ = self._pageDist, column = 1, columnspan = 2, row = nRow, sticky = 'ew')
        self._pageDist.grid_rowconfigure(nRow, weight = 0, pad = 44)
        nRow = nRow + 1
        self.chkLibGridFirstRow = nRow
        # here are placed the lib check box - (re)generated by _setupLibs()
        nRow = nRow + CHKLIB_MAXROWS
        self._pageDist.grid_rowconfigure(nRow, weight = 0, minsize = 33)  # vertical spacer
        nRow = nRow + 1
        self._cmdUATReset.grid(in_ = self._pageDist, column = 0, row = nRow, sticky = 'we')
        self._cmdDist.grid(in_ = self._pageDist, column = 2, row = nRow, sticky = 'we')
        self._pageDist.grid_rowconfigure(nRow, weight = 0, pad = 69)

        self._pageDist.grid_columnconfigure(0, weight = 1)
        self._pageDist.grid_columnconfigure(1, weight = 1)
        self._pageDist.grid_columnconfigure(2, weight = 1)

        ## second tab page: Checking distribution
        CHECK_HINTS = "Checking needs some seconds (until the timeout) for every machine switched\n" \
                    + "off or never accessed before from your machine with Windows Explorer. You can\n" \
                    + "cancel the checking by clicking on the 'Check' button again (labeled 'Cancel'\n" \
                    + "while the checking is running)."

        self._pageCheck = self._tabNoteBook.add('_pageCheck', label='Check O$', underline=0)
        self._lblCheckTitle = Tkinter.Label(self._pageCheck,
            text = "The 'Check' button is for to check the MasterLibs consistences and the yet\n" \
                 + "distributed libraries on all the client machines (XL, SP or a single computer).\n\n" \
                 + CHECK_HINTS,
            justify = 'left')

        self.chkCheckXL = IntVar()
        self._chkCheckXL = Tkinter.Checkbutton(self._pageCheck,
                                               text = 'Check all XL machines',
                                               justify = 'left',
                                               variable = self.chkCheckXL)
        self.chkCheckSP = IntVar()
        self._chkCheckSP = Tkinter.Checkbutton(self._pageCheck,
                                               text = 'Check all SP machines',
                                               justify = 'left',
                                               variable = self.chkCheckSP)
        self.chkCheckInp = IntVar()
        self._chkCheckInp = Tkinter.Checkbutton(self._pageCheck,
                                               text = 'Check inputted machine',
                                               justify = 'left',
                                               variable = self.chkCheckInp)
        self.txtMachine = StringVar()
        self._txtMachine = Tkinter.Entry(self._pageCheck,
                                         textvariable = self.txtMachine,
                                         validate = 'focusout',
                                         validatecommand = self._txtMachine_command)
        self._cmdCheck = Tkinter.Button(self._pageCheck,
                                        text = 'Check',
                                        command = self._cmdCheck_command)

        # Geometry Management and Resize Behavior for Check notebook page
        self._lblCheckTitle.grid(in_ = self._pageCheck, column = 1, row = 1,
                                 columnspan = '3', rowspan = '1', sticky = 'wn')
        self._pageCheck.grid_rowconfigure(1, weight = 1, minsize = 120, pad = 0)
        self._chkCheckXL.grid(in_ = self._pageCheck, column = 1, row = 2)
        self._chkCheckSP.grid(in_ = self._pageCheck, column = 2, row = 2)
        self._chkCheckInp.grid(in_ = self._pageCheck, column = 3, row = 2)
        self._pageCheck.grid_rowconfigure(2, weight = 1, minsize = 40, pad = 0)
        self._txtMachine.grid(in_ = self._pageCheck, column = 3, row = 3)
        self._pageCheck.grid_rowconfigure(3, weight = 1, minsize = 20, pad = 0)
        self._cmdCheck.grid(in_ = self._pageCheck, column = 3, row = 4,
                            columnspan = '1', padx = '3', rowspan = '1', sticky = 'ew')
        self._pageCheck.grid_rowconfigure(4, weight = 1, minsize = 120, pad = 0)

        self._pageCheck.grid_columnconfigure(1, weight = 1, minsize = 50, pad = 0)
        self._pageCheck.grid_columnconfigure(2, weight = 1, minsize = 50, pad = 0)
        self._pageCheck.grid_columnconfigure(3, weight = 1, minsize = 50, pad = 0)

        ## third tab page: Checking distribution folders
        self._pageFCheck = self._tabNoteBook.add('_pageFCheck', label='File Check', underline=0)
        self._lblFCTitle = Tkinter.Label(self._pageFCheck,
            text = "The 'Check' button is for to compare the given File Path on the inputted\n" \
                 + "machines against the given reference machine.\n" \
                 + "If the File Path value not starts with the machines root (/ or \), then\n" \
                 + "the share c$ is used for default. If it ends in a / or \ char, then all files\n" \
                 + "in the path are compared. Wildcards * and ? can be used also.\n\n" \
                 + CHECK_HINTS,
            justify = 'left')

        self._lblFCMachine = Tkinter.Label(self._pageFCheck,
                                           text = "Reference machine")
        self.txtFCMachine = StringVar()
        self._txtFCMachine = Tkinter.Entry(self._pageFCheck,
                                           textvariable = self.txtFCMachine)
        
        self._lblFCFile = Tkinter.Label(self._pageFCheck,
                                        text = "File path")
        self.txtFCFile = StringVar()
        self._txtFCFile = Tkinter.Entry(self._pageFCheck,
                                        textvariable = self.txtFCFile)
        
        self._lblFCMachines = Tkinter.Label(self._pageFCheck,
                                            text = "Machines to check")
        self.txtFCMachines = StringVar()
        self._txtFCMachines = Tkinter.Entry(self._pageFCheck,
                                            textvariable = self.txtFCMachines)
        self._cmdFCheck = Tkinter.Button(self._pageFCheck,
                                         text = 'Check',
                                         command = self._cmdFCheck_command)

        # Geometry Management and Resize Behavior for FCheck notebook page
        self._lblFCTitle.grid(in_ = self._pageFCheck, column = 1, row = 1,
                              columnspan = '3', rowspan = '1', sticky = 'wn')
        self._pageFCheck.grid_rowconfigure(1, weight = 1, minsize = 150, pad = 0)
        self._lblFCMachine.grid(in_ = self._pageFCheck, column = 1, row = 2,
                                sticky = 'e')
        self._txtFCMachine.grid(in_ = self._pageFCheck, column = 2, row = 2,
                                sticky = 'w')
        self._pageFCheck.grid_rowconfigure(2, weight = 1, minsize = 20, pad = 0)
        self._lblFCFile.grid(in_ = self._pageFCheck, column = 1, row = 3,
                             sticky = 'e')
        self._txtFCFile.grid(in_ = self._pageFCheck, column = 2, row = 3,
                             columnspan = '2', sticky = 'ew')
        self._pageFCheck.grid_rowconfigure(3, weight = 1, minsize = 20, pad = 0)
        self._lblFCMachines.grid(in_ = self._pageFCheck, column = 1, row = 4,
                                 sticky = 'e')
        self._txtFCMachines.grid(in_ = self._pageFCheck, column = 2, row = 4,
                                 columnspan = '2', sticky = 'ew')
        self._pageFCheck.grid_rowconfigure(4, weight = 1, minsize = 20, pad = 0)
        self._cmdFCheck.grid(in_ = self._pageFCheck, column = 3, row = 5,
                             columnspan = '1', padx = '3', rowspan = '1', sticky = 'ew')
        self._pageFCheck.grid_rowconfigure(5, weight = 1, minsize = 40, pad = 0)

        self._pageFCheck.grid_columnconfigure(1, weight = 0, minsize = 20, pad = 0)
        self._pageFCheck.grid_columnconfigure(2, weight = 1, minsize = 50, pad = 0)
        self._pageFCheck.grid_columnconfigure(3, weight = 2, minsize = 50, pad = 0)

        # set widget values - loaded from configuration settings
        self.txtFCMachine.set(ConfigString('FCMachine'))
        self.txtFCMachines.set(ConfigString('FCMachines'))
        self.txtFCFile.set(ConfigString('FCFile'))
        if ConfigBool('ChkCheckXL'):
            self._chkCheckXL.select()
        if ConfigBool('ChkCheckSP'):
            self._chkCheckSP.select()
        if ConfigBool('ChkCheckInp'):
            self._chkCheckInp.select()
        self.txtMachine.set(ConfigString('TxtCheckInp'))
        root.geometry(ConfigString('Geometry'))
        
        self._setupLibs()  # create and init. lib check boxes, configure logging

        # add an event handler for to save the current user settings
        # .. __del__(self) not works for RootWin.geometry() because the wm
        # .. is yet destroyed, when __del__ is called
        root.bind("<Destroy>", self._destroy)
        
    def _destroy(self, *args):
        ConfigSavePrepare()
        MoConfig.set(MsUserSection, 'FCMachine', self.txtFCMachine.get())
        MoConfig.set(MsUserSection, 'FCMachines', self.txtFCMachines.get())
        MoConfig.set(MsUserSection, 'FCFile', self.txtFCFile.get())
        MoConfig.set(MsUserSection, 'ChkCheckXL', self.chkCheckXL.get())
        MoConfig.set(MsUserSection, 'ChkCheckSP', self.chkCheckSP.get())
        MoConfig.set(MsUserSection, 'ChkCheckInp', self.chkCheckInp.get())
        MoConfig.set(MsUserSection, 'TxtCheckInp', self.txtMachine.get())
        MoConfig.set(MsUserSection, 'Geometry', self.RootWin.geometry())
        ConfigSaveComplete()
        
        
    ###################################################
    ##############  widget callbacks  #################
    ###################################################

    # (re)create lib check boxes and populate cboDefTNS with current LAUNCHER.INI values
    def _setupLibs(self, *args):
        useBuild = self.chkUseBuild.get()
        srcLibIndex = ListIndex(MlsSrcLibPaths, self.cboSrcLibPaths.get())
        distDest = self.rbDistDest.get()
        # process GUI intelligence
        if not useBuild and distDest == MnLiveDestID:
            self.rbDistDest.set(MnUATDestCount-1)   # default to last UAT slot/base, don't distribute allow dev/O$
            distDest = self.rbDistDest.get()
            self.StatusPrint("Distribution to LIVE is only allowed from the build.", logging.WARN)
        if useBuild and srcLibIndex <> 0:
            self.StatusPrint("Built libs get always distributed from your build folder. Changed Source Path accordingly.", logging.WARN)
            self._cboSrcLibPaths.pick(0)
            srcLibIndex = ListIndex(MlsSrcLibPaths, self.cboSrcLibPaths.get())
        elif not useBuild and srcLibIndex == 0:
            self.StatusPrint("Developer libs get always distributed from one of your Acumen folders. Changed to 1st Omnis installation.", logging.WARN)
            self._cboSrcLibPaths.pick(1)
            srcLibIndex = ListIndex(MlsSrcLibPaths, self.cboSrcLibPaths.get())

        DistInitPaths(srcLibIndex, distDest)    # init path variables (needed by DistLibVersions)

        # now 1st remove and then recreate lib check boxes from last refresh
        nI = 1
        while getattr(self, 'chkLib' + str(nI), None):
            delattr(self, 'chkLib' + str(nI))
            getattr(self, '_chkLib' + str(nI)).destroy()
            delattr(self, '_chkLib' + str(nI))
            nI = nI + 1
        lLibs = DistLibVersions(self, True)   # include also new locally build libs
        if distDest != MnLiveDestID:       # prepare to determine next UAT build version
            nLibVer = float(NEW_LIB_VERSION_UAT)
        nI = 1
        for sLibVerFile in lLibs:
            setattr(self, 'chkLib' + str(nI), IntVar())
            fConf = Tkinter.Checkbutton(self._pageDist, justify = 'left',
                                    text = sLibVerFile.upper(), takefocus = '0',
                                    variable = getattr(self, 'chkLib' + str(nI)),
                                    command = Command(self._chkLib_command, sLibVerFile, nI))
            setattr(self, '_chkLib' + str(nI), fConf)
            nR = int((nI-1) / 3) + self.chkLibGridFirstRow
            fConf.grid(in_ = self._pageDist, column = ((nI-1) % 3), row = nR, sticky = 'w', padx = 10)
            self._pageDist.grid_rowconfigure(nR, weight = 0)
            # new libs checkboxes keep unselected and enabled
            if not SrcLibIsNew(sLibVerFile):
                if useBuild:
                    if os.path.isfile(SrcLibPath(sLibVerFile, self)):
                        dtLibSrc = SrcLibDate(sLibVerFile, self)
                        if dtLibSrc == DistLibDate(sLibVerFile):
                            fConf.configure(foreground = 'red3')
                        elif TODAY_DATETIME - dtLibSrc < timedelta(hours=1):
                            fConf.select()
                    else:
                        fConf.configure(state = 'disabled')
                if distDest != MnLiveDestID:
                    sLibVerName = os.path.splitext(sLibVerFile)[0]
                    nLV = float(sLibVerName[len(SrcLibName(sLibVerName)):])
                    if nLibVer < nLV:
                        nLibVer = nLV
            nI = nI + 1

        # get current default TNS name (LAUNCHER.INI/SERVICE_NAME)
        self._cboDefTNS.subwidget('listbox').delete(0, END) # delete all items in the listbox subwidget
        sCurrentTNS, lAllTNS = TNSInfo(MlsDistPaths[0] + 'LAUNCHER.INI')
        nI = 0
        for sTNS in lAllTNS:
            self._cboDefTNS.insert(nI, sTNS)
            nI += 1
        self._cboDefTNS.pick(ListIndex(lAllTNS,sCurrentTNS))    # does self.cboDefTNS.set(sCurrentTNS)

        # behaviour settings
        if distDest == MnLiveDestID:
            self._cboDefTNS.configure(state = 'disabled')
            self._chkUseBuild.configure(state = 'disabled')
            self._cmdUATReset.configure(state = 'disabled')
        else:
            self._cboDefTNS.configure(state = 'normal')
            self._chkUseBuild.configure(state = 'normal')
            self._cmdUATReset.configure(state = 'normal')
            self.sLibVerUAT = (str(nLibVer + 0.1) + "0")[:3]
        if useBuild:
            self._rbDistLIVE.configure(state = 'normal')
            self._cboSrcLibPaths.configure(state = 'disabled')
        else:
            self._rbDistLIVE.configure(state = 'disabled')
            self._cboSrcLibPaths.configure(state = 'normal')
        # all these is not showing 
        #self._pageDist.update()
        #self._rbDistLIVE.update_idletasks()     # don't -"-, so maybe a little faster


    # Callback to handle all _chkLib* widgets
    def _chkLib_command(self, sLib, nI):
        # check if lib was yet distributed
        if getattr(self, 'chkLib' + str(nI)).get():
            if not SrcLibIsNew(sLib) \
            and SrcLibDate(sLib, self) == DistLibDate(sLib):   # lazy AND
                self.StatusPrint("Library " + sLib + " was already distributed.", logging.ERROR)


    def _txtMachine_command(self, *args):
        # not used because sVal has not the current value
        #sVal = self.txtMachine.get()
        #if sVal == '':
        #    sState = 'normal'
        #else:
        #    sState = 'disabled'
        #self._cmdCheck.configure(state = sState)
        #self._chkCheckSP.configure(state = sState)
        return 1

    def _cmdClose_command(self, *args):
        self.RootWin.destroy()

    def _cmdCheck_command(self, *args):
        self.Wait(True, True)
        if self.sBreakMode == 'CANCELED':
            return          # user pressed Cancel (its the same button)
        
        nErrors = CheckServerLibs(self) + CheckClientLibs(self)
        if self.sBreakMode == 'CANCELED':
            self.StatusPrint("Distribution check canceled by user. Found " + str(nErrors) + " warnings and errors!", logging.ERROR)
        elif nErrors == 0:
            self.StatusPrint("Distribution check completed without errors!")
        else:
            self.StatusPrint("Distribution check found " + str(nErrors) + " warnings and errors!", logging.ERROR)
        self.Wait(False, True)

    def _cmdFCheck_command(self, *args):
        self.Wait(True, True)
        if self.sBreakMode == 'CANCELED':
            return          # user pressed Cancel (its the same button)
        nErrors = CheckFiles(self)
        if self.sBreakMode == 'CANCELED':
            self.StatusPrint("File check canceled by user. Found " + str(nErrors) + " warnings and errors!", logging.ERROR)
        elif nErrors == 0:
            self.StatusPrint("File check completed without errors!")
        else:
            self.StatusPrint("File check found " + str(nErrors) + " warnings and errors!", logging.ERROR)
        self.Wait(False, True)

    # Callback to handle _cmdDist widget option -command
    def _cmdDist_command(self, *args):
        #self._cmdDist.configure(relief='sunken')      # not works (for <Return> event)
        #self._cmdDist.update_idletasks()              # even not with this (found in INET::button_invoker())
        self.Wait(True)
        # distribute libs
        lLibs = DistLibVersions(self, True)   # include also new locally build libs
        nI = 1
        nLibs = 0
        ok = True
        for sLibVerFile in lLibs:
            if getattr(self, 'chkLib' + str(nI)).get():
                self.StatusPrint("Distributing " + SrcLibPath(sLibVerFile, self) + " to " + str(MlsDistPaths))
                ok = DistLibrary(sLibVerFile, self)
                if not ok:
                    break
                getattr(self, '_chkLib' + str(nI)).configure(state = 'disabled')
                nLibs = nLibs + 1
            nI = nI + 1
        if ok:
            self.StatusPrint("Finished the distribution of " + str(nLibs) + " libraries.")
        cDefTNSName = self.cboDefTNS.get()
        if cDefTNSName:
            ok = DistTNSDefName(cDefTNSName, self.rbDistDest.get())
            if ok:
                self.StatusPrint("Finished the distribution of the default TNS name " + cDefTNSName + " to " + MlsDistPaths[0] + ".")
            
        #self._cmdDist.configure(relief='raised')     # NOT WORKS (see up)
        self.Wait(False)

    def _cmdUATReset_command(self, *args):
        self.Wait(True)
        self.StatusPrint("Replacing all libraries in base " + MlsDistPaths[0] + " with LIVE libaries")
        try:
            # not works (neither with * at the end) - to keep user rights for folder better to only replace libs
            #shutil.rmtree(MlsDistPaths[0][:-1])
            #shutil.copytree(MlsLiveDistPaths[0][:-1], MlsDistPaths[0][:-1])
            # the next version was only copying in the 2nd level and only libraries, missing launcher, TXT, STB and CORE subdires
            #for sFile in glob.glob(MlsDistPaths[0] + "*/*" + EXT_LBS):
            #    self.StatusPrint("Removing " + sFile, logging.INFO)
            #    os.remove(sFile)
            #for sFile in glob.glob(MlsLiveDistPaths[0] + "*/*" + EXT_LBS):
            #    sLibName = SrcLibName(os.path.basename(sFile)).upper()
            #    sDestPath = MlsDistPaths[0] + sLibName
            #    if not os.path.exists(sDestPath):
            #        self.StatusPrint("Creating folder " + sDestPath, logging.INFO)
            #        os.mkdir(sDestPath)
            #    self.StatusPrint("Copying " + sFile, logging.INFO)
            #    shutil.copy2(sFile, sDestPath + "/" + sLibName + " " + NEW_LIB_VERSION_UAT + EXT_LBS)
            # finally we make now an exact copy of the 1st MasterLibs folder (w/o removing UAT_LibsX)
            for path, dirs, files in os.walk(MlsDistPaths[0], topdown=False):
                for sFile in files:
                    self.StatusPrint("Removing file " + os.path.join(path, sFile), logging.DEBUG)
                    os.remove(os.path.join(path, sFile))
                for name in dirs:
                    self.StatusPrint("Removing folder " + os.path.join(path, name), logging.DEBUG)
                    os.rmdir(os.path.join(path, name))
            for srcPath, dirs, files in os.walk(MlsLiveDistPaths[0]):
                if srcPath.find(FOLDER_IGNORE_ON_COPY) == -1:     ## exclude files/folders underneath DfsrPrivate
                    dstPath = MlsDistPaths[0] + srcPath[len(MlsLiveDistPaths[0]):]
                    for name in dirs:
                        if name <> FOLDER_IGNORE_ON_COPY:  ## exclude DfsrPrivate root folder to be created
                            self.StatusPrint("Creating folder " + os.path.join(dstPath, name))
                            os.mkdir(os.path.join(dstPath, name))
                    for sFile in files:
                        if sFile[-len(EXT_LBS):].upper() == EXT_LBS.upper() \
                        and sFile.upper() <> 'LAUNCHER.LBS':
                            sLibName = SrcLibName(sFile)
                            self.StatusPrint("Copying file " + os.path.join(srcPath, sFile) + " into " + os.path.join(dstPath, sLibName + " " + NEW_LIB_VERSION_UAT + EXT_LBS))
                            shutil.copy2(os.path.join(srcPath, sFile), os.path.join(dstPath, sLibName + " " + NEW_LIB_VERSION_UAT + EXT_LBS))
                        else:
                            self.StatusPrint("Copying file " + os.path.join(srcPath, sFile) + " to " + dstPath)
                            shutil.copy2(os.path.join(srcPath, sFile), os.path.join(dstPath, sFile))
        except:
            self.StatusPrint("Error occured on resetting the UAT base to the current live libraries: " + str(sys.exc_info()), logging.CRITICAL)
        else:
            self.StatusPrint("Finished resetting all libraries to live.")
        self._setupLibs()
        self.Wait(False)
            
            
    def StatusPrint(self, sText, nMsgLevel = logging.INFO):
        #if nMsgLevel >= logging.WARN or IS_DEBUG:  # if not needed - done with loglevel configuration
        # write it to the log file too
        MoLogger.log(nMsgLevel, "%-9s %-13s %s" % (win32api.GetUserName(), win32api.GetComputerName(), sText))
    
        if nMsgLevel >= logging.INFO or IS_DEBUG:
            if nMsgLevel == logging.WARN:
                sText = '## ' + sText
            elif nMsgLevel == logging.ERROR:
                sText = '!! ' + sText
            if sText[-1:] != '.':
                sText = sText + '.'
            self._txtStatus.insert(index = 'end', chars = sText + '\n')
            self._txtStatus.see(index = 'end')
            #not works for redrawing/refreshing: tkinter.Tcl_DoOneEvent(tkinter.ALL_EVENTS + tkinter.DONT_WAIT)
            #self.RootWin.update()              # processes also user inputs
            self.RootWin.update_idletasks()     # don't -"-, so maybe a little faster
            
    def Wait(self, bWait = True, bBreakable = False):
        if bWait and bBreakable and self.sBreakMode == 'BREAKABLE':
            self.sBreakMode = 'CANCELED'    # user pressed Cancel
            return                          # exit second callback

        if bWait:
            sState = 'disabled'
            sText = 'Cancel'
            if bBreakable:
                self.sBreakMode = 'BREAKABLE'
        else:
            sState = 'normal'
            sText = 'Check'
            if bBreakable:
                self.sBreakMode = ''
        self._cmdDist.configure(state = sState)
        self._cmdClose.configure(state = sState)
        self._chkCheckXL.configure(state = sState)
        self._chkCheckSP.configure(state = sState)
        self._chkCheckInp.configure(state = sState)
        self._txtMachine.configure(state = sState)
        self._cboDefTNS.configure(state = sState)
        self._chkUseBuild.configure(state = sState)
        self._cboSrcLibPaths.configure(state = sState)
        for nI in range(MnUATDestCount):
            cCh = unichr(DEST_UAT_A_CHR_ORD + nI)
            getattr(self, '_rbDistUAT_' + cCh).configure(state = sState)
        self._rbDistLIVE.configure(state = sState)
        self._cmdUATReset.configure(state = sState)
        if bBreakable:
            self._cmdCheck.configure(text = sText)
            self._cmdFCheck.configure(text = sText)
        else:
            self._cmdCheck.configure(state = sState)
            self._cmdFCheck.configure(state = sState)




### Distributor Helping Methods ###

def DistLibrary(sLibVerFile, wDist):
    useBuild = wDist.chkUseBuild.get()
    distDest = wDist.rbDistDest.get()
    sLibName = SrcLibName(sLibVerFile)
    bLibNew = SrcLibIsNew(sLibVerFile)
    if not bLibNew:
        sLibVerName = os.path.splitext(sLibVerFile)[0]
    elif distDest == MnLiveDestID:
        sLibVerName = sLibName + " " + NEW_LIB_VERSION_LIVE
    else:
        sLibVerName = sLibName + " " + NEW_LIB_VERSION_UAT
    sLibFile = sLibName + EXT_LBS
    sStbFile = sLibName + EXT_STB
    sLibSrcFilePath = SrcLibPath(sLibVerFile, wDist)
    sStbSrcFilePath = os.path.dirname(sLibSrcFilePath) + "/" + sStbFile
    bHasStb = os.path.isfile(sStbSrcFilePath)

    if distDest == MnLiveDestID and not bLibNew and os.path.isfile(MsBuildPath + sLibFile):
        # backup the lib and string table (from the last build) if already exists
        if os.path.isfile(MsZipPath + sLibName + EXT_ZIP):
            sZipMode = "a"
        else:
            sZipMode = "w"
        zfile = zipfile.ZipFile(MsZipPath + sLibName + EXT_ZIP, sZipMode)
        zfile.write(MsBuildPath + sLibFile, sLibVerFile, zipfile.ZIP_DEFLATED)
        if bHasStb:
            zfile.write(MsBuildPath + sStbFile, sLibVerName + EXT_STB, zipfile.ZIP_DEFLATED)
        zfile.close()
    
    # copy new lib/stb in the global/public build path (overwriting the old/just_zipped ones)
    try:
        shutil.copy2(sLibSrcFilePath, MsBuildPath + sLibFile)
        if bHasStb:
            shutil.copy2(sStbSrcFilePath, MsBuildPath + sStbFile)
    except:
        wDist.StatusPrint("File " + sLibSrcFilePath + " is locked. Please close your Omnis and try again: " + str(sys.exc_info()), logging.CRITICAL)
        return False

    if distDest == MnLiveDestID:
        nLibVerLen = len(sLibVerName) - len(sLibName) - 1
        sLibVer = (str(float(sLibVerName[len(sLibName):]) + 0.01) + "00")[:nLibVerLen] # increment lib version number
    else:
        sLibVer = wDist.sLibVerUAT
    sLibNewVerFile = sLibName + " " + sLibVer + EXT_LBS

    # distribute the new builded lib and delete the old ones, also copy STB
    for path in MlsDistPaths:
        if bLibNew and not os.path.exists(path + sLibName.upper()):
            os.mkdir(path + sLibName.upper())
        shutil.copy2(MsBuildPath + sLibFile, path + sLibName + "/" + sLibNewVerFile)
        if not bLibNew:
            os.remove(path + sLibName + "/" + sLibVerFile)
        # distribute the new builded stb (overwriting the existing)
        if bHasStb:
            shutil.copy2(MsBuildPath + sStbFile, path + sLibName)
        

    # rename the dev library or delete the local build library and string table
    if not useBuild:
        os.rename(sLibSrcFilePath, os.path.dirname(sLibSrcFilePath) + "/" + sLibNewVerFile)
    elif not IS_DEBUG:
        os.remove(sLibSrcFilePath)
        if bHasStb:
            os.remove(sStbSrcFilePath)
    return True


def DistTNSDefName(cDefTNSName, sDistDest):
    # updated LAUNCHER.ini/SERVICE_NAME with given TNS name
    # get current default TNS name (LAUNCHER.INI/SERVICE_NAME)
    # ..(cannot use ConfigParser - needs section header)
    sIniFilePath = MlsDistPaths[0] + 'LAUNCHER.INI'
    if os.path.isfile(sIniFilePath):
        fIni = file(sIniFilePath, 'r')
        lIniContents = fIni.readlines()
        fIni.close()
    if lIniContents:
        sIniContent = lIniContents[0]    # SERVICE_NAME always on 1st line
        nPos1 = sIniContent.find('=') + 1
        sIniContent = sIniContent[:nPos1] + cDefTNSName+ '\n'
        lIniContents[0] = sIniContent
    else:
        sIniContent = 'SERVICE_NAME=' + cDefTNSName + '\n'
        lIniContents = [sIniContent, 'TNS_NAMES=AR.WORLD,RP.WORLD,SP.WORLD,XL.WORLD,AR.TEST,RP.TEST,SP.TEST,SP.TEST2,RP.DEV']
        
    fIni = file(sIniFilePath, 'w')
    fIni.writelines(lIniContents)
    fIni.close()
    return True


def DistLibVersions(wDist, bIncludeNewLibs = False):
    lDistLibs = [os.path.basename(sLib)
                 for sLib in glob.glob(MlsDistPaths[0] + "*/*" + EXT_LBS)]
    if bIncludeNewLibs:
        if wDist.chkUseBuild.get():
            sSearch = "*"        # search for new builded libs already not distributed
        else:
            sSearch = "*/*"      # search for not distributed dev libs
        lLibsNewBuilded = [NEW_LIB_PREFIX + os.path.basename(sLib)
                           for sLib in glob.glob(MsLibSrcPath + sSearch + EXT_LBS)
                           if DistLibFile(lDistLibs, os.path.splitext(os.path.basename(sLib))[0]) == '']
    else:
        lLibsNewBuilded = []
    return lDistLibs + lLibsNewBuilded

def DistLibFile(lDistLibs, sLibSrcFile):
    sLibSrcFile = SrcLibName(sLibSrcFile)
    for sLib in lDistLibs:
        if SrcLibName(sLib).upper() == sLibSrcFile.upper():
            return sLib
    return ''
    
def DistLibDate(sLibVerFile):
    libstat = os.stat(DistLibPath(sLibVerFile))
    return datetime.datetime.fromtimestamp(libstat[ST_MTIME])

def DistLibPath(sLibVerFile):
    sLibName = SrcLibName(sLibVerFile)
    return MlsDistPaths[0] + sLibName + "/" + sLibVerFile

def SrcLibDate(sLibVerFile, wDist):
    libstat = os.stat(SrcLibPath(sLibVerFile, wDist))
    return datetime.datetime.fromtimestamp(libstat[ST_MTIME])

def SrcLibName(sLibVerFile):
    sLibName = os.path.basename(sLibVerFile)
    if SrcLibIsNew(sLibName): #sLibVerFile):
        sLibName = sLibName[len(NEW_LIB_PREFIX):]
    nPos = sLibName.find(' ')
    if nPos != -1:
        sLibName = sLibName[:nPos]
    else:
        sLibName = os.path.splitext(sLibName)[0]
    return sLibName

def SrcLibIsNew(sLibVerFile):
    sLibName = os.path.basename(sLibVerFile)
    return sLibName[:len(NEW_LIB_PREFIX)] == NEW_LIB_PREFIX

def SrcLibPath(sLibVerFile, wDist):
    if wDist.chkUseBuild.get():
      return MsLibSrcPath + SrcLibName(sLibVerFile) + EXT_LBS
    fileList = glob.glob(MsLibSrcPath + SrcLibName(sLibVerFile) + "/*" + EXT_LBS)
    if len(fileList) == 1:
      return fileList[0]
    else:
      wDist.StatusPrint(MsLibSrcPath + SrcLibName(sLibVerFile) + "/*" + EXT_LBS + " either contains none or more than one library", logging.ERROR)
      return ''

def CheckClientLibs(wDist):
    sMachines = ['_SP_']
    if wDist.chkCheckXL.get():
        sMachines = MsMachinesXL + sMachines
    if wDist.chkCheckSP.get():
        sMachines = sMachines + MsMachinesSP
    if wDist.chkCheckInp.get():
        if (wDist.txtMachine.get().lower() in MsMachinesXL):
            sMachines = [wDist.txtMachine.get()] + sMachines
        else:
            sMachines = sMachines + [wDist.txtMachine.get()]

    lLibs = DistLibVersions(wDist)   # all libs under MlsDistPaths[0]
    nError = 0
    bSP = False
    for sMachine in sMachines:
        # call event processing to make this loop user-breakable
        nRet = 1
        while nRet != 0:
          nRet = tkinter.dooneevent(2)   # 2==DONT_WAIT
        if wDist.sBreakMode == 'CANCELED':
            break
        # seperate XL from SP eg. for to test for 'Program files'
        # .. or 'Archivos de programa'
        if sMachine == '_SP_':
            bSP = True
            continue
        # proof if machine is switched on AND if the user has access to it
        if os.path.isdir("//" + sMachine + "/c$"):
            sMachPath = "//" + sMachine + "/c$/"
        elif os.path.isdir("//" + sMachine + "/C"):
            sMachPath = "//" + sMachine + "/C/"
            wDist.StatusPrint("Machine " + sMachine + " has C share instead of c$.", logging.ERROR)
            nError = nError + 1
        else:
            wDist.StatusPrint("Machine " + sMachine + " is switched off or access is denied.", logging.ERROR)
            nError = nError + 1
            continue                # skip to next machine
        # check all the possible installation pathes
        nInstCount = 0
        for sLibPath in MlsClientPaths:
            if os.path.isdir(sMachPath + sLibPath):
                nInstCount = nInstCount + 1
                if (not bSP and sLibPath[:13] == 'Program Files') \
                or (bSP and sLibPath[:20] == 'Archivos de programa'):
                    wDist.StatusPrint("Machine " + sMachine + " has O$ under " + sLibPath, logging.WARN)
                    nError = nError + 1
                else:
                    wDist.StatusPrint("Machine " + sMachine + " has O$ installed under " + sLibPath)
                    
                # check all the libs under this installation path
                sPath = sMachPath + sLibPath
                for sLibVerFile in lLibs:
                    if not os.path.isfile(sPath + SrcLibName(sLibVerFile) + "/" + sLibVerFile):
                        sFNam = str([os.path.basename(sLib) for sLib in glob.glob(sPath + SrcLibName(sLibVerFile) + "/*" + EXT_LBS)])
                        wDist.StatusPrint("Missing library " + sLibVerFile + " on machine " + sMachine \
                                          + " (found " + sFNam + ")", logging.ERROR)
                        nError = nError + 1
            
        if nInstCount == 0:
            wDist.StatusPrint("Machine " + sMachine + " has no O$ folder (ACUMENAPP or TigerLogic under Program Files).", logging.ERROR)
            nError = nError + 1
        elif nInstCount > 1 and 'resv' not in sMachine:
            wDist.StatusPrint("Machine " + sMachine + " has " + str(nInstCount) + " O$ installations.", logging.WARN)
            nError = nError + 1

    return nError

def CheckServerLibs(wDist):
  lLibs = DistLibVersions(wDist)   # all libs under MlsDistPaths[0]
  nError = 0
  for sLibVerFile in lLibs:
    # call event processing to make this loop user-breakable
    nRet = 1
    while nRet != 0:
      nRet = tkinter.dooneevent(2)   # 2==DONT_WAIT
    if wDist.sBreakMode == 'CANCELED':
      break

    # compare all other distribution paths with the reference on MlsDistPaths[0]
    sLibName = SrcLibName(sLibVerFile)
    for path in MlsDistPaths[1:]:
      if not CheckServerLib(path + sLibName + "/" + sLibVerFile, wDist):
        nError = nError + 1
  return nError

def CheckServerLib(sLibPath, wDist):
  if os.path.isfile(sLibPath):
    return True
  else:
    wDist.StatusPrint("Library " + sLibPath + " not exists!", logging.ERROR)
    return False

def CheckFiles(wDist):
  nError = 0
  sRefMach = '//' + wDist.txtFCMachine.get()
  sRefFilePath = wDist.txtFCFile.get().replace('\\','/')
  if sRefFilePath[0] <> '/':
    # extend non absolute path with default C:\ share
    sRefFilePath = '/c$/' + sRefFilePath
  if sRefFilePath[-1] == '/':
    sRefPath = sRefFilePath
    sRefFilePath = sRefPath + '*'
  else:
    sRefPath = sRefFilePath[:sRefFilePath.rfind('/')+1]
  bProgDir = (sRefPath.lower().find('/program files/') >= 0)
  
  try:
    lRefPaths = glob.glob(sRefMach + sRefFilePath)
  except:
    return 1    # RETURN Error
  if len(lRefPaths) == 0:
    wDist.StatusPrint("No reference files found in " + sRefMach + sRefPath, logging.ERROR)
    return 0    # RETURN
  lRefFiles = [os.path.basename(f) for f in lRefPaths]
  
  sMachs = wDist.txtFCMachines.get() + " "  # add space for easier end recognition
  sMach = ''
  for sCh in sMachs:
    if sCh <> ' ' and sCh <> ',':
      sMach = sMach + sCh
      continue
    elif sMach == '':
      break
    # call event processing to make this loop user-breakable
    nRet = 1
    while nRet != 0:
      nRet = tkinter.dooneevent(2)   # 2==DONT_WAIT
    if wDist.sBreakMode == 'CANCELED':
      break

    # compare with the reference with sMach (return tupel with match,mismatch,error lists)
    if bProgDir and sMach.lower() in MsMachinesXL:
      sPath = sRefPath.lower().replace('/program files/', '/archivos de programa/')
    else:
      sPath = sRefPath
    res = filecmp.cmpfiles(sRefMach + sRefPath, '//' + sMach + sPath, lRefFiles)
    for sFile in res[0]:
      wDist.StatusPrint("Machine " + sMach + " not differs " + sFile)
    for sFile in res[1]:
      wDist.StatusPrint("On Machine " + sMach + " differs " + sFile, logging.ERROR)
      nError = nError + 1
    for sFile in res[2]:
      wDist.StatusPrint("Machine " + sMach + " couldn't compare " + sFile, logging.WARN)
      nError = nError + 1
    sMach = ''
  return nError
  

def TNSInfo(sIniFilePath):
    sCurrTNS = ''
    lAllTNS = []
    if os.path.isfile(sIniFilePath):
        try:   # added to pass permission errors on LAUNCHER.INI
            fIni = file(sIniFilePath, 'r')
            lIniContent = fIni.readlines()
            if lIniContent:
                sIniContent = lIniContent[0]    # SERVICE_NAME is on 1st line
                nPos1 = sIniContent.find('=') + 1
                nPos2 = sIniContent.find('\n')
                if nPos2 == -1:
                    nPos2 = len(sIniContent)
                sCurrTNS = sIniContent[nPos1:nPos2]
                sIniContent = lIniContent[1]    # TNS_NAMES list is on 2nd line
                nPos1 = sIniContent.find('=') + 1
                nPos2 = sIniContent.find('\n')
                if nPos2 == -1:
                    nPos2 = len(sIniContent)
                lAllTNS = sIniContent[nPos1:nPos2].split(',')
            fIni.close()
        except:
            pass
    return sCurrTNS, lAllTNS
    

def ListIndex(list, val):
    ## needed because python is throwing an exception when .index not finds an entry in the list
    if val in list:
        nI = list.index(val)
    else:
        nI = -1
    return nI


def main():
  # Standalone Code Initialization
  root = Tix.Tk()  # changed from root = Tk() - used with Pmw
  demo = DistWin(root)
  if IS_DEBUG:
    root.title('Distributer V' + VERSION + "       D E B U G G I N G")
  else:
    root.title('Distributer V' + VERSION)
  # with root.quit DistWin.__del__() is not called, but works with root.destroy
  root.protocol('WM_DELETE_WINDOW', root.destroy)
  root.mainloop()

if __name__ == '__main__':
  main()
