from pathlib import Path
from typing import Any

import yaml


def get_test_data_path() -> Path:
    """Returns the parent directory of testing data."""
    return Path(__file__).parent.resolve() / "data"


def make_arguments(*arguments: Any) -> str:
    """Converts values into a command line arguments."""
    return " ".join(arguments)


def make_options(key: str, *options: Any) -> str:
    """Converts a key and values into a command line options."""
    return " ".join(f"--{key} {option}" for option in options)


def make_configuration_file(path: Path, **kwargs) -> None:
    with path.open("wt") as file:
        contents = {key: value for key, value in kwargs.items() if value}
        yaml.dump(contents, file)
