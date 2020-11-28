from datasette.app import Datasette
import pytest
import re
import shutil
import textwrap


@pytest.fixture(scope="session")
def datasette(tmp_path_factory):
    root = tmp_path_factory.mktemp("root")
    src = root / "src"
    src.mkdir()
    (src / "one.txt").write_text("Hello\nThere\nThis\nIs a test file")
    (src / "sub").mkdir()
    (src / "sub/two.txt").write_text("Second test file")
    (src / "{{curlies}}.txt").write_text("File with curlies in the name -v")
    return Datasette(
        [],
        memory=True,
        metadata={
            "plugins": {
                "datasette-ripgrep": {
                    "path": str(src),
                }
            }
        },
    )


@pytest.mark.asyncio
async def test_plugin_is_installed(datasette):
    response = await datasette.client.get("/-/plugins.json")
    assert 200 == response.status_code
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-ripgrep" in installed_plugins


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("rg"), reason="rg executable not found")
async def test_ripgrep_search(datasette):
    response = await datasette.client.get("/-/ripgrep?pattern=est")
    assert "<title>ripgrep: est</title>" in response.text
    html = re.sub(r"(\s+\n)+", "\n", response.text)
    assert (
        "<h3>one.txt</h3>\n"
        '        <pre><a href="/-/ripgrep/view/one.txt#L4">4   </a> Is a test file</pre>'
    ) in html
    assert (
        "<h3>sub/two.txt</h3>"
        '\n        <pre><a href="/-/ripgrep/view/sub/two.txt#L1">1   </a> Second test file</pre>'
    ) in html


@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("rg"), reason="rg executable not found")
async def test_ripgrep_pattern_not_treated_as_flag(datasette):
    response = await datasette.client.get("/-/ripgrep?pattern=-v")
    assert "<title>ripgrep: -v</title>" in response.text
    html = re.sub(r"(\s+\n)+", "\n", response.text)
    assert (
        "<h3>{{curlies}}.txt</h3>\n"
        '        <pre><a href="/-/ripgrep/view/%7B%7Bcurlies%7D%7D.txt#L1">1   </a> File with curlies in the name -v</pre>'
    ) in html


@pytest.mark.asyncio
async def test_view_file(datasette):
    response = await datasette.client.get("/-/ripgrep/view/one.txt")
    assert "<h1>one.txt</h1>" in response.text
    assert (
        textwrap.dedent(
            """
    <pre><code id="L1" data-line="1">Hello</code>
    <code id="L2" data-line="2">There</code>
    <code id="L3" data-line="3">This</code>
    <code id="L4" data-line="4">Is a test file</code>
    </pre>"""
        )
        in response.text
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,expected_status,expected_message",
    (
        ("three.txt", 404, "File not found: three.txt"),
        ("..%2F..%2F..%2Ftmp%2Fblah.txt", 403, "File must be inside path directory"),
    ),
)
async def test_view_file_errors(datasette, path, expected_status, expected_message):
    response = await datasette.client.get("/-/ripgrep/view/" + path)
    assert response.status_code == expected_status
    assert expected_message in response.text


@pytest.mark.asyncio
async def test_view_file_with_curlies(datasette):
    response = await datasette.client.get("/-/ripgrep/view/%7B%7Bcurlies%7D%7D.txt")
    assert response.status_code == 200
    assert "File with curlies in the name" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata,authenticated,path,expected_status",
    [
        # Deny all access
        ({"allow": False}, False, "/-/ripgrep", 403),
        ({"allow": False}, True, "/-/ripgrep", 403),
        ({"allow": False}, False, "/-/ripgrep/view/one.txt", 403),
        ({"allow": False}, True, "/-/ripgrep/view/one.txt", 403),
        # Allow all access
        ({"allow": True}, False, "/-/ripgrep", 200),
        ({"allow": True}, True, "/-/ripgrep", 200),
        ({"allow": True}, False, "/-/ripgrep/view/one.txt", 200),
        ({"allow": True}, True, "/-/ripgrep/view/one.txt", 200),
        # Allow only to logged in user
        ({"allow": {"id": "user"}}, False, "/-/ripgrep", 403),
        ({"allow": {"id": "user"}}, True, "/-/ripgrep", 200),
        ({"allow": {"id": "user"}}, False, "/-/ripgrep/view/one.txt", 403),
        ({"allow": {"id": "user"}}, True, "/-/ripgrep/view/one.txt", 200),
    ],
)
async def test_permissions(datasette, metadata, authenticated, path, expected_status):
    original = datasette._metadata
    try:
        datasette._metadata = {**datasette._metadata, **metadata}
        cookies = {}
        if authenticated:
            cookies["ds_actor"] = datasette.sign({"a": {"id": "user"}}, "actor")
        response = await datasette.client.get(path, cookies=cookies)
        assert response.status_code == expected_status
    finally:
        datasette._metadata = original
