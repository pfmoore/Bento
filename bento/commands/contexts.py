from bento.commands.registries \
    import \
        CommandRegistry, ContextRegistry, OptionsRegistry
from bento.commands.dependency \
    import \
        CommandScheduler
from bento.commands.hooks \
    import \
        HookRegistry

class GlobalContext(object):
    def __init__(self, commands_registry=None, contexts_registry=None,
            options_registry=None, commands_scheduler=None):
        self._commands_registry = commands_registry or CommandRegistry()
        self._contexts_registry = contexts_registry or ContextRegistry()
        self._options_registry = options_registry or OptionsRegistry()
        self._scheduler = commands_scheduler or CommandScheduler()
        self._hooks_registry = HookRegistry()

    #------------
    # Command API
    #------------
    def register_command(self, cmd_name, cmd, public=True):
        """Register a command name to a command instance.

        Parameters
        ----------
        cmd_name: str
            name of the command
        cmd: object
            instance from a subclass of Command
        """
        self._commands_registry.register(cmd_name, cmd, public)

    def retrieve_command(self, cmd_name):
        """Return the command instance registered for the given command name."""
        return self._commands_registry.retrieve(cmd_name)

    def is_command_registered(self, cmd_name):
        """Return True if the command is registered."""
        return self._commands_registry.is_registered(cmd_name)

    def command_names(self, public_only=True):
        if public_only:
            return self._commands_registry.public_command_names()
        else:
            return self._commands_registry.command_names()

    #--------------------
    # Command Context API
    #--------------------
    def register_command_context(self, cmd_name, klass):
        self._contexts_registry.register(cmd_name, klass)

    def retrieve_command_context(self, cmd_name):
        return self._contexts_registry.retrieve(cmd_name)

    def is_command_context_registered(self, cmd_name):
        """Return True if the command context is registered."""
        return self._contexts_registry.is_registered(cmd_name)

    #--------------------
    # Command Options API
    #--------------------
    def register_options_context(self, cmd_name, klass):
        return self._options_registry.register(cmd_name, klass)

    def retrieve_options_context(self, cmd_name):
        return self._options_registry.retrieve(cmd_name)

    def is_options_context_registered(self, cmd_name):
        return self._options_registry.is_registered(cmd_name)

    def add_option_group(self, cmd_name, name, title):
        """Add a new option group for the given command.
        
        Parameters
        ----------
        cmd_name: str
            name of the command
        name: str
            name of the group option
        title: str
            title of the group
        """
        ctx = self._options_registry.retrieve(cmd_name)
        ctx.add_group(name, title)

    def add_option(self, cmd_name, option, group=None):
        """Add a new option for the given command.

        Parameters
        ----------
        cmd_name: str
            name of the command
        option: str
            name of the option
        group: str, None
            group to associated with
        """
        ctx = self._options_registry.retrieve(cmd_name)
        ctx.add_option(option, group)

    #-----------------------
    # Command dependency API
    #-----------------------
    def set_before(self, cmd_name, cmd_name_before):
        """Specify that command cmd_name_before should run before cmd_name."""
        self._scheduler.set_before(cmd_name, cmd_name_before)

    def set_after(self, cmd_name, cmd_name_after):
        """Specify that command cmd_name_before should run after cmd_name."""
        self._scheduler.set_after(cmd_name, cmd_name_after)

    def retrieve_dependencies(self, cmd_name):
        """Return the ordered list of command names to run before the given
        command name."""
        return self._scheduler.order(cmd_name)

    #---------
    # Hook API
    #---------
    def add_pre_hook(self, hook, cmd_name):
        self._hooks_registry.add_pre_hook(hook, cmd_name)

    def add_post_hook(self, hook, cmd_name):
        self._hooks_registry.add_post_hook(hook, cmd_name)

    def retrieve_pre_hooks(self, cmd_name):
        return self._hooks_registry.retrieve_pre_hooks(cmd_name)

    def retrieve_post_hooks(self, cmd_name):
        return self._hooks_registry.retrieve_post_hooks(cmd_name)