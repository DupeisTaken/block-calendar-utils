"""Quiet terminal presentation; layout is always computed without ANSI codes."""

import argparse
from contextlib import contextmanager
import os
import re
import sys
import textwrap


class SpacedHelpFormatter(argparse.HelpFormatter):
    """Separate entries and preserve paragraph breaks while still wrapping text."""

    def _format_action(self, action):
        return super()._format_action(action).rstrip() + "\n\n"

    def _fill_text(self, text, width, indent):
        return "\n".join(textwrap.fill(line, width, initial_indent=indent, subsequent_indent=indent) if line else "" for line in text.splitlines())


@contextmanager
def windows_vt(stream):
    """Enable ANSI only on a real Windows console, restoring its previous mode."""
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetConsoleMode.restype = wintypes.BOOL
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.SetConsoleMode.restype = wintypes.BOOL
    try:
        handle = msvcrt.get_osfhandle(stream.fileno())
    except (AttributeError, OSError, ValueError):
        yield False
        return
    mode = wintypes.DWORD()
    if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
        yield False
        return
    changed = not mode.value & 4  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    enabled = not changed or bool(kernel.SetConsoleMode(handle, mode.value | 4))
    try:
        yield enabled
    finally:
        if changed and enabled:
            kernel.SetConsoleMode(handle, mode.value)


@contextmanager
def terminal_color(stream):
    """Pipes, NO_COLOR and basic terminals always receive clean plain text."""
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not getattr(stream, "isatty", lambda: False)():
        yield False
    elif os.name == "nt":
        with windows_vt(stream) as enabled:
            yield enabled
    else:
        yield True


def style_help(text):
    """Shared emphasis across help, prompts, results, lists and previews.

    Actions/flags, dates and clock values use one accent everywhere. Headings
    carry weight, never extra colors, boxes, icons or animated decoration.
    """
    result = []
    for line in text.splitlines(keepends=True):
        if line.startswith("SHBS Calendar") or line.rstrip() in {"Start here", "Actions", "Shortcuts", "Courses", "Activities", "Exceptions", "Semesters"}:
            line = "\033[1m" + line.rstrip("\n") + "\033[0m\n"
        elif heading := re.match(r"^([A-Za-z][A-Za-z /?&-]{0,28}:)(.*)", line):
            line = f"\033[1m{heading[1]}\033[0m{line[len(heading[1]):]}"
        elif line.startswith("First time using?"):
            line = line.replace("First time using?", "\033[1mFirst time using?\033[0m", 1)
        # Color only real flag tokens, never the hyphens inside module names,
        # date values or explanatory words. Style after layout to keep alignment.
        line = re.sub(r"(?<![\w-])(?:--?[A-Za-z][A-Za-z-]*(?![\w-])|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}:[0-9]{2})(?![\w])", lambda m: f"\033[36m{m[0]}\033[0m", line)
        if match := re.match(r"(\s*)(Saved[^:\n]*:|Exported|Valid:|Using|Error:|Cancelled\.)", line):
            start, end = match.span(2)
            line = line[:start] + "\033[1m" + line[start:end] + "\033[0m" + line[end:]
        result.append(line)
    return "".join(result)


def write_help(text, stream):
    with terminal_color(stream) as enabled:
        stream.write(style_help(text) if enabled else text)
        # Flush before restoring Windows console mode so escapes are consumed.
        stream.flush()


def emit(*values, sep=" ", end="\n", file=None):
    """A single presentation boundary for all CLI output; exports stay untouched."""
    write_help(sep.join(str(value) for value in values) + end, file if file is not None else sys.stdout)


def ask(prompt):
    """Keep input and output styling consistent, including NO_COLOR and pipes."""
    with terminal_color(sys.stdout) as enabled:
        return input(style_help(prompt) if enabled else prompt)


def error_message(message, more="--docs", stream=None):
    """A concise failure, a correction when useful, and one documentation route."""
    text = str(message)
    date_hint = "Use YYYY-MM-DD" in text or "Unrecognized or ambiguous date range" in text
    if date_hint:
        text = text.split(". Use ", 1)[0].rstrip(".") + "."
    # Keep corrections separate from the failure, instead of flattening the
    # parser's diagnostic and its examples into one dense paragraph.
    paragraphs = text.splitlines() or [""]
    lines = textwrap.wrap(paragraphs[0], width=84, initial_indent="Error: ", subsequent_indent="  ")
    for paragraph in paragraphs[1:]:
        lines += [""] + textwrap.wrap(paragraph, width=84, initial_indent="  ", subsequent_indent="  ")
    if date_hint:
        lines += ["", "  Dates: YYYY-MM-DD or MMDD · Range: --day 9.14:9.18"]
    lines += ["", "  More: " + more.strip()]
    emit("\n".join(lines), file=stream if stream is not None else sys.stderr)
