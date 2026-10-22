import re
from decimal import Decimal

from transforms._destination_common import (
    record,
    section,
    run_transform,
)


DE = "daad_bintho_2023_24"

DE_ITEMS = [
    (
        "teaching_language",
        "Teaching language",
        "Lehrsprache im Studium",
    ),
    (
        "campus_navigation",
        "Campus navigation",
        "Zurechtfinden auf dem Campus",
    ),
    (
        "general_life",
        "Overall living situation",
        "Allgemeine Zufriedenheit",
    ),
    (
        "daily_culture",
        "Everyday culture",
        "Umstellung auf deutsche Alltagskultur",
    ),
    (
        "timetable",
        "Timetable organisation",
        "Organisation des Stundenplans",
    ),
    (
        "international_contact",
        "Contact with international students",
        "Kontakt zu anderen internationalen",
    ),
    (
        "learning_culture",
        "Teaching and learning culture",
        "Umstellung auf deutsche Lehr-/Lernkultur",
    ),
    (
        "daily_german",
        "German in everyday life",
        "Deutsche Sprache im Alltag",
    ),
    (
        "university_admin",
        "University administration",
        "Bürokratische Formalitäten innerhalb",
    ),
    (
        "part_time_job",
        "Finding a part-time job",
        "Suche nach einem Nebenjob",
    ),
    (
        "local_contact",
        "Contact with local students",
        "Kontakt zu deutschen/inländischen",
    ),
    (
        "housing_search",
        "Finding accommodation",
        "Wohnungssuche",
    ),
    (
        "external_admin",
        "Administration outside university",
        "Bürokratische Formalitäten außerhalb",
    ),
]


def german_values(body, marker):
    lines = [
        line
        for line in body.splitlines()
        if marker.casefold() in line.casefold()
    ]

    if len(lines) != 1:
        raise ValueError(f"Expected one German chart row: {marker}")

    values = [
        Decimal(token.replace(",", "."))
        for token in re.findall(r"\d{1,2},\d", lines[0])
    ]

    if (
        len(values) != 5
        or abs(sum(values) - 100) > Decimal("0.3")
    ):
        raise ValueError(
            f"Invalid five-level chart: {marker}: {values}"
        )

    return (
        sum(values[-2:]),
        lines[0].strip(),
        [str(value) for value in values],
    )


def prepare(rows, run):
    output = []

    row, body = section(rows, DE, "3.23")

    definition = (
        "DAAD BintHo 2023/24; international degree-seeking "
        "students in Germany; rather dissatisfied + "
        "completely dissatisfied."
    )

    for order, (code, label, marker) in enumerate(DE_ITEMS, 1):
        value, evidence, tokens = german_values(body, marker)

        output.append(
            record(
                run, row, "3.23", code, label,
                2023, "ALL", "All international students",
                value, definition, evidence,
                {
                    "sort_order": order,
                    "extracted_labels": tokens,
                    "calculation": "Sum of last two chart labels",
                },
            )
        )

    groups = [
        ("EU", "EU students", "Studierende aus EU-Staaten"),
        (
            "NON_EU",
            "Non-EU students",
            "Studierende aus Nicht-EU-Staaten",
        ),
        ("ALL", "All international students", "Befragte insgesamt"),
    ]

    figures = [
        ("3.24", "local_contact", "Contact with local students"),
        ("3.25", "daily_german", "German in everyday life"),
    ]

    for order, (table, code, label) in enumerate(figures, 1):
        row, body = section(rows, DE, table)

        for group, group_label, marker in groups:
            value, evidence, tokens = german_values(body, marker)

            output.append(
                record(
                    run, row, table, code, label,
                    2023, group, group_label, value,
                    (
                        "DAAD BintHo 2023/24; international "
                        "degree-seeking students in Germany; "
                        "rather poor + very poor."
                    ),
                    evidence,
                    {
                        "sort_order": order,
                        "extracted_labels": tokens,
                        "calculation": "Sum of last two chart labels",
                    },
                )
            )

    return output


if __name__ == "__main__":
    run_transform(DE, "daad-v1", prepare, 19)