from click.testing import CliRunner

from .cli import main


def test_main():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
