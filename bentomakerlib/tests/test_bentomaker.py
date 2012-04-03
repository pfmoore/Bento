import os
import sys
import tempfile
import shutil

import os.path as op

import multiprocessing

from bento.compat.api.moves \
    import \
        unittest
from bento.core.node \
    import \
        create_base_nodes
from bento.core.utils \
    import \
        extract_exception
from bento.core.parser.api \
    import \
        ParseError
from bento.convert.api \
    import \
        ConvertionError
from bento.commands.api \
    import \
        CommandExecutionFailure
from bento.commands.context \
    import \
        GlobalContext

import bentomakerlib.bentomaker

# FIXME: nose is broken - needed to make it happy
if sys.platform == "darwin":
    import bento.commands.build_mpkg
# FIXME: nose is broken - needed to make it happy
import bento.commands.build_yaku
# FIXME: nose is broken - needed to make it happy
from bento.compat.dist \
    import \
        DistributionMetadata

from bento.commands.errors \
    import \
        UsageException

from bentomakerlib.bentomaker \
    import \
        main, noexc_main, _wrapped_main, parse_global_options

class Common(unittest.TestCase):
    def setUp(self):
        super(Common, self).setUp()

        self.d = tempfile.mkdtemp()
        self.old = os.getcwd()

        try:
            os.chdir(self.d)
            self.top_node, self.build_node, self.run_node = create_base_nodes(self.d, op.join(self.d, "build"))
        except:
            os.chdir(self.old)
            shutil.rmtree(self.d)

    def tearDown(self):
        os.chdir(self.old)
        shutil.rmtree(self.d)
        super(Common, self).tearDown()

class TestSpecialCommands(Common):
    # FIXME: stupid mock to reset global state between tests
    def test_help_globals(self):
        main(["help", "globals"])

    def test_help_commands(self):
        main(["help", "commands"])

    def test_global_options_version(self):
        main(["--version"])

    def test_global_options_full_version(self):
        main(["--full-version"])

    def test_usage(self):
        main(["--help"])

    def test_command_help(self):
        main(["configure", "--help"])

class TestMain(Common):
    def test_no_bento(self):
        main([])

    def test_help_non_existing_command(self):
        self.assertRaises(UsageException, lambda: main(["help", "floupi"]))

    def test_configure_help(self):
        bento_info = """\
Name: foo
"""
        self.top_node.make_node("bento.info").write(bento_info)
        main(["configure", "--help"])

    def test_help_command(self):
        bento_info = """\
Name: foo
"""
        self.top_node.make_node("bento.info").write(bento_info)
        main(["help", "configure"])

    def test_configure(self):
        bento_info = """\
Name: foo
"""
        self.top_node.make_node("bento.info").write(bento_info)
        main(["configure"])

class TestMainCommands(Common):
    def setUp(self):
        super(TestMainCommands, self).setUp()

        bento_info = """\
Name: foo
"""
        self.top_node.make_node("bento.info").write(bento_info)

    def tearDown(self):
        super(TestMainCommands, self).tearDown()

    def test_configure(self):
        main(["configure"])

    def test_build(self):
        main(["build"])

    def test_install(self):
        main(["install"])

    def test_sdist(self):
        main(["sdist"])

    def test_build_egg(self):
        main(["build_egg"])

    @unittest.skipIf(sys.platform != "win32", "wininst is win32-only test")
    def test_wininst(self):
        main(["build_wininst"])

    @unittest.skipIf(sys.platform != "darwin", "mpkg is darwin-only test")
    def test_mpkg(self):
        main(["build_mpkg"])

class TestConvertCommand(Common):
    def test_convert(self):
        self.top_node.make_node("setup.py").write("""\
from distutils.core import setup

setup(name="foo")
""")
        main(["convert"])
        n = self.top_node.find_node("bento.info")
        r_bento = """\
Name: foo
Version: 0.0.0
Summary: UNKNOWN
Url: UNKNOWN
DownloadUrl: UNKNOWN
Description: UNKNOWN
Author: UNKNOWN
AuthorEmail: UNKNOWN
Maintainer: UNKNOWN
MaintainerEmail: UNKNOWN
License: UNKNOWN
Platforms: UNKNOWN

ExtraSourceFiles:
    setup.py
"""
        self.assertEqual(n.read(), r_bento)

class TestRunningEnvironment(Common):
    def test_in_sub_directory(self):
        bento_info = """\
Name: foo
"""
        self.top_node.make_node("bento.info").write(bento_info)

        subdir_node = self.top_node.make_node("subdir")
        subdir_node.mkdir()

        try:
            os.chdir(subdir_node.abspath())
            self.assertRaises(UsageException, lambda: main(["--bento-info=../bento.info", "configure"]))
        finally:
            os.chdir(self.top_node.abspath())

class TestCommandData(Common):
    def test_simple(self):
        # We use subprocesses to emulate how bentomaker would run itself - this
        # is more of a functional test than a unit test.
        bento_info = """\
Name: foo
"""
        self.top_node.make_node("bento.info").write(bento_info)

        p = multiprocessing.Process(target=noexc_main, args=(['configure', '--prefix=/fubar'],))
        p.start()
        p.join()

        def check_cmd_data(q):
            from bentomakerlib.bentomaker \
                import \
                    CommandDataProvider, CMD_DATA_DUMP

            cmd_data_db = self.build_node.find_node(CMD_DATA_DUMP)
            if cmd_data_db is None:
                raise IOError()
            cmd_data_store = CommandDataProvider.from_file(cmd_data_db.abspath())
            q.put(cmd_data_store.get_argv("configure"))

        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=check_cmd_data, args=(q,))
        p.start()
        self.assertEqual(q.get(timeout=1), ["--prefix=/fubar"])
        p.join()

    def test_flags(self):
        """Test that flag value specified on the command line are correctly
        stored between run."""
        # We use subprocesses to emulate how bentomaker would run itself - this
        # is more of a functional test than a unit test.
        bento_info = """\
Name: foo

Flag: debug
    Description: debug flag
    Default: true

HookFile: bscript

Library:
    if flag(debug):
        Modules: foo
    else:
        Modules: bar
"""
        self.top_node.make_node("bento.info").write(bento_info)
        self.top_node.make_node("bscript").write("""\
import sys
from bento.commands import hooks

@hooks.pre_build
def pre_build(context):
    if not context.pkg.py_modules == ['bar']:
        sys.exit(57)
""")
        self.top_node.make_node("foo.py").write("")
        self.top_node.make_node("bar.py").write("")

        p = multiprocessing.Process(target=main, args=(['configure', '--debug=false'],))
        p.start()
        p.join()

        p = multiprocessing.Process(target=main, args=(['build'],))
        p.start()
        p.join()

        self.assertEqual(p.exitcode, 0)

def raise_function(klass):
    raise klass()

class TestBentomakerError(Common):
    def _assert_raises(self, error_code):
        try:
            noexc_main()
        except SystemExit:
            e = extract_exception()
            self.assertEqual(e.code, error_code)

    def test_simple(self):
        errors = (
            (UsageException, 1),
            (ParseError, 2),
            (ConvertionError, 3),
            (CommandExecutionFailure, 4),
            (bento.core.errors.ConfigurationError, 8),
            (bento.core.errors.BuildError, 16),
            (bento.core.errors.InvalidPackage, 32),
            (Exception, 1),
        )
        for klass, error_code in errors:
            old_main = bentomakerlib.bentomaker.main
            bentomakerlib.bentomaker.main = lambda argv: raise_function(klass)
            try:
                self._assert_raises(error_code)
            finally:
                bentomakerlib.bentomaker.main = old_main

class TestStartupHook(Common):
    def setUp(self):
        super(TestStartupHook, self).setUp()

        bento_info = """\
Name: foo

HookFile: bscript
"""
        self.top_node.make_node("bento.info").write(bento_info)

    def test_simple(self):
        bscript = """\
from bento.commands import hooks

@hooks.startup
def startup(context):
    context.seen = True
"""
        self.top_node.make_node("bscript").write(bscript)

        global_context = GlobalContext()
        popts = parse_global_options(global_context, ["configure"])

        _wrapped_main(global_context, popts, self.run_node, self.top_node,
                self.build_node)
        self.assertTrue(getattr(global_context, "seen", False))

    def test_register_command(self):
        bscript = """\
from bento.commands import hooks
from bento.commands.core import Command

@hooks.startup
def startup(context):
    context.register_command("foo", Command)
"""
        self.top_node.make_node("bscript").write(bscript)

        global_context = GlobalContext()
        popts = parse_global_options(global_context, ["configure"])

        _wrapped_main(global_context, popts, self.run_node, self.top_node,
                self.build_node)
        self.assertTrue(global_context.is_command_registered("foo"))

    def test_register_existing_command(self):
        bscript = """\
from bento.commands import hooks
from bento.commands.core import Command

@hooks.startup
def startup(context):
    context.register_command("configure", Command)
"""
        self.top_node.make_node("bscript").write(bscript)

        global_context = GlobalContext()
        popts = parse_global_options(global_context, ["configure"])

        self.assertRaises(ValueError, _wrapped_main,
                          global_context, popts, self.run_node, self.top_node,
                           self.build_node)
