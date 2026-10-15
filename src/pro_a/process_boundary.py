"""Windows mandatory-integrity boundary for unprivileged Web/MCP processes.

Provision only mutable Workbench directories as Low. Canonical, Operator,
configuration and installed code must remain Medium or above. No ACL mutation
is performed by this launcher. A failed boundary check never enables admission.
"""
import argparse
import ctypes as c
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import sys

from .operational_contract import require


def _api():
    require(os.name == 'nt', 'WINDOWS_INTEGRITY_BOUNDARY_REQUIRED')
    a = c.WinDLL('advapi32', use_last_error=True)
    k = c.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = w.HANDLE
    k.CloseHandle.argtypes = [w.HANDLE]
    a.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    a.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    return a, k


def _check(ok):
    if not ok:
        raise c.WinError(c.get_last_error())


class _Sid(c.Structure):
    _fields_ = [('sid', c.c_void_p), ('attributes', w.DWORD)]


def integrity_level():
    a, k = _api()
    token = w.HANDLE()
    _check(a.OpenProcessToken(k.GetCurrentProcess(), 8, c.byref(token)))
    try:
        size = w.DWORD()
        a.GetTokenInformation(token, 25, None, 0, c.byref(size))
        data = c.create_string_buffer(size.value)
        _check(a.GetTokenInformation(token, 25, data, size, c.byref(size)))
        sid = c.cast(data, c.POINTER(_Sid)).contents.sid
        # SID header: revision, subauthority count, authority; last DWORD is RID.
        count = c.cast(sid, c.POINTER(c.c_ubyte))[1]
        return c.cast(sid + 8, c.POINTER(w.DWORD))[count - 1]
    finally:
        k.CloseHandle(token)


def require_readonly_boundary(config):
    require(integrity_level() == 4096, 'UNPRIVILEGED_PROCESS_REQUIRED')
    _, k = _api()
    k.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
    k.CreateFileW.restype = w.HANDLE
    paths = [config.knowledge_db, config.knowledge_db.parent, Path(__file__).resolve().parent,
             Path(sys.executable).resolve()]
    for path in paths:
        # Request write/delete/DACL rights without creating or modifying anything.
        for access in (0x40000000, 0x10000, 0x40000):
            handle = k.CreateFileW(str(path), access, 7, None, 3, 0x02000000, None)
            if handle != w.HANDLE(-1).value:
                k.CloseHandle(handle)
                require(False, 'CANONICAL_WRITE_BOUNDARY_MISSING')
            require(c.get_last_error() == 5, 'BOUNDARY_ACCESS_CHECK_FAILED')
    return {'scheme': 'WINDOWS_MANDATORY_INTEGRITY', 'web_integrity': 4096}


def launch(command, cwd=None, *, stdio=False):
    """Start an ordinary child with an irreversible Low primary token, no handles."""
    a, k = _api()
    require(integrity_level() >= 8192, 'TRUSTED_LAUNCHER_REQUIRED')

    class Startup(c.Structure):
        _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
                    ('x', w.DWORD), ('y', w.DWORD), ('xs', w.DWORD), ('ys', w.DWORD),
                    ('xc', w.DWORD), ('yc', w.DWORD), ('fill', w.DWORD), ('flags', w.DWORD),
                    ('show', w.WORD), ('cb2', w.WORD), ('res2', c.c_void_p),
                    ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]
    class Process(c.Structure):
        _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]
    class StartupEx(c.Structure):
        _fields_ = [('startup', Startup), ('attributes', c.c_void_p)]
    a.CreateRestrictedToken.argtypes = [w.HANDLE, w.DWORD, w.DWORD, c.c_void_p, w.DWORD,
                                      c.c_void_p, w.DWORD, c.c_void_p, c.POINTER(w.HANDLE)]
    a.ConvertStringSidToSidW.argtypes = [w.LPCWSTR, c.POINTER(c.c_void_p)]
    a.SetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    a.CreateProcessAsUserW.argtypes = [w.HANDLE, w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p,
                                     w.BOOL, w.DWORD, c.c_void_p, w.LPCWSTR,
                                     c.c_void_p, c.POINTER(Process)]
    token, low = w.HANDLE(), w.HANDLE()
    sid = c.c_void_p()
    _check(a.OpenProcessToken(k.GetCurrentProcess(), 0xF01FF, c.byref(token)))
    inherited = []
    attributes = None
    try:
        _check(a.CreateRestrictedToken(token, 1, 0, None, 0, None, 0, None, c.byref(low)))
        _check(a.ConvertStringSidToSidW('S-1-16-4096', c.byref(sid)))
        label = _Sid(sid, 0x20)
        _check(a.SetTokenInformation(low, 25, c.byref(label), c.sizeof(label) + 12))
        startup = Startup(); startup.cb = c.sizeof(startup)
        flags = 0x08000000
        if stdio:
            # Only the three explicit pipes may cross the privilege boundary.
            k.GetStdHandle.argtypes = [w.DWORD]; k.GetStdHandle.restype = w.HANDLE
            k.DuplicateHandle.argtypes = [w.HANDLE, w.HANDLE, w.HANDLE, c.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD]
            for number in (-10, -11, -12):
                handle = w.HANDLE()
                _check(k.DuplicateHandle(k.GetCurrentProcess(), k.GetStdHandle(number & 0xffffffff),
                                        k.GetCurrentProcess(), c.byref(handle), 0, True, 2))
                inherited.append(handle.value)
            startup.flags = 0x100
            startup.stdin, startup.stdout, startup.stderr = inherited
            size = c.c_size_t()
            k.InitializeProcThreadAttributeList.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(c.c_size_t)]
            k.UpdateProcThreadAttribute.argtypes = [c.c_void_p, w.DWORD, c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_void_p]
            k.InitializeProcThreadAttributeList(None, 1, 0, c.byref(size))
            attributes = c.create_string_buffer(size.value)
            _check(k.InitializeProcThreadAttributeList(attributes, 1, 0, c.byref(size)))
            handles = (w.HANDLE * 3)(*inherited)
            _check(k.UpdateProcThreadAttribute(attributes, 0, 0x20002, handles, c.sizeof(handles), None, None))
            startup.cb = c.sizeof(StartupEx)
            startup = StartupEx(startup, c.cast(attributes, c.c_void_p))
            flags |= 0x80000
        process = Process()
        _check(a.CreateProcessAsUserW(low, None, c.create_unicode_buffer(subprocess.list2cmdline(command)),
                                     None, None, stdio, flags, None, cwd, c.byref(startup), c.byref(process)))
        k.CloseHandle(process.thread)
        if stdio:
            k.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
            k.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
            k.WaitForSingleObject(process.process, 0xffffffff)
            code = w.DWORD(); _check(k.GetExitCodeProcess(process.process, c.byref(code)))
            k.CloseHandle(process.process)
            return code.value
        k.CloseHandle(process.process)
        return process.pid
    finally:
        k.CloseHandle(token)
        if low: k.CloseHandle(low)
        for handle in inherited: k.CloseHandle(handle)
        if attributes is not None:
            k.DeleteProcThreadAttributeList.argtypes = [c.c_void_p]
            k.DeleteProcThreadAttributeList(attributes)
        if sid:
            k.LocalFree.argtypes = [c.c_void_p]
            k.LocalFree(sid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd')
    parser.add_argument('--stdio', action='store_true')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    require(bool(args.command), 'COMMAND_REQUIRED')
    result = launch(args.command, args.cwd, stdio=args.stdio)
    if args.stdio: raise SystemExit(result)
    print(result)


if __name__ == '__main__':
    main()
