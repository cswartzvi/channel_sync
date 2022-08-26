# import pathlib
# import subprocess

# from click.testing import CliRunner

# from conda_local.adapters.channel import CondaChannel
# from conda_local.adapters.channel import LocalCondaChannel
# from conda_local.cli import update


# # @pytest.mark.slow
# def test_update(runner: CliRunner, tmp_path: pathlib.Path):
#     channel = CondaChannel("conda-forge")
#     directory = tmp_path / "channel"
#     directory.mkdir(parents=True, exist_ok=True)
#     target = LocalCondaChannel(directory)

#     parameters = _update_parameters(
#         channel,
#         ["python=3.8.12", "pydantic"],
#         exclusions=[],
#         disposables=[],
#         subdirs=["noarch", "win-64"],
#         target=target,
#     )
#     runner.invoke(update, parameters)

#     venv = (directory / "venv").resolve()
#     result = subprocess.run(
#         ["conda", "create", "-p", str(venv), "python=3.8.12", "pydantic"],
#         capture_output=True,
#     )
#     assert not result.returncode, "Error creating conda environment"

#     result = subprocess.run(
#         [
#             "conda",
#             "run",
#             "-p",
#             str(venv),
#             "python",
#             "-c",
#             "import pydantic",
#         ],
#         capture_output=True,
#     )
#     assert not result.returncode, "Cannot import module pydantic"

#     result = subprocess.run(
#         [
#             "conda",
#             "run",
#             "-p",
#             str(venv),
#             "python",
#             "-c",
#             "import sys;print(sys.version.startswith('3.8.12'))",
#         ],
#         capture_output=True,
#     )
#     assert not result.returncode, "Error getting python version"
#     assert result.stdout.strip() == b"True", "Incorrect python version"
