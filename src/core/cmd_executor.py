from anyio import run_process


class CommandExecutor:
    async def subprocess_exec(self, cmd: str):
        await run_process(cmd)
