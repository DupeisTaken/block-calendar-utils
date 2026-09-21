"""Sequential inspect/write/export stages over the existing command services.

Parse every stage before running any of them. Stages commit independently, so a
later failure stops the sequence but never pretends to roll back a completed save.
"""

from .cli_interface import GROUP_ACTIONS, ROOT_COMMANDS, children, normalize, render_help, rows
from .help_style import error_message, write_help
from .models import CalendarError


STAGES = {"--inspect": "inspect", "-i": "inspect", "--write": "write", "-w": "write", "--export": "export", "-e": "export"}
CONTEXT = {"--root", "--profile", "--semester", "-r"}
TARGETS = {token: name for flag, (name, short) in ROOT_COMMANDS.items()
           if name in {"courses", "activities", "semester", "exceptions", "init", "validate"}
           for token in (flag, short) if token and token not in STAGES}
ALLOWED = {
    "inspect": {"courses": {"list", "path"}, "activities": {"list"}, "semester": {"list", "show"}, "exceptions": {"list"}, "preview": {None}, "validate": {None}},
    "write": {"courses": {"edit", "set", "clear", "enable", "disable", "import"}, "activities": {"edit", "set", "clear", "enable", "disable"}, "semester": {"use", "new"}, "exceptions": {"set", "remove"}, "init": {None}},
    "export": {"export": {None}},
}


def starts_workflow(argv):
    """Only a new top-level action selects this grammar; legacy scripts survive."""
    index = 0
    while index < len(argv):
        token = argv[index]
        head, equals, _ = token.partition("=")
        if head in CONTEXT:
            index += 1 if equals else 2
        elif token.startswith("-r") and not token.startswith("--") and len(token) > 2:
            index += 1
        else:
            return head in STAGES
    return False


def split_stages(argv, root):
    """Consume option values before stage markers, and honor literal '--'.

Long flags have one arity across existing parsers. Short option values that do
not begin with a dash cannot be stage markers. Attached values remain opaque.
"""
    arities = {}
    def collect(parser):
        for action in parser._actions:
            for flag in action.option_strings:
                count = 0 if action.nargs == 0 else action.nargs if isinstance(action.nargs, int) else 1
                arities[flag] = max(arities.get(flag, 0), count)
        for child in set(children(parser).values()):
            collect(child)
    collect(root)
    stages, context, index = [], {}, 0
    while index < len(argv):
        token = argv[index]
        head, equals, attached = token.partition("=")
        if token == "--":
            if not stages:
                raise CalendarError("Choose --inspect, --write or --export before literal arguments.")
            stages[-1][1].extend(argv[index:])
            break
        if head in CONTEXT or (token.startswith("-r") and not token.startswith("--") and len(token) > 2):
            flag = "--root" if head == "-r" or token.startswith("-r") and not token.startswith("--") else head
            if head not in CONTEXT:
                value = token[2:]
            elif equals:
                value = attached
            else:
                index += 1
                if index >= len(argv) or argv[index].startswith("-"):
                    raise CalendarError(f"{flag} needs a value. For a value starting with a dash, use {flag}=VALUE.")
                value = argv[index]
            if flag in context and context[flag] != value:
                raise CalendarError(f"Conflicting {flag} values. One workflow uses one data root, profile and semester.")
            context[flag] = value
        elif head in STAGES:
            if equals:
                raise CalendarError(f"{head} starts an action and takes no attached value.")
            stages.append((STAGES[head], []))
        else:
            if not stages:
                raise CalendarError("Start with --inspect, --write or --export.")
            stages[-1][1].append(token)
            if not equals:
                for _ in range(arities.get(head, 0)):
                    if index + 1 >= len(argv) or argv[index + 1].startswith("-") and not argv[index + 1][1:2].isdigit():
                        break
                    index += 1
                    stages[-1][1].append(argv[index])
        index += 1
    prefix = [f"{flag}={value}" for flag, value in context.items()]
    return stages, prefix


def navigation_help(mode, detailed=False):
    heading = "SHBS Calendar / " + mode.title()
    if mode == "inspect":
        items = [("--day DATE[:DATE]", "Preview events for a day or inclusive range"), ("--courses", "List block keys, names and enabled state"), ("--activities", "List club IDs, names and times"), ("--semesters", "List timetables; add --show ID to review one"), ("--exceptions", "List school and personal date rules"), ("--validate --day DATE", "Check events without writing a calendar")]
    else:
        items = [("--courses", "Enter course names; or --set BLOCK NAME"), ("--activities", "Enter club names; or --set ID NAME"), ("--exceptions", "Save closures, blank hours or morning/afternoon cutoffs"), ("--semesters", "Select with --use ID; create with --new ID"), ("--init", "Create missing blank profile files")]
    lines = [heading, "", f"  python -m shbs-calendar --{mode} [target] [options]", ""] + rows(items)
    lines += ["  Add --help or --docs after a target for its arguments.", f"  Example: --{mode} --courses --docs", ""]
    if detailed:
        lines += ["  Actions run left to right. Repeat --inspect, --write or --export to stack.", "  Each write saves before the next action; a failure stops later actions.", "  Completed writes stay saved if a later action fails. Help never runs actions.", "  --root PATH, --profile NAME and --semester ID apply to the whole workflow.", "  Use --week, --exception, --edit and --import in full: -i, -w and -e", "  always start actions in this workflow.", "", '  python -m shbs-calendar -w --courses -e --day 9.18', ""]
    else:
        lines += [f"  More: --{mode} --docs"]
    return "\n".join(lines) + "\n"


def translate(mode, tokens):
    """Map intent + target to one existing handler; no scheduling is duplicated."""
    if mode == "export":
        return ["--export", *tokens]
    target = TARGETS.get(tokens[0]) if tokens else None
    if target is None:
        if mode == "inspect":
            return ["--preview", *tokens]
        raise CalendarError("After --write, choose --courses, --activities, --exceptions, --semesters or --init.")
    rest = tokens[1:]
    flag = "--semesters" if target == "semester" else "--" + target
    actions = GROUP_ACTIONS.get(target, {})
    # The first operation follows the target. An omitted operation means list
    # for inspection or batch entry for editable names, never an inferred save.
    first = rest[0] if rest else None
    explicit = any(first in {"--" + action, short, action} for action, short in actions.items()) if first else False
    default = "list" if mode == "inspect" and target in GROUP_ACTIONS else "edit" if mode == "write" and target in {"courses", "activities"} else None
    if not explicit and default:
        rest = ["--" + default, *rest]
    return [flag, *rest]


def run_workflow(argv, root):
    from .cli import command_settings, exception_changes, main, parser
    import sys

    try:
        stages, context = split_stages(argv, root)
        prepared = []
        for mode, tokens in stages:
            help_only = not tokens or all(t in {"--help", "-h", "--docs"} for t in tokens)
            if help_only and mode != "export":
                write_help(navigation_help(mode, "--docs" in tokens), sys.stdout)
                return 0
            cli = parser()
            # The same parser tree renders the new public route even when the
            # underlying service action still has its compatibility name.
            def mark(node):
                node.navigation_mode = mode
                for child in set(children(node).values()):
                    mark(child)
            mark(cli)
            translated = context + translate(mode, tokens)
            args = cli.parse_args(normalize(translated, cli))
            action = getattr(args, "action", None)
            if mode == "write" and args.command in {"semester", "exceptions"} and action is None:
                write_help(render_help(children(cli)[args.command]), sys.stdout)
                return 0
            if args.command not in ALLOWED[mode] or action not in ALLOWED[mode][args.command]:
                raise CalendarError(f"That operation does not belong to --{mode}. Use --inspect for viewing, --write for saving, or --export for calendars.")
            if args.command == "semester" and action == "use" and getattr(args, "semester", args.id) != args.id:
                raise CalendarError("--semester ID applies to the whole workflow and conflicts with --semesters --use ID. Use the same ID or omit --semester.")
            prepared.append((translated, args, mode))
        # Date mistakes in a later stage must fail before an earlier CSV write.
        for _, args, _ in prepared:
            if args.command in {"export", "preview", "validate"}:
                command_settings(args)
            elif args.command == "exceptions" and args.action != "list":
                exception_changes(args)
        for position, (translated, args, mode) in enumerate(prepared, 1):
            status = main(translated, prepared=args)
            if status:
                if len(prepared) > 1:
                    from .help_style import emit
                    emit(f"\nStopped at action {position} (--{mode}). Later actions did not run; completed writes remain saved.", file=sys.stderr)
                return status
        return 0
    except (CalendarError, ValueError) as exc:
        error_message(exc, "--docs")
        return 2
