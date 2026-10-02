"""``python -m ndxplorer`` (and the ``ndxplorer`` / ``ndxplorer-gui`` scripts).

Without a subcommand this opens ndX: the emtk app (:mod:`ndxplorer.app`) in a
native window (:func:`ndxplorer.app.launch.run`). No Qt is imported. The
subcommands ``filter`` and ``image`` are the headless CLI (:mod:`ndxplorer.cli`).
A browser runs the same app through ``python -m ndxplorer.app.web``.
"""

import click

from .logging_config import logging


class MutuallyExclusiveOption(click.Option):
    """Custom option class to enforce mutual exclusivity"""

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.mutually_exclusive:
            for other_name in self.mutually_exclusive:
                if other_name in opts and opts[other_name] is not None and self.name in opts and opts[self.name] is not None:
                    raise click.ClickException(f"Option --{self.name} is mutually exclusive with --{other_name}.")
        return super().handle_parse_result(ctx, opts, args)


@click.group(invoke_without_command=True)
@click.option('--file', '-f', type=click.Path(exists=True), cls=MutuallyExclusiveOption,
              mutually_exclusive=['folder'], help='Open specific file (.bur, .csv, etc.)')
@click.option('--folder', '-d', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              cls=MutuallyExclusiveOption, mutually_exclusive=['file'],
              help='Open folder containing data files')
@click.option('--chisurf-rpc', type=str, default=None,
              help='Connect to a ChiSurf RPC server at host:port for the "Send selection to" '
                   'menu (e.g. 127.0.0.1:8765).')
@click.option('--verbose', '-v', is_flag=True, help='Enable info logging (default is warnings only)')
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--host', type=click.Choice(['native', 'tk']), default=None,
              help='Window: native (wgpu + glfw, the default when available) or tk.')
@click.option('--size', 'size', type=str, default=None, metavar='WxH',
              help='Window size in logical pixels, e.g. 992x593 (default 900x600).')
@click.pass_context
def main(ctx, file, folder, chisurf_rpc, verbose, debug, host, size):
    """ndX - Fluorescence Data Explorer

    Examples:
      # Open with specific folder
      ndxplorer --folder "path/to/burstwise_All 0.1500#30"

      # Open with specific file
      ndxplorer --file "data.bur"

      # Open empty application
      ndxplorer
    """
    if ctx.invoked_subcommand is not None:
        # A subcommand (filter, image) was invoked, let click handle it
        return

    # Set up logging level. WARNING by default -- ndX logs INFO on every plot
    # update and file operation, which is noise during normal use.
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug logging enabled")
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)

    from .app.launch import parse_size, run

    try:
        window_size = parse_size(size)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint='--size')
    raise SystemExit(run(path=file or folder, host=host, chisurf_rpc=chisurf_rpc,
                         size=window_size))


# Register subcommands from cli.py
from .cli import filter_cmd, image_cmd  # noqa: E402

main.add_command(filter_cmd, name="filter")
main.add_command(image_cmd, name="image")


if __name__ == "__main__":
    main()
