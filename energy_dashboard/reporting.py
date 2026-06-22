from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_ministry_briefing_pdf(
    latest: pd.Series,
    security: dict,
    briefing: dict,
    summary: str,
    actions: pd.DataFrame,
    rules: pd.DataFrame,
    scenario_impacts: pd.DataFrame,
    scenario_impact_summary: str,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.3 * cm,
        leftMargin=1.3 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Kyrgyzstan Energy Situation Briefing", styles["Title"]),
        Paragraph(f"Current status: {briefing['status']} | Security index: {security['score']:.1f}/100", styles["Heading2"]),
        Paragraph(summary, styles["BodyText"]),
        Spacer(1, 0.3 * cm),
    ]

    metrics = [
        ["Metric", "Value"],
        ["Production", f"{latest['production_twh']:.1f} TWh"],
        ["Consumption", f"{latest['consumption_twh']:.1f} TWh"],
        ["Domestic deficit / surplus", f"{latest['domestic_gap_twh']:.1f} TWh"],
        ["Net imports", f"{latest['net_imports_twh']:.1f} TWh"],
        ["Hydropower share", f"{latest['hydro_share_pct']:.1f}%"],
    ]
    story.append(_styled_table(metrics, [6.5 * cm, 9 * cm]))
    story.extend([Spacer(1, 0.3 * cm), Paragraph("Situation Panel", styles["Heading2"])])
    story.append(
        _styled_table(
            [
                ["Field", "Assessment"],
                ["Main driver", briefing["main_driver"]],
                ["Key concern", briefing["key_concern"]],
                ["Outlook", briefing["outlook"]],
            ],
            [4.8 * cm, 10.7 * cm],
        )
    )

    scenario_rows = [
        ["Scenario", "Forecast demand", "Security index", "Risk level", "Net balance", "Key concern"]
    ]
    for _, row in scenario_impacts.iterrows():
        scenario_rows.append(
            [
                row["Scenario"],
                row["Forecast demand"],
                row["Security Index"],
                row["Risk level"],
                row["Net balance estimate"],
                row["Key concern"],
            ]
        )
    story.extend(
        [
            Spacer(1, 0.3 * cm),
            KeepTogether(
                [
                    Paragraph("Scenario Impact Analysis", styles["Heading2"]),
                    _styled_table(
                        scenario_rows,
                        [2.0 * cm, 2.3 * cm, 1.9 * cm, 2.1 * cm, 2.3 * cm, 4.9 * cm],
                        small=True,
                    ),
                    Spacer(1, 0.15 * cm),
                    Paragraph(scenario_impact_summary, styles["BodyText"]),
                ]
            ),
        ]
    )

    story.extend([Spacer(1, 0.3 * cm), Paragraph("Recommended Actions", styles["Heading2"])])
    action_rows = [["Priority", "Action", "Reason"]]
    for _, row in actions.head(4).iterrows():
        action_rows.append([row["Priority"], row["Recommended action"], row["Reason"]])
    story.append(_styled_table(action_rows, [2.2 * cm, 6.6 * cm, 6.7 * cm], small=True))

    rule_rows = [["Rule", "Current", "Status"]]
    for _, row in rules.iterrows():
        rule_rows.append([row["Policy rule"], row["Current value"], row["Status"]])
    story.extend(
        [
            Spacer(1, 0.3 * cm),
            KeepTogether(
                [
                    Paragraph("Policy Rule Checks", styles["Heading2"]),
                    _styled_table(rule_rows, [7 * cm, 4 * cm, 4.5 * cm], small=True),
                ]
            ),
        ]
    )

    doc.build(story)
    return buffer.getvalue()


def _styled_table(rows: list[list[str]], widths: list[float], small: bool = False) -> Table:
    font_size = 7 if small else 9
    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    body_style.fontSize = font_size
    body_style.leading = font_size + 2
    wrapped = [[Paragraph(str(cell), body_style) for cell in row] for row in rows]
    table = Table(wrapped, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table
