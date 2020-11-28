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
    (src / "two.txt").write_text("Second test file")
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
    html = re.sub(r"(\s+\n)+", "\n", response.text)
    assert "<h3>one.txt</h3>\n        <pre>4    Is a test file</pre>" in html
    assert "<h3>two.txt</h3>\n        <pre>1    Second test file</pre>" in html
