import click.testing
import pytest


@pytest.fixture(scope="session")
def runner():
    return click.testing.CliRunner()
