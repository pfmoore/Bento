import os

from collections \
    import \
        defaultdict
from cPickle \
    import \
        dump, load

class PickledStore(object):
    """Simple class to store/retrieve data from a pickled file."""
    @classmethod
    def from_dump(cls, filename):
        fid = open(filename, "rb")
        try:
            data = load(fid)
        finally:
            fid.close()

        inst = cls()
        inst._data = data
        return inst

    def store(self, filename):
        fid = open(filename, "wb")
        try:
            dump(self._data, fid)
        finally:
            fid.close()

def _invert_dependencies(deps):
    """Given a dictionary of edge -> dependencies representing a DAG, "invert"
    all the dependencies."""
    ideps = {}
    for k, v in deps.items():
        for d in v:
            l = ideps.get(d, None)
            if l:
                l.append(k)
            else:
                l = [k]
            ideps[d] = l

    return ideps

class CommandScheduler(object):
    def __init__(self):
        self.before = defaultdict(list)
        self.klasses = {}

    def _register(self, klass):
        if not klass.__name__ in self.klasses:
            self.klasses[klass.__name__] = klass

    def set_before(self, klass, klass_prev):
        """Set klass_prev to be run before klass"""
        self._register(klass)
        self._register(klass_prev)
        klass_name = klass.__name__
        klass_prev_name = klass_prev.__name__
        if not klass_prev_name in self.before[klass_name]:
            self.before[klass_name].append(klass_prev_name)

    def set_after(self, klass, klass_next):
        """Set klass_next to be run after klass"""
        return self.set_before(klass_next, klass)

    def order(self, target):
        # XXX: cycle detection missing !
        after = _invert_dependencies(self.before)

        visited = {}
        out = []

        # DFS-based topological sort: this is better to only get the
        # dependencies of a given target command instead of sorting the whole
        # dag
        def _visit(n, stack_visited):
            if n in stack_visited:
                raise ValueError("Cycle detected: %r" % after)
            else:
                stack_visited[n] = None
            if not n in visited:
                visited[n] = None
                for m, v in after.items():
                    if n in v:
                        _visit(m, stack_visited)
                out.append(n)
            stack_visited.pop(n)
        _visit(target.__name__, {})
        return [self.klasses[o] for o in out[:-1]]

# Instance of this class record, persist and retrieve data on a per command
# basis, to reuse them between runs. Anything refered in Command.external_deps
# need to be registered here
# It is slightly over-designed for the current use-case of storing per-command
# arguments
class CommandDataProvider(object):
    @classmethod
    def from_file(cls, filename):
        if os.path.exists(filename):
            fid = open(filename, "rb")
            try:
                cmd_argv = load(fid)
            finally:
                fid.close()
        else:
            cmd_argv = {}
        return cls(cmd_argv)

    def __init__(self, cmd_argv=None):
        if cmd_argv is None:
            cmd_argv = {}
        self._cmd_argv = cmd_argv

    def set(self, cmd_name, cmd_argv):
        self._cmd_argv[cmd_name] = cmd_argv[:]

    def get_argv(self, cmd_name):
        try:
            return self._cmd_argv[cmd_name]
        except KeyError:
            return []

    def store(self, filename):
        fid = open(filename, "wb")
        try:
            dump(self._cmd_argv, fid)
        finally:
            fid.close()
