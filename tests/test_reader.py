"""The CPU reader, and the two ways it was wrong before anyone looked.

A reader that drops the word "no" is worse than no reader at all: a missed finding makes the
record look thinner and the gate refuses it, but an invented one makes the record look fuller
than it is, which is the one direction this product cannot absorb."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from askfirst.reader import Reader  # noqa: E402
from askfirst.schema import load_schema  # noqa: E402

reader = Reader(load_schema("ddxplus"))


def read(note):
    found, refused = reader(note)
    return set(found), {r["field"] for r in refused}


def test_plain_finding_is_read():
    found, _ = read("Chest pain at rest.")
    assert "E_14" in found


def test_denial_does_not_fire():
    found, refused = read("Patient denies cough.")
    assert "E_201" not in found
    assert "E_201" in refused


def test_negation_stops_at_the_full_stop():
    """The bug: "Denies fever and denies cough. Known high blood pressure." threw away the blood
    pressure, because "denies" sat three words behind it across a sentence boundary."""
    found, _ = read("Denies fever and denies cough. Known high blood pressure.")
    assert "E_102" in found or "E_104" in found


def test_one_word_does_not_make_a_finding():
    """The first version fired a field when any one long word from its question appeared, which
    gave 43.3% precision — nine invented findings a note."""
    found, _ = read("The chest radiograph was unremarkable.")
    assert "E_14" not in found


def test_value_labels_are_read():
    found, _ = read("Pain is located in the hypochondrium(R).")
    assert found, "no finding came out of a note naming a region verbatim"


def test_empty_note_reads_nothing():
    found, refused = read("")
    assert not found and not refused


def test_reading_is_cheap():
    """It has to run on the box that serves the page, which has no accelerator."""
    import time
    note = "Chest pain at rest. Denies cough. Known high blood pressure. " * 12
    started = time.time()
    for _ in range(20):
        reader(note)
    assert (time.time() - started) / 20 < 0.25
