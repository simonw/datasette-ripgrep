from datasette import hookimpl
from datasette.utils.asgi import Response
import asyncio
import json


async def run_ripgrep(pattern, path):
    proc = await asyncio.create_subprocess_exec(
        "rg",
        pattern,
        path,
        "--json",
        stdout=asyncio.subprocess.PIPE,
    )
    max_lines = 1000
    results = []
    num_results = 0
    while True:
        try:
            line = await proc.stdout.readline()
            if line:
                results.append(json.loads(line))
                num_results += 1
                if num_results >= max_lines:
                    break
            else:
                break
        except (asyncio.exceptions.LimitOverrunError, ValueError):
            # This exception is thrown at the end of the loop
            break
    proc.terminate()
    return results


async def ripgrep(request, datasette):
    pattern = (request.args.get("pattern") or "").strip()
    config = datasette.plugin_config("datasette-ripgrep") or {}
    path = config.get("path")
    if not path:
        return Response.html("The path plugin configuration is required.", status=500)
    results = []
    if pattern:
        results = await run_ripgrep(pattern, path)
    return Response.html(
        await datasette.render_template(
            "ripgrep.html",
            {
                "pattern": pattern,
                "results": results,
            },
        )
    )


@hookimpl
def register_routes():
    return (("/-/ripgrep", ripgrep),)
