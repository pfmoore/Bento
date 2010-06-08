import sys
import os
import shutil

from bento.installed_package_description \
    import \
        InstalledSection
from bento.commands.errors \
    import \
        CommandExecutionFailure

import yaku.context

def build_extension(bld, pkg, inplace):
    ret = {}
    for ext in pkg.extensions.values():
        try:
            outputs = bld.builders["pyext"].extension(ext.name, ext.sources)
            so_ext = bld.builders["pyext"].env["PYEXT_SO"]
            if inplace:
                # FIXME: do package -> location + remove hardcoded extension
                # FIXME: handle in-place at yaku level
                for o in outputs:
                    target = os.path.join(
                                os.path.dirname(ext.name.replace(".", os.sep)),
                                os.path.basename(o))
                    shutil.copy(o, target)
        except RuntimeError, e:
            msg = "Building extension %s failed: %s" % (ext.name, str(e))
            raise CommandExecutionFailure(msg)

        # FIXME: do package -> location translation correctly
        pkg_dir = os.path.dirname(ext.name.replace('.', os.path.sep))
        target = os.path.join('$sitedir', pkg_dir)
        fullname = ext.name
        ext_targets = outputs
        # FIXME: assume all outputs of one extension are in one directory
        srcdir = os.path.dirname(ext_targets[0])
        section = InstalledSection("extensions", fullname, srcdir,
                                    target, [os.path.basename(o) for o in outputs])
        ret[fullname] = section
    return ret

def build_extensions(pkg, inplace=False):
    bld = yaku.context.get_bld()
    if "-v" in sys.argv:
        bld.env["VERBOSE"] = True

    try:
        return build_extension(bld, pkg, inplace)
    finally:
        bld.store()