"""Defines the hook endpoints for the dbt templater plugin."""

from sqlfluff_sqlc_postgres.templater import SqlcPlaceholderTemplater
from sqlfluff.core.plugin import hookimpl


@hookimpl
def get_templaters():
    """Get templaters."""
    
    return [SqlcPlaceholderTemplater]

