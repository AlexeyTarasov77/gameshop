from anyio import run_process


class CommandExecutor:
    async def subprocess_exec(self, *args):
        await run_process(*args)
