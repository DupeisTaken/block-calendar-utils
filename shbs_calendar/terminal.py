"""Plain-text day columns that fit a terminal, including wide Unicode text."""

import unicodedata


def display_width(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)


def wrap_line(text, width):
    """Wrap without truncation; prefer spaces but allow long unbroken names."""
    result = []
    while display_width(text) > width:
        used, stop = 0, 0
        for i, char in enumerate(text):
            size = display_width(char)
            if used + size > width:
                break
            used, stop = used + size, i + 1
        space = text.rfind(" ", 0, stop + 1)
        cut = space if space > width // 3 else stop
        result.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return result + [text]


def day_columns(preview, header, width):
    """Place successive days across each row, never mixing calendar weeks."""
    columns = min(3, max(1, (width + 4) // 40))
    cell_width = (width - 4 * (columns - 1)) // columns
    lines = [part for line in header for part in wrap_line(line, width)]
    groups = {}
    for event in preview.events:
        groups.setdefault(event.start.date(), []).append(event)
    weeks = {}
    for day, events in groups.items():
        panel = wrap_line(day.strftime("%A, %d %B %Y"), cell_width)
        panel.append("─" * cell_width)
        for event in events:
            title = " ".join(event.title.split())
            place = f" · {' '.join(event.location.split())}" if event.location else ""
            text = f"{event.start:%H:%M}–{event.end:%H:%M}  {event.block}  {title}{place}"
            wrapped = wrap_line(text, cell_width - 2)
            panel.extend([wrapped[0], *("  " + part for part in wrapped[1:])])
        weeks.setdefault(day.isocalendar()[:2], []).append(panel)
    for panels in weeks.values():
        for offset in range(0, len(panels), columns):
            row = panels[offset:offset + columns]
            lines.append("")
            for i in range(max(map(len, row))):
                cells = [panel[i] if i < len(panel) else "" for panel in row]
                lines.append("    ".join(cell + " " * (cell_width - display_width(cell)) for cell in cells).rstrip())
    if not preview.events:
        lines += ["", *wrap_line("No events in this range. Check course selections and date exceptions.", width)]
    return "\n".join(lines)
