import re
from decimal import Decimal, ROUND_HALF_UP

from transforms._destination_common import (
    record,
    section,
    run_transform,
)


JP = "jasso_lifestyle_2023"

JP_BEFORE = [
    ("weather_culture", "Adapting to climate, food and customs"),
    ("learning_concern", "Achieving study goals"),
    ("communication", "Building relationships and communicating"),
    ("housing_concern", "Securing suitable accommodation"),
    ("health_disasters", "Illness and natural disasters"),
    ("loneliness", "Loneliness and homesickness"),
    ("financial_concern", "Financial difficulties"),
    ("no_concern", "No particular concern"),
    ("other_concern", "Other concerns"),
]

JP_AFTER = [
    ("prices", "High living costs"),
    ("daily_culture", "Different daily customs"),
    ("housing_search", "Finding accommodation"),
    ("housing_rules", "Housing and waste rules"),
    ("japanese", "Learning Japanese"),
    ("english", "Learning English"),
    ("local_contact", "Interacting with Japanese students"),
    ("staff_communication", "Communicating with school staff"),
    ("learning", "Keeping up with classes"),
    ("other", "Other difficulties"),
]


def prepare(rows, run):
    output = []

    for table, items in [
        ("2-3", JP_BEFORE),
        ("4-11", JP_AFTER),
    ]:
        row, body = section(rows, JP, table, japanese=True)

        series = {
            "counts": [],
            2023: [],
            2021: [],
            2019: [],
        }
        evidence = []

        patterns = [
            ("counts", r"^人数\s*\(人\)\s*(.*)$"),
            (2023, r"^率\s*\(%\)\s*(.*)$"),
            (2021, r"^令和\s*3\s*年率\s*\(%\)\s*(.*)$"),
            (2019, r"^令和\s*元\s*年率\s*\(%\)\s*(.*)$"),
        ]

        for line in body.splitlines():
            line = " ".join(line.split())

            for key, pattern in patterns:
                match = re.match(pattern, line)

                if match:
                    values = re.findall(
                        r"\d[\d,]*(?:\.\d+)?",
                        match[1],
                    )

                    series[key].extend(
                        Decimal(value.replace(",", ""))
                        for value in values
                    )

                    evidence.append(line)

        denominators = re.findall(
            r"回答者数の計\s*\(\s*([\d,]+)\s*人\s*\)",
            body,
        )

        if (
            len(denominators) != 1
            or any(
                len(values) != len(items)
                for values in series.values()
            )
        ):
            raise ValueError(
                f"Invalid JASSO table width/denominator: {table}; "
                f"lengths={[len(v) for v in series.values()]}"
            )

        n = int(denominators[0].replace(",", ""))

        if n <= 0:
            raise ValueError("Invalid JASSO denominator")

        for index, (code, label) in enumerate(items):
            count = series["counts"][index]

            if (
                count != count.to_integral_value()
                or not 0 <= count <= n
            ):
                raise ValueError(
                    f"Invalid respondent count: {table}/{code}"
                )

            calculated = (
                count * 100 / Decimal(n)
            ).quantize(
                Decimal("0.1"),
                rounding=ROUND_HALF_UP,
            )

            if calculated != series[2023][index]:
                raise ValueError(
                    f"Count/percentage mismatch: {table}/{code}"
                )

            for year in [2023, 2021, 2019]:
                output.append(
                    record(
                        run, row, table, code, label,
                        year, "ALL",
                        "Self-financed international students",
                        (
                            calculated
                            if year == 2023
                            else series[year][index]
                        ),
                        (
                            f"JASSO {year}; self-financed international "
                            "students in Japan; respondent percentage; "
                            "up to 3 responses. Historical waves "
                            "are separate samples."
                        ),
                        "\n".join(evidence),
                        {
                            "sort_order": index + 1,
                            "column_index": index + 1,
                            "percentage_basis": (
                                "respondents, not ranking points"
                            ),
                        },
                        numerator=int(count) if year == 2023 else None,
                        denominator=n if year == 2023 else None,
                    )
                )

    return output


if __name__ == "__main__":
    run_transform(JP, "jasso-v1", prepare, 57)