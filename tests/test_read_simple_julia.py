import pytest
from nbformat.v4.nbbase import new_code_cell, new_markdown_cell, new_notebook

import jupytext
from jupytext.compare import compare, compare_notebooks


def test_read_simple_file(
    julia='''"""
   cube(x)

Compute the cube of `x`, ``x^3``.

# Examples
```jldoctest
julia> cube(2)
8
```
"""
function cube(x)
   x^3
end

cube(x)

# And a markdown comment
''',
):
    nb = jupytext.reads(julia, "jl")
    assert nb.metadata["jupytext"]["main_language"] == "julia"
    assert len(nb.cells) == 3
    assert nb.cells[0].cell_type == "code"
    assert (
        nb.cells[0].source
        == '''"""
   cube(x)

Compute the cube of `x`, ``x^3``.

# Examples
```jldoctest
julia> cube(2)
8
```
"""
function cube(x)
   x^3
end'''
    )
    assert nb.cells[1].cell_type == "code"
    assert nb.cells[1].source == "cube(x)"
    assert nb.cells[2].cell_type == "markdown"
    compare(nb.cells[2].source, "And a markdown comment")

    julia2 = jupytext.writes(nb, "jl")
    compare(julia2, julia)


@pytest.mark.parametrize("format_name", ["light", "percent"])
def test_round_trip_markdown_enum_plus(format_name):
    """This test was extracted from issue #872"""
    nb = new_notebook(cells=[new_markdown_cell("+ item"), new_code_cell("fun(3)")])

    fmt = "jl:" + format_name
    text = jupytext.writes(nb, fmt=fmt)
    nb2 = jupytext.reads(text, fmt=fmt)
    compare_notebooks(nb2, nb)
