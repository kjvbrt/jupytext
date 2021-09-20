import pytest
from git.exc import HookExecutionError
from pre_commit.main import main as pre_commit

from jupytext import read

from .utils import (
    skip_pre_commit_tests_on_windows,
    skip_pre_commit_tests_when_jupytext_folder_is_not_a_git_repo,
)


@skip_pre_commit_tests_on_windows
@skip_pre_commit_tests_when_jupytext_folder_is_not_a_git_repo
def test_pre_commit_hook_sync_in_distinct_folder(
    tmpdir,
    cwd_tmpdir,
    tmp_repo,
    jupytext_repo_root,
    jupytext_repo_rev,
    python_notebook,
):
    """
    In this test we sync (and execute) notebooks in a 'script' subfolder to a paired 'notebook' folder
    Cf. https://github.com/mwouts/jupytext/issues/851
    """

    # We set the pairing information in a Jupytext config file:
    tmpdir.join("jupytext.toml").write(
        """
formats="scripts///py:percent,notebooks///ipynb"

# Without this, the script gets a header when we do '--execute'
# (MW: ideally I'd prefer --sync --execute to work without this)
notebook_metadata_filter="-all"
"""
    )

    # Then for the pre-commit configuration we use '--sync --execute'
    pre_commit_config_yaml = f"""
repos:
- repo: {jupytext_repo_root}
  rev: {jupytext_repo_rev}
  hooks:
  - id: jupytext
    args: [--sync, --execute]
    files: ^scripts/
    types: [python]
    additional_dependencies:
    -   nbconvert
    -   ipykernel
"""
    tmpdir.join(".pre-commit-config.yaml").write(pre_commit_config_yaml)

    tmp_repo.git.add(".pre-commit-config.yaml")
    pre_commit(["install", "--install-hooks", "-f"])

    # write a test script

    # MW: the final blank line in test.py is mandatory,
    # otherwise --sync --execute will add it and cause a conflict
    tmpdir.mkdir("scripts").join("test.py").write("# %%\n1 + 2\n")

    # try to commit it, should fail because the ipynb version hasn't been added
    tmp_repo.git.add("scripts/test.py")
    with pytest.raises(
        HookExecutionError,
        match="git add notebooks/test.ipynb",
    ):
        tmp_repo.index.commit("failing")

    # add the ipynb file, now the commit will succeed
    tmp_repo.git.add("notebooks/test.ipynb")
    tmp_repo.index.commit("passing")

    nb = read(tmpdir.join("notebooks").join("test.ipynb"))
    (cell,) = nb.cells
    assert cell.source == "1 + 2"
    assert cell.outputs[0]["data"]["text/plain"] == "3"
