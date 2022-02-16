import pytest
from git.exc import HookExecutionError
from nbformat.v4.nbbase import new_markdown_cell
from pre_commit.main import main as pre_commit

from jupytext import read, write

from .utils import (
    skip_pre_commit_tests_on_windows,
    skip_pre_commit_tests_when_jupytext_folder_is_not_a_git_repo,
)


@skip_pre_commit_tests_on_windows
@skip_pre_commit_tests_when_jupytext_folder_is_not_a_git_repo
def test_pre_commit_hook_sync_notebook_with_no_cell_ids(
    tmpdir,
    cwd_tmpdir,
    tmp_repo,
    jupytext_repo_root,
    jupytext_repo_rev,
    python_notebook,
):
    pre_commit_config_yaml = f"""
repos:
- repo: {jupytext_repo_root}
  rev: {jupytext_repo_rev}
  hooks:
  - id: jupytext
    args: [--sync, --set-formats, 'ipynb,py:percent', --show-changes]
    additional_dependencies:
      - 'nbformat<=5.0.8'
"""
    tmpdir.join(".pre-commit-config.yaml").write(pre_commit_config_yaml)

    tmp_repo.git.add(".pre-commit-config.yaml")
    pre_commit(["install", "--install-hooks", "-f"])

    # write a test notebook and sync it to py:percent
    nb = python_notebook
    write(nb, "test.ipynb")

    # At this stage, the notebook has cell ids on disk
    assert "id" in (tmpdir / "test.ipynb").read()

    # try to commit it, should fail because
    # 1. the hook will create the py version
    # 2. and remove the cell ids from the ipynb notebook

    # TODO: the cell ids are not removed at this point???
    tmp_repo.git.add("test.ipynb")
    with pytest.raises(
        HookExecutionError,
        match="git add test.py",
    ):
        tmp_repo.index.commit("failing")

    # The pre-commit hook removed the cell ids
    # because of the constraint on nbformat
    assert "id" not in (tmpdir / "test.ipynb").read()
    tmp_repo.git.add("test.ipynb")

    # It also created the paired py file
    tmp_repo.git.add("test.py")
    tmp_repo.index.commit("passing")
    assert "test.ipynb" in tmp_repo.tree()
    assert "test.py" in tmp_repo.tree()

    # modify the ipynb file
    nb = read("test.ipynb")
    nb.cells.append(new_markdown_cell("A new cell"))
    write(nb, "test.ipynb")

    tmp_repo.git.add("test.ipynb")

    # We try to commit one more time, this updates the py file
    with pytest.raises(
        HookExecutionError,
        match="files were modified by this hook",
    ):
        tmp_repo.index.commit("failing")

    # the text file has been updated
    assert "A new cell" in tmpdir.join("test.py").read()

    # trying to commit should fail again because we forgot to add the .py version
    with pytest.raises(HookExecutionError, match="git add test.py"):
        tmp_repo.index.commit("still failing")

    nb = read("test.ipynb")
    assert len(nb.cells) == 2

    # add the text file, now the commit will succeed
    tmp_repo.git.add("test.py")
    tmp_repo.index.commit("passing")

    # Now we remove the requirement for nbformat<=5.0.8 i.e.
    # we introduce the cell ids
    pre_commit_config_yaml = f"""
    repos:
    - repo: {jupytext_repo_root}
      rev: {jupytext_repo_rev}
      hooks:
      - id: jupytext
        args: [--sync, --set-formats, 'ipynb,py:percent', --show-changes]
    """
    tmpdir.join(".pre-commit-config.yaml").write(pre_commit_config_yaml)

    # TODO: what do we get when we run 'pre-commit run --all'?
    status = pre_commit(["run", "--all"])
    assert status == 0

    # Cell ids have been added
    assert "id" in (tmpdir / "test.ipynb").read()

    # Only the ipynb file has changed, so we just add and commit that one
    tmp_repo.git.add("test.ipynb")
    tmp_repo.index.commit("passing")
