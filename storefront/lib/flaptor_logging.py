import logging as pylogging
from logging import config 
import os

usingNativeLogger = True

__loggers = {}



def get_logger(name, force_new=False):
    '''Get the Logger instance for a given name'''
    global __loggers
    if __loggers is None:
        __loggers = {}
    if force_new:
        return pylogging.getLogger(name)
    if not __loggers.has_key(name):
        __loggers[name] = pylogging.getLogger(name)
    return __loggers[name]
    
class SpecialFormatter(pylogging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[37;4%dm"
    PIDCOLOR_SEQ = "\033[1;3%dm"
    BOLD_SEQ = "\033[1m"
    COLORS = {
        'WARN': YELLOW,
        'INFO': GREEN,
        'DEBU': BLUE,
        'CRIT': RED,
        'ERRO': RED
    }

    def __init__(self, *args, **kwargs):
        pylogging.Formatter.__init__(self, *args, **kwargs)
    def format(self, record):
        if not hasattr(record, 'prefix'): record.prefix = ''
        if not hasattr(record, 'suffix'): record.suffix = ''
        if not hasattr(record, 'compname'): record.compname = ''
        record.pid = os.getpid()
        
        record.levelname = record.levelname[:4]
        
        r = pylogging.Formatter.format(self, record)
        if record.levelname in SpecialFormatter.COLORS:
            levelcolor = SpecialFormatter.COLOR_SEQ % (SpecialFormatter.COLORS[record.levelname])
            r = r.replace('$LEVELCOLOR', levelcolor)
            r = r.replace('$RESET', SpecialFormatter.RESET_SEQ)
        else:
            r = r.replace('$COLOR', '')
            r = r.replace('$RESET', '')
        pidcolor = SpecialFormatter.COLOR_SEQ % (1 + (record.pid % 5))
        r = r.replace('$PIDCOLOR', pidcolor)
        r = r.replace('$BOLD', SpecialFormatter.BOLD_SEQ)
        return r

pylogging.SpecialFormatter = SpecialFormatter

if usingNativeLogger:
    try:
        config.fileConfig('logging.conf')
    except Exception, e:
        print e

#class NativePythonLogger:
#    def __init__(self, name):
#        '''Creates a new Logger for the given name.
#        Do not call this method directly, instead use
#        get_logger(name) to get the appropriate instance'''
#        self.name = name
#        self.__logger = pylogging.getLogger(name)
#        #self.updateLevel(5)
#
#    def updateLevel(self, level):
#        self.__level = level
#        if level == 1:
#            self.__logger.setLevel(pylogging.CRITICAL)
#        elif level == 2:
#            self.__logger.setLevel(pylogging.INFO)
#        elif level == 3:
#            self.__logger.setLevel(pylogging.WARNING)
#        elif level == 4:
#            self.__logger.setLevel(pylogging.INFO)
#        elif level == 5:
#            self.__logger.setLevel(pylogging.DEBUG)
#    
#    def debug(self, format_str, *values):
#        self.__logger.debug(format_str, *values)
#    def info(self, format_str, *values):
#        self.__logger.info(format_str, *values)
#    def warn(self, format_str, *values):
#        self.__logger.warn(format_str, *values)
#    def error(self, format_str, *values):
#        self.__logger.error(format_str, *values)
#    def exception(self, format_str, *values):
#        self.__logger.exception(format_str, *values)
#    def fatal(self, format_str, *values):
#        self.__logger.critical(format_str, *values)
