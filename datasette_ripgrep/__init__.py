from datasette import hookimpl
from datasette.utils.asgi import Response
import asyncio
import json
from pathlib import Path


async def run_ripgrep(pattern, path, time_limit=1.0, max_lines=2000):
    proc = await asyncio.create_subprocess_exec(
        "rg",
        pattern,
        path,
        "--json",
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        limit=1024 * 1024,
    )
    max_lines_hit = False
    time_limit_hit = False
    results = []

    async def inner(results):
        nonlocal max_lines_hit
        while True:
            try:
                line = await proc.stdout.readline()
            except (asyncio.exceptions.LimitOverrunError, ValueError):
                # Skip 'Separator is not found, and chunk exceed the limit' lines
                continue
            if line == b"":
                break
            try:
                results.append(json.loads(line))
            except json.decoder.JSONDecodeError:
                # Usually this means a really long line which was
                # truncated as invalid JSON
                print(line)
            if len(results) >= max_lines:
                max_lines_hit = True
                break

    results = []

    try:
        await asyncio.wait_for(inner(results), timeout=time_limit)
    except asyncio.TimeoutError:
        time_limit_hit = True
    try:
        proc.kill()
    except OSError:
        # Ignore 'no such process' error
        pass
    # We should have accumulated some results anyway
    return results, time_limit_hit


async def ripgrep(request, datasette):
    pattern = (request.args.get("pattern") or "").strip()
    config = datasette.plugin_config("datasette-ripgrep") or {}
    time_limit = config.get("time_limit") or 1.0
    max_lines = config.get("max_lines") or 2000
    path = config.get("path")
    if not path:
        return Response.html("The path plugin configuration is required.", status=500)
    results = []
    time_limit_hit = False
    if pattern:
        results, time_limit_hit = await run_ripgrep(
            pattern, path, time_limit=time_limit, max_lines=max_lines
        )

    def fix_path(path_):
        return Path(path_).relative_to(path)

    return Response.html(
        await datasette.render_template(
            "ripgrep.html",
            {
                "pattern": pattern,
                "results": results,
                "fix_path": fix_path,
                "time_limit_hit": time_limit_hit,
            },
        )
    )


@hookimpl
def register_routes():
    return (("/-/ripgrep", ripgrep),)
