from langchain_core.tools import tool as base_tool

import inspect

import app.tools as tools

def tagged_tool(*tags):
    def tool_decorator(fn):
        wrapped = base_tool(fn)
        wrapped.tags = list(tags)
        return wrapped
    return tool_decorator

def get_all_tools():
    # Get all functions that are tools (langchain_core.tools.Tool instances)
    all_tools  = [
        tool_fn for name, tool_fn in inspect.getmembers(tools)
        if hasattr(tool_fn, "tags")
    ]
    return all_tools

def get_tools_by_tag(tag: str):
    return [tool_fn for tool_fn in get_all_tools() if tag in tool_fn.tags]

def get_tools_by_tags(*tags):
    return [tool_fn for tool_fn in get_all_tools() if all(tag in tool_fn.tags for tag in tags)]