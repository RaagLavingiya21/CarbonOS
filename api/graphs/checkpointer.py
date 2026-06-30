"""Shared LangGraph checkpointer — PostgresSaver when DATABASE_URL is set."""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from db.database_url import get_database_url

load_dotenv()

_checkpointer: Any = None
_exit_stack = ExitStack()


def get_checkpointer():
    """Return a LangGraph checkpointer backed by Supabase Postgres when configured."""
    global _checkpointer
    if _checkpointer is None:
        db_url = get_database_url()
        if db_url:
            from langgraph.checkpoint.postgres import PostgresSaver

            saver = _exit_stack.enter_context(PostgresSaver.from_conn_string(db_url))
            saver.setup()
            _checkpointer = saver
        else:
            _checkpointer = MemorySaver()
    return _checkpointer
