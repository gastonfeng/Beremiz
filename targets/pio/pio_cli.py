import asyncio
import os
import sys
from functools import partial
from io import StringIO
from os.path import isfile
from threading import Thread

import click
from click import Context, Command
from syncasync import sync_to_async

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(os.path.join(application_path, 'platformio-core'))
from platformio import app, fs, exception
from platformio.commands.run.command import process_env, print_processing_summary
from platformio.commands.run.helpers import clean_build_dir, handle_legacy_libdeps
from platformio.project.config import ProjectConfig
from platformio.project.helpers import find_project_dir_above


def call_click_command(cmd, *args, **kwargs):
    """ Wrapper to call a click command

    :param cmd: click cli command function to call
    :param args: arguments to pass to the function
    :param kwargs: keywrod arguments to pass to the function
    :return: None
    """

    # Get positional arguments from args
    arg_values = {c.name: a for a, c in zip(args, cmd.params)}
    args_needed = {c.name: c for c in cmd.params
                   if c.name not in arg_values}

    # build and check opts list from kwargs
    opts = {a.name: a for a in cmd.params if isinstance(a, click.Option)}
    for name in kwargs:
        if name in opts:
            arg_values[name] = kwargs[name]
        else:
            if name in args_needed:
                arg_values[name] = kwargs[name]
                del args_needed[name]
            else:
                raise click.BadParameter(
                    "Unknown keyword argument '{}'".format(name))

    # check positional arguments list
    for arg in (a for a in cmd.params if isinstance(a, click.Argument)):
        if arg.name not in arg_values:
            raise click.BadParameter("Missing required positional"
                                     "parameter '{}'".format(arg.name))

    # build parameter lists
    opts_list = sum(
        [[o.opts[0], str(arg_values[n])] for n, o in opts.items()], [])
    args_list = [str(v) for n, v in arg_values.items() if n not in opts]

    # call the command
    cmd(opts_list + args_list)


class MyStringIO(StringIO):
    def __init__(self, queue, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.queue = queue

    def flush(self):
        val = self.getvalue()
        self.queue.put(('std', val.strip(' \t\r\n\0')))
        self.truncate(0)


class MyStringIOERR(StringIO):
    def __init__(self, queue, *args, **kwargs):
        StringIO.__init__(self, *args, **kwargs)
        self.queue = queue

    def flush(self):
        val = self.getvalue()
        self.queue.put(('err', val.strip(' \t\r\n\0')))
        self.truncate(0)


async def run(
        queue,
        ctx=Context(Command('run')),
        environment='',
        target=[],
        upload_port='',
        project_dir='.',
        project_conf='./platformio.ini',
        jobs=8,
        silent='',
        verbose='',
        disable_auto_clean='',
):
    saveStdout, saveStderr = sys.stdout, sys.stderr
    sys.stderr = MyStringIOERR(queue)
    sys.stdout = MyStringIO(queue)
    # sys.stderr,sys.stdout=logger,logger
    app.set_session_var("custom_project_conf", project_conf)

    # find project directory on upper level
    if isfile(project_dir):
        project_dir = find_project_dir_above(project_dir)

    is_test_running = False  # CTX_META_TEST_IS_RUNNING in ctx.meta

    with fs.cd(project_dir):
        config = ProjectConfig.get_instance(project_conf)
        config.validate(environment)

        # clean obsolete build dir
        if not disable_auto_clean:
            build_dir = config.get_optional_dir("build")
            try:
                clean_build_dir(build_dir, config)
            except:  # pylint: disable=bare-except
                click.secho(
                    "Can not remove temporary directory `%s`. Please remove "
                    "it manually to avoid build issues" % build_dir,
                    fg="yellow",
                )

        handle_legacy_libdeps(project_dir, config)

        default_envs = config.default_envs()
        results = []
        for env in config.envs():
            skipenv = any(
                [
                    environment and env not in environment,
                    not environment and default_envs and env not in default_envs,
                ]
            )
            if skipenv:
                results.append({"env": env})
                continue

            # print empty line between multi environment project
            if not silent and any(r.get("succeeded") is not None for r in results):
                click.echo()

            results.append(
                process_env(
                    ctx,
                    env,
                    config,
                    environment,
                    target,
                    upload_port,
                    silent,
                    verbose,
                    jobs,
                    is_test_running,
                )
            )

        command_failed = any(r.get("succeeded") is False for r in results)

        if not is_test_running and (command_failed or not silent) and len(results) > 1:
            print_processing_summary(results)
        # sys.stdout,sys.stderr=saveStdout,saveStderr
        queue.put("QUIT")
        if command_failed:
            raise exception.ReturnErrorCode(1)
        return True


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def shutdown(loop):
    loop.stop()


async def run_async(q):
    new_loop = asyncio.new_event_loop()
    t = Thread(target=start_loop, args=(new_loop,), name='pio_loop')
    t.start()

    future = asyncio.run_coroutine_threadsafe(run(q), new_loop)
    res = await sync_to_async(future.result)()
    new_loop.call_soon_threadsafe(partial(shutdown, new_loop))
    return res


if __name__ == '__main__':
    run()
