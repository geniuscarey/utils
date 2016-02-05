import subprocess
import os
import shlex
import ctypes, os
import time
import pprint

CLOCK_MONOTONIC_RAW = 4
class timespec(ctypes.Structure):
    _fields_ = [
        ('tv_sec', ctypes.c_long),
        ('tv_nsec', ctypes.c_long)
    ]

librt = ctypes.CDLL('librt.so.1', use_errno=True)
clock_gettime = librt.clock_gettime
clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

def monotonic_time():
    t = timespec()
    if clock_gettime(CLOCK_MONOTONIC_RAW , ctypes.pointer(t)) != 0:
        errno_ = ctypes.get_errno()
        raise OSError(errno_, os.strerror(errno_))
    return t.tv_sec + t.tv_nsec * 1e-9

DEBUG = True
class Log(object):
    def __init__(self, logger):
        self._logger = logger

    def do_nothing(self, *args, **kwargs):
        if DEBUG:
            print args, kwargs

    def __getattr__(self, name):
        if self._logger:
            return getattr(self._logger, name)
        else:
            return self.do_nothing

class ExecuteException(Exception):
    def __init__(self, ret_code, cmd, stdout, stderr):
        self.ret_code = ret_code
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
        err_msg = 'execute cmd error:\n'
        err_dict = {"cmd": cmd,
                    "ret_code": ret_code,
                    "stdout": stdout,
                    "stderr": stderr}
        err_msg += pprint.pformat(err_dict, indent=1)
        super(ExecuteException, self).__init__(err_msg)

def execute(cmd,
            run_as_root=False,
            input=None,
            retries=1,
            retry_delay=0,
            expect_retcode=[0],
            shell=True,
            logger=None):

    _log = Log(logger)

    if run_as_root and os.geteuid() != 0:
        cmd = "sudo" + cmd

    if not shell:
        cmd = shlex.split(cmd)

    for i in range(retries+1):
        start_time = monotonic_time()
        pobj = subprocess.Popen(cmd,
                                shell=shell,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                close_fds=True)
        res = pobj.communicate(input)
        pobj.stdin.close()
        ret_code = pobj.returncode
        time_elapse = monotonic_time() - start_time
        _log.info("run cmd %s return %s" % (cmd, ret_code))
        stdout, stderr = res
        if expect_retcode and ret_code not in expect_retcode:
            raise ExecuteException(cmd=cmd,
                                   ret_code=ret_code,
                                   stdout=stdout,
                                   stderr=stderr)

        return (stdout, stderr)
        time.sleep(retry_delay)
