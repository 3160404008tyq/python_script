import os, sys
from importlib import reload

class Reloader:
    """Checks to see if any loaded modules have changed on disk and, 
    if so, reloads them.
    """

    """File suffix of compiled modules."""
    if sys.platform.startswith('java'):
        SUFFIX = '$py.class'
    else:
        SUFFIX = '.pyc'
    
    def __init__(self):
        self.mtimes = {}

    def __call__(self):
        for mod in sys.modules.values():
            self.check(mod)

    def check(self, mod):
        # jython registers java packages as modules but they either
        # don't have a __file__ attribute or its value is None
        if not (mod and hasattr(mod, '__file__') and mod.__file__):
            return

        try: 
            mtime = os.stat(mod.__file__).st_mtime
        except (OSError, IOError):
            return
        if mod.__file__.endswith(self.__class__.SUFFIX) and os.path.exists(mod.__file__[:-1]):
            mtime = max(os.stat(mod.__file__[:-1]).st_mtime, mtime)
            
        if mod not in self.mtimes:
            self.mtimes[mod] = mtime
        elif self.mtimes[mod] < mtime:
            try:
                reload(mod)
                print(mod.__file__, "is updated!")
                self.mtimes[mod] = mtime
            except:
                print(mod.__file__, "failed to update!")
                pass
