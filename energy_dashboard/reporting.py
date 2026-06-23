from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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
    security_breakdown: pd.DataFrame,
    changes: dict[str, float],
    changes_summary: str,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.1 * cm,
        leftMargin=1.1 * cm,
        topMargin=0.9 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BriefingTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BriefingHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=11,
            textColor=colors.HexColor("#1e3a5f"),
            spaceBefore=2,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BriefingBody",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="MethodNote",
            parent=styles["BodyText"],
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#475569"),
            borderColor=colors.HexColor("#cbd5e1"),
            borderWidth=0.5,
            borderPadding=4,
            backColor=colors.HexColor("#f8fafc"),
        )
    )
    story = [
        Paragraph("Kyrgyzstan Energy Situation Briefing", styles["BriefingTitle"]),
        Paragraph(
            f"Planning reference: {int(latest['year'])} | Current status: {briefing['status']} | "
            f"Security Index: {security['score']:.1f}/100",
            styles["BriefingHeading"],
        ),
        Paragraph(summary, styles["BriefingBody"]),
        Spacer(1, 0.10 * cm),
    ]

    metrics = [
        ["Metric", "Value", "Metric", "Value"],
        ["Production", f"{latest['production_twh']:.1f} TWh", "Consumption", f"{latest['consumption_twh']:.1f} TWh"],
        [
            "Domestic deficit / surplus",
            f"{latest['domestic_gap_twh']:.1f} TWh",
            "Net imports",
            f"{latest['net_imports_twh']:.1f} TWh",
        ],
        ["Hydropower share", f"{latest['hydro_share_pct']:.1f}%", "Security Index", f"{security['score']:.1f}/100"],
    ]
    story.append(_styled_table(metrics, [4.2 * cm, 3.5 * cm, 4.2 * cm, 3.6 * cm], compact=True))
    story.extend([Spacer(1, 0.10 * cm), Paragraph("Situation Panel", styles["BriefingHeading"])])
    story.append(
        _styled_table(
            [
                ["Field", "Assessment"],
                ["Main driver", briefing["main_driver"]],
                ["Key concern", briefing["key_concern"]],
                ["Outlook", briefing["outlook"]],
            ],
            [4.8 * cm, 10.7 * cm],
            compact=True,
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
            Spacer(1, 0.10 * cm),
            KeepTogether(
                [
                    Paragraph("Scenario Impact Analysis", styles["BriefingHeading"]),
                    _styled_table(
                        scenario_rows,
                        [2.0 * cm, 2.3 * cm, 1.9 * cm, 2.1 * cm, 2.3 * cm, 4.9 * cm],
                        small=True,
                        compact=True,
                    ),
                    Spacer(1, 0.04 * cm),
                    Paragraph(scenario_impact_summary, styles["BriefingBody"]),
                ]
            ),
        ]
    )

    breakdown_rows = [["Component", "Weight", "Contribution", "Current indicator"]]
    for _, row in security_breakdown.iterrows():
        breakdown_rows.append(
            [row["Component"], row["Weight"], row["Contribution"], row["Current indicator"]]
        )
    story.extend(
        [
            Spacer(1, 0.10 * cm),
            KeepTogether(
                [
                    Paragraph("Security Index Breakdown", styles["BriefingHeading"]),
                    _styled_table(
                        breakdown_rows,
                        [4.4 * cm, 1.7 * cm, 2.4 * cm, 7.0 * cm],
                        small=True,
                        compact=True,
                    ),
                ]
            ),
        ]
    )

    change_rows = [
        ["Demand YoY", "Production YoY", "Net imports YoY", "Hydro share change", "Domestic gap change"],
        [
            f"{changes['demand_yoy_pct']:+.1f}%",
            f"{changes['production_yoy_pct']:+.1f}%",
            f"{changes['imports_yoy_pct']:+.1f}%",
            f"{changes['hydro_share_change_pct']:+.1f} pp",
            f"{changes['domestic_gap_change_twh']:+.1f} TWh",
        ],
    ]
    story.extend(
        [
            Spacer(1, 0.10 * cm),
            KeepTogether(
                [
                    Paragraph("What Changed Since Last Year?", styles["BriefingHeading"]),
                    _styled_table(change_rows, [3.1 * cm] * 5, small=True, compact=True),
                    Spacer(1, 0.04 * cm),
                    Paragraph(changes_summary, styles["BriefingBody"]),
                ]
            ),
        ]
    )

    story.extend([Spacer(1, 0.10 * cm), Paragraph("Recommended Actions", styles["BriefingHeading"])])
    action_rows = [["Priority", "Action", "Trigger / evidence", "Reason"]]
    for _, row in actions.head(4).iterrows():
        action_rows.append(
            [
                row["Priority"],
                row["Recommended action"],
                row["Trigger / evidence"],
                row["Reason"],
            ]
        )
    story.append(
        _styled_table(
            action_rows,
            [1.5 * cm, 4.8 * cm, 4.8 * cm, 4.4 * cm],
            tiny=True,
            compact=True,
        )
    )

    rule_rows = [["Rule", "Current", "Status"]]
    for _, row in rules.iterrows():
        rule_rows.append([row["Policy rule"], row["Current value"], row["Status"]])
    story.extend(
        [
            Spacer(1, 0.10 * cm),
            KeepTogether(
                [
                    Paragraph("Policy Rule Checks", styles["BriefingHeading"]),
                    _styled_table(
                        rule_rows,
                        [7 * cm, 4 * cm, 4.5 * cm],
                        small=True,
                        compact=True,
                    ),
                ]
            ),
        ]
    )

    methodology_note = (
        "Methodology note: The Security Index is an explainable policy prototype combining production coverage "
        "(35 points), hydropower dependency (20), recent demand growth (20), and forecast reserve margin (25). "
        "Production coverage and forecast reserve margin are related energy-coverage measures and together account "
        "for 60 of 100 points; the Index therefore primarily reflects energy coverage, hydropower dependence, and "
        "demand pressure rather than every dimension of electricity security. "
        "Reserve margin always uses a fixed 12-month forecast window. Forecast monthly patterns are estimated from "
        "annual data and are not observed monthly demand. Displayed model ranges are uncalibrated sensitivity bands, "
        "not probabilistic confidence intervals. Scenario hydropower multipliers affect the scenario balance estimate, "
        "not the Security Index production input; index differences reflect scenario demand assumptions. Official 2024 useful "
        "electricity supply is available by PES service territory; regional production, losses, balance, and risk "
        "ranking remain unavailable. Use this briefing for strategic discussion and further analysis, not for "
        "real-time dispatch, binding procurement, budgeting, or investment approval."
    )
    story.extend(
        [
            Spacer(1, 0.10 * cm),
            Paragraph("Methodology and Use Note", styles["BriefingHeading"]),
            Paragraph(methodology_note, styles["MethodNote"]),
        ]
    )

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


def _page_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 0.8 * cm, A4[0] - doc.rightMargin, 0.8 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 0.48 * cm, "Kyrgyzstan Energy Intelligence Dashboard")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.48 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _styled_table(
    rows: list[list[str]],
    widths: list[float],
    small: bool = False,
    tiny: bool = False,
    compact: bool = False,
) -> Table:
    font_size = 6 if tiny else 7 if small else 8
    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    body_style.fontSize = font_size
    body_style.leading = font_size + 1.5
    wrapped = [[Paragraph(str(cell), body_style) for cell in row] for row in rows]
    table = Table(wrapped, colWidths=widths, repeatRows=1)
    vertical_padding = 2 if compact else 4
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
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), vertical_padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), vertical_padding),
            ]
        )
    )
    return table
