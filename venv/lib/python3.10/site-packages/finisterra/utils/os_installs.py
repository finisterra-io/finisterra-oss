import platform
import os
import subprocess
import logging

logger = logging.getLogger('finisterra')


def get_os():
    if os.name == 'nt':
        return 'Windows'
    elif os.name == 'posix':
        if platform.system() == 'Darwin':
            return 'macOS'
        else:
            return 'Linux'
    else:
        return 'Unknown'
