"""
Adapted from placeholder template tests. See: https://github.com/sqlfluff/sqlfluff/pull/2107
"""

import pytest

from sqlfluff.core import FluffConfig
from sqlfluff.core.errors import SQLTemplaterError
from sqlfluff_sqlc_postgres.templater import AUTOFILL_PARAMS, SqlcPlaceholderTemplater

def test__templater_raw():
    """Test the templaters when nothing has to be replaced."""
    t = SqlcPlaceholderTemplater(override_context=dict(param_style="sqlc"))
    instr = "SELECT * FROM {{blah}} WHERE %(gnepr)s OR e~':'"
    outstr, _ = t.process(in_str=instr, fname="test")
    assert str(outstr) == instr

@pytest.mark.parametrize(
    "instr, expected_outstr",
    [
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param AND explicit_param = @explicit_param",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['string']} AND explicit_param = explicit_param",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param IS @missing_param::boolean",
            f"SELECT bla FROM blob WHERE missing_param IS {AUTOFILL_PARAMS['boolean']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::integer",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['integer']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::float",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['float']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::date",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['date']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::integer[]",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['integer_array']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::text[]",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['text_array']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::boolean[]",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['boolean_array']}",
        ),
        (
            "SELECT bla FROM blob WHERE missing_param = @missing_param::float[]",
            f"SELECT bla FROM blob WHERE missing_param = {AUTOFILL_PARAMS['float_array']}",
        ),
    ],
    ids=[
        "ignore_explicit_param_and_autofill_missing_untyped_param",
        "autofill_missing_params_boolean",
        "autofill_missing_params_integer",
        "autofill_missing_params_float",
        "autofill_missing_params_date",
        "autofill_missing_params_integer_array",
        "autofill_missing_params_string_array",
        "autofill_missing_params_boolean_array",
        "autofill_missing_params_float_array",
    ],
)
def test__templater_custom_regex_autofill_params_parametrized(instr, expected_outstr):
    """Test custom regex param autofill."""
    t = SqlcPlaceholderTemplater(
        override_context=dict(
            param_style="sqlc",
            autofill_missing_params=True,
            explicit_param="explicit_param",
        )
    )
    outstr, _ = t.process(
        in_str=instr,
        fname="test",
        config=FluffConfig(),
    )
    assert str(outstr) == expected_outstr


def test__templater_exception():
    """Test the exception raised when variables are missing."""
    t = SqlcPlaceholderTemplater(override_context=dict(param_style="sqlc"))
    instr = "SELECT name FROM table WHERE user_id = @user_id"
    with pytest.raises(
        SQLTemplaterError, match=r"Failure in placeholder templating: 'user_id'"
    ):
        t.process(in_str=instr, fname="test")


def test__templater_setup():
    """Test the exception raised when config is incomplete or ambiguous."""
    t = SqlcPlaceholderTemplater(override_context=dict(name="'john'"))
    with pytest.raises(
        ValueError,
        match=r"No param_regex nor param_style was provided to the placeholder templater",
    ):
        t.process(in_str="SELECT 2+2", fname="test")

    t = SqlcPlaceholderTemplater(
        override_context=dict(param_style="bla", param_regex="bli")
    )
    with pytest.raises(
        ValueError,
        match=r"Either param_style or param_regex must be provided, not both",
    ):
        t.process(in_str="SELECT 2+2", fname="test")


def test__templater_styles():
    """Test the exception raised when parameter style is unknown."""
    t = SqlcPlaceholderTemplater(override_context=dict(param_style="pperccent"))
    with pytest.raises(ValueError, match=r"Unknown param_style"):
        t.process(in_str="SELECT 2+2", fname="test")
