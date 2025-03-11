from pathlib import Path
from string import Template
import aiofiles


async def parse(template_name: str, **kwargs) -> str:
    """Parses html file under provided path
    with variables substitution using python's builtin Template"""
    async with aiofiles.open(Path(__file__).parent / "html" / template_name) as f:
        contents = await f.read()
    s = Template(contents)
    return s.substitute(kwargs)
