from datasette import hookimpl
from datasette.utils.asgi import Response, Forbidden
import asyncio
import json
from pathlib import Path
import urllib


async def run_ripgrep(
    pattern,
    path,
    globs=None,
    time_limit=1.0,
    max_lines=2000,
    ignore=False,
    literal=False,
    context=2,
):
    args = ["-e", pattern, path, "--json"]
    if context:
        args.extend(["-C", str(context)])
    if ignore:
        args.append("-i")
    if literal:
        args.append("-F")
    if globs:
        for glob in globs:
            args.extend(["--glob", glob])
    proc = await asyncio.create_subprocess_exec(
        "rg",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        limit=1024 * 1024,
        cwd=path,
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
    await check_permission(request, datasette)
    pattern = (request.args.get("pattern") or "").strip()
    ignore = request.args.get("ignore")
    literal = request.args.get("literal")
    globs = [g.strip() for g in request.args.getlist("glob") if g.strip()]

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
            pattern,
            path,
            globs=globs,
            time_limit=time_limit,
            max_lines=max_lines,
            ignore=ignore,
            literal=literal,
        )

    def fix_path(path_):
        return str(Path(path_).relative_to(path))

    try:
        widest_line_number = len(
            str(
                max(
                    result["data"]["line_number"]
                    for result in results
                    if "line_number" in result["data"]
                )
            )
        )
    except ValueError:
        # max() arg is an empty sequence
        widest_line_number = 1

    return Response.html(
        await datasette.render_template(
            "ripgrep.html",
            {
                "pattern": pattern,
                "results": results,
                "fix_path": fix_path,
                "time_limit_hit": time_limit_hit,
                "url_quote": urllib.parse.quote,
                "literal": literal,
                "ignore": ignore,
                "globs": globs,
                "widest_line_number": widest_line_number,
            },
        )
    )


async def view_file(request, datasette):
    await check_permission(request, datasette)
    config = datasette.plugin_config("datasette-ripgrep") or {}
    subpath = urllib.parse.unquote(request.url_vars["subpath"])
    path = config.get("path")
    if not path:
        return Response.html("The path plugin configuration is required.", status=500)
    filepath = Path(path) / subpath
    filepath = filepath.resolve()
    # Make absolutely sure it's still inside the root
    if not str(filepath).startswith(str(path)):
        return Response.html("File must be inside path directory", status=403)
    if not filepath.exists():
        return Response.text("File not found: {}".format(subpath), status=404)
    lines = filepath.read_text().split("\n")
    widest_line_number = len(str(len(lines) + 1))
    return Response.html(
        await datasette.render_template(
            "ripgrep_view_file.html",
            {
                "subpath": subpath,
                "lines": enumerate(lines),
                "widest_line_number": widest_line_number,
            },
        )
    )


async def check_permission(request, datasette):
    if (
        await datasette.permission_allowed(
            request.actor,
            "view-instance",
            default=None,
        )
    ) is False:
        raise Forbidden("view-instance denied")


@hookimpl
def register_routes():
    return (
        ("^/-/ripgrep$", ripgrep),
        ("^/-/ripgrep/view/(?P<subpath>.*)$", view_file),
    )


@hookimpl
def menu_links(datasette, actor):
    return [
        {"href": datasette.urls.path("/-/ripgrep"), "label": "ripgrep search"},
    ]
