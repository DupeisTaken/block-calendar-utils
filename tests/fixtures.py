"""Opt-in synthetic test semesters; never read a user's installed timetables."""

from dataclasses import replace

from bcutils.app import Workspace
from bcutils.semesters import TEMPLATE_ROOT, create_semester
from bcutils.storage import load_semester


def install_example(root):
    return create_semester(Workspace(root), "2026-27-s1", template="shbs-example")


def example_semester():
    # Retain the historical fixture identity for UID regression checks.
    return replace(load_semester(TEMPLATE_ROOT / "shbs-example"), id="2026-27-s1")
