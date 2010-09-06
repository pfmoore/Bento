import sys
import os
import shutil

from bento.installed_package_description \
    import \
        InstalledSection
from bento.commands.errors \
    import \
        CommandExecutionFailure
from bento.core.utils \
    import \
        cpu_count
import bento.core.errors

import yaku.task_manager
import yaku.context
import yaku.scheduler
import yaku.errors

def run_tasks(bld, all_outputs, inplace):
    task_manager = yaku.task_manager.TaskManager(bld.tasks)
    runner = yaku.scheduler.SerialRunner(bld, task_manager)
    runner.start()
    runner.run()

    if inplace:
        # FIXME: do package -> location + remove hardcoded extension
        # FIXME: handle in-place at yaku level
        for ext, outputs in all_outputs.items():
            for o in outputs:
                target = os.path.join(
                            os.path.dirname(ext.replace(".", os.sep)),
                            os.path.basename(o.abspath()))
                shutil.copy(o.abspath(), target)
    return

def build_isection(bld, ext_name, files):
    # Given an extension name and the list of files which constitute
    # it (e.g. the .so on unix, the .pyd on windows, etc...), return
    # an InstallSection

    # FIXME: do package -> location translation correctly
    pkg_dir = os.path.dirname(ext_name.replace('.', os.path.sep))
    target = os.path.join('$sitedir', pkg_dir)

    # FIXME: assume all outputs of one extension are in one directory
    srcdir = files[0].parent.path_from(bld.src_root)
    section = InstalledSection("extensions", ext_name, srcdir,
                                target, [o.name for o in files])
    return section

def build_extension(bld, extension, verbose):
    builder = bld.builders["pyext"]
    try:
        if verbose:
            builder.env["VERBOSE"] = True
        return builder.extension(extension.name, extension.sources)
    except RuntimeError, e:
        msg = "Building extension %s failed: %s" % \
              (extension.name, str(e))
        raise CommandExecutionFailure(msg)

def _build_extensions(extensions, bld, inplace, verbose, extension_callback):
    ret = {}
    if len(extensions) < 1:
        return  ret

    all_outputs = {}
    subexts = {}

    for name, ext in extensions.items():
        if name in extension_callback:
            tasks = extension_callback[name](bld, ext, verbose)
            if tasks is None:
                raise ValueError(
                    "Registered callback for %s did not return " \
                    "a list of tasks!" % ext.name)
        else:
            tasks = build_extension(bld, ext, verbose)
        if len(tasks) > 1:
            outputs = tasks[0].gen.outputs
            if len(outputs) > 0:
                all_outputs[ext.name] = outputs
                ret[ext.name] = build_isection(bld, ext.name, outputs)

    run_tasks(bld, all_outputs, inplace)
    return ret

def build_compiled_library(bld, extension, verbose, callbacks):
    builder = bld.builders["ctasks"]
    try:
        if verbose:
            builder.env["VERBOSE"] = True
        for p in extension.include_dirs:
            builder.env["CPPPATH"].insert(0, p)
        if extension.name in callbacks:
            tasks = callbacks[extension.name](bld, extension, verbose)
            if tasks is None:
                raise ValueError(
                    "Registered callback for %s did not return " \
                    "a list of tasks!" % extension.name)
        else:
            tasks = builder.static_library(extension.name,
                                          extension.sources)
        return tasks
    except RuntimeError, e:
        msg = "Building extension %s failed: %s" % (extension.name, str(e))
        raise CommandExecutionFailure(msg)

def _build_compiled_libraries(compiled_libraries, bld, inplace, verbose, callbacks):
    ret = {}
    if len(compiled_libraries) < 1:
        return  ret

    all_outputs = {}
    for ext in compiled_libraries.values():
        outputs = build_compiled_library(bld, ext, verbose, callbacks)
        all_outputs[ext.name] = outputs
        ret[ext.name] = build_isection(bld, ext.name, outputs)

    run_tasks(bld, all_outputs, inplace)
    return ret

def build_extensions(extensions, yaku_build_ctx, builder_callbacks, inplace=False, verbose=False):
    try:
        return _build_extensions(extensions, yaku_build_ctx,
                inplace, verbose, builder_callbacks)
    except yaku.errors.TaskRunFailure, e:
        if e.explain:
            msg = e.explain
        else:
            msg = ""
        msg += "command '%s' failed (see above)" % " ".join(e.cmd)
        raise bento.core.errors.BuildError(msg)

def build_compiled_libraries(libraries, yaku_build_ctx, callbacks, inplace=False, verbose=False):
    try:
        return _build_compiled_libraries(libraries, yaku_build_ctx, inplace, verbose, callbacks)
    except yaku.errors.TaskRunFailure, e:
        if e.explain:
            msg = e.explain
        else:
            msg = ""
        msg += "command '%s' failed (see above)" % " ".join(e.cmd)
        raise bento.core.errors.BuildError(msg)