# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2014 Ciro Mattia Gonano <ciromattia@gmail.com>
# Copyright (c) 2013-2019 Pawel Jastrzebski <pawelj@iosphe.re>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all
# copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
# AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
# DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA
# OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.
#

from functools import lru_cache
import os
from hashlib import md5
from html.parser import HTMLParser
import subprocess
from packaging.version import Version
from re import split
import sys
from traceback import format_tb
from loguru import logger
import datetime

# Loglama sistemini yapılandır
def setup_logging():
    try:
        log_path = os.path.join(os.path.expanduser("~"), ".kcc", "logs")
        os.makedirs(log_path, exist_ok=True)
        
        # Log dosya adını tarih ve saat ile oluştur
        log_file = os.path.join(log_path, f"kcc_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Konsol ve dosya loglamasını yapılandır
        logger.remove()  # Varsayılan handler'ı kaldır
        
        # PyInstaller ile oluşturulan exe için özel loglama yapılandırması
        if getattr(sys, 'frozen', False):
            # Sadece dosya loglaması yap
            logger.add(log_file, 
                      format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                      level="DEBUG",
                      rotation="100 MB",
                      retention="30 days")
        else:
            # Normal modda hem konsol hem dosya loglaması yap
            logger.add(sys.stderr,
                      format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                      level="INFO")
            logger.add(log_file,
                      format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                      level="DEBUG",
                      rotation="100 MB",
                      retention="30 days")
    except Exception as e:
        print(f"Loglama sistemi başlatılamadı: {str(e)}")
        # Minimum loglama yapılandırması
        logger.add(lambda msg: print(msg), level="INFO")

# Uygulama başlangıcında loglama sistemini başlat
setup_logging()

class HTMLStripper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

    def error(self, message):
        pass


def getImageFileName(imgfile):
    logger.debug(f"Checking image file: {imgfile}")
    name, ext = os.path.splitext(imgfile)
    ext = ext.lower()
    if (name.startswith('.') and len(name) == 1) or ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.jp2', '.j2k', '.jpx', '.heic', '.heif']:
        logger.warning(f"Unsupported or invalid image format: {ext}")
        return None
    logger.debug(f"Valid image file found: {name}{ext}")
    return [name, ext]


def walkSort(dirnames, filenames):
    logger.debug(f"Sorting {len(dirnames)} directories and {len(filenames)} files")
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in split('([0-9]+)', key)]
    dirnames.sort(key=lambda name: alphanum_key(name.lower()))
    filenames.sort(key=lambda name: alphanum_key(name.lower()))
    return dirnames, filenames


def walkLevel(some_dir, level=1):
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        dirs, files = walkSort(dirs, files)
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]



def sanitizeTrace(traceback):
    return ''.join(format_tb(traceback))\
        .replace('C:/projects/kcc/', '')\
        .replace('c:/projects/kcc/', '')\
        .replace('C:/python37-x64/', '')\
        .replace('c:/python37-x64/', '')\
        .replace('C:\\projects\\kcc\\', '')\
        .replace('c:\\projects\\kcc\\', '')\
        .replace('C:\\python37-x64\\', '')\
        .replace('c:\\python37-x64\\', '')


# noinspection PyUnresolvedReferences
def dependencyCheck(level):
    missing = []
    if level > 2:
        try:
            from PySide6.QtCore import qVersion as qtVersion
            if Version('6.5.1') > Version(qtVersion()):
                missing.append('PySide 6.5.1+')
        except ImportError:
            missing.append('PySide 6.5.1+')
        try:
            import raven
        except ImportError:
            missing.append('raven 6.0.0+')
    if level > 1:
        try:
            from psutil import __version__ as psutilVersion
            if Version('5.0.0') > Version(psutilVersion):
                missing.append('psutil 5.0.0+')
        except ImportError:
            missing.append('psutil 5.0.0+')
        try:
            from types import ModuleType
            from slugify import __version__ as slugifyVersion
            if isinstance(slugifyVersion, ModuleType):
                slugifyVersion = slugifyVersion.__version__
            if Version('1.2.1') > Version(slugifyVersion):
                missing.append('python-slugify 1.2.1+')
        except ImportError:
            missing.append('python-slugify 1.2.1+')
    
    # Temel görüntü işleme kütüphaneleri
    try:
        from PIL import __version__ as pillowVersion
        if Version('5.2.0') > Version(pillowVersion):
            missing.append('Pillow 5.2.0+')
    except ImportError:
        missing.append('Pillow 5.2.0+')
    
    # HEIF desteği kontrolü
    try:
        import pillow_heif
    except ImportError:
        print('WARNING: pillow-heif is not installed. HEIF/HEIC support will be disabled.')
    
    # Numpy kontrolü
    try:
        import numpy
        if Version('1.22.4') > Version(numpy.__version__):
            missing.append('numpy 1.22.4+')
    except ImportError:
        missing.append('numpy 1.22.4+')

    if len(missing) > 0:
        print('ERROR: ' + ', '.join(missing) + ' is not installed!')
        sys.exit(1)
    
    # Arşiv araçlarını kontrol et
    available_archive_tools()

@lru_cache
def available_archive_tools():
    logger.debug("Checking available archive tools")
    available = []
    tool_versions = {}
    
    tools = {
        'tar': ['tar', '--version'],
        '7z': ['7z', '--help'],
        'unar': ['unar', '--version'],
        'unrar': ['unrar', '--version']
    }

    for tool, command in tools.items():
        try:
            logger.debug(f"Checking {tool} availability")
            result = subprocess_run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode == 0:
                available.append(tool)
                output = result.stdout.decode('utf-8', errors='ignore')
                tool_versions[tool] = output.split('\n')[0] if output else 'Version unknown'
                logger.info(f"Found {tool}: {tool_versions[tool]}")
        except FileNotFoundError:
            logger.warning(f"{tool} not found in system PATH")
    
    if not available:
        logger.error("No archive tools found!")
        print('WARNING: No archive tools found. Please install at least one of: tar, 7z, unar, or unrar')
    else:
        print('Available archive tools:')
        for tool in available:
            print(f'- {tool}: {tool_versions.get(tool, "Version unknown")}')
    
    return available

def subprocess_run(command, **kwargs):
    logger.debug(f"Running command: {command}")
    if os.name == 'nt':
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    try:
        result = subprocess.run(command, timeout=30, **kwargs)
        logger.debug(f"Command completed with return code: {result.returncode}")
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 30 seconds: {command}")
        print(f'WARNING: Command {command} timed out after 30 seconds')
        return subprocess.CompletedProcess(command, -1)
    except Exception as e:
        logger.error(f"Error running command {command}: {str(e)}")
        raise
