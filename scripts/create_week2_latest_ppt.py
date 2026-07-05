from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
OUT_PATH = OUT_DIR / "week2_latest_work_summary.pptx"

DATASET = ROOT / "dataset"
HUMAN_V2 = ROOT / "outputs/week2_human_diagnostics_keypoints_v2"
HUMAN_QUICK = ROOT / "outputs/week2_human_diagnostics_keypoints_quick"
VREF_OUT = ROOT / "outputs/week2_human_phase_reference_p6p7_v2"

SPATIAL_ID_SUMMARY = DATASET / "ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel/summary_seed628_n10.json"
SPATIAL_OOD_SUMMARY = DATASET / "ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel/summary_seed628_n30.json"
SPATIAL_LOSS_PNG = DATASET / "ar_guidance_spatial_S15_S35/loss.png"

ORIENTATION_SUMMARY = DATASET / "orn_mvp_full/policy_rollouts_seed628/summary_seed628_n10.json"
ORIENTATION_PNG = DATASET / "orn_mvp_full/orientation_plots/orn_mvp_R30_ee_xyz_orientation.png"

TEMPORAL_VREF_SUMMARY = DATASET / "temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/summary_seed628_n10.json"
TEMPORAL_VREF_PNG = DATASET / "temporal_vref_p6p7_V075_V250/temporal_plots/temporal_V075_150_V025_250_summary.png"
VREF_JSON = VREF_OUT / "v_ref_phase_reference.json"

HUMAN_SPATIAL_PNG = HUMAN_QUICK / "corridor_crossing_xz_center_radius_by_group.png"
HUMAN_ORN_PNG = HUMAN_QUICK / "orientation_p95_by_group.png"


COLORS = {
    "ink": RGBColor(31, 41, 55),
    "muted": RGBColor(107, 114, 128),
    "light": RGBColor(243, 244, 246),
    "line": RGBColor(209, 213, 219),
    "blue": RGBColor(37, 99, 235),
    "green": RGBColor(22, 163, 74),
    "amber": RGBColor(217, 119, 6),
    "red": RGBColor(220, 38, 38),
    "purple": RGBColor(124, 58, 237),
    "teal": RGBColor(13, 148, 136),
    "dark": RGBColor(17, 24, 39),
    "white": RGBColor(255, 255, 255),
}

SPATIAL_RADII = {
    "S15": (0.15, 0.036),
    "S20": (0.20, 0.048),
    "S25": (0.25, 0.060),
    "S30": (0.30, 0.072),
    "S35": (0.35, 0.084),
}

SPATIAL_ORDER = ["S15", "S20", "S25", "S30", "S35"]
ORIENTATION_ORDER = ["R00", "R15", "R30"]
TEMPORAL_VREF_ORDER = ["V075_150", "V050_200", "V025_250"]


def load_rollout_summary(path: Path, order: list[str]) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    summaries = data.get("summaries", [])
    by_cond = {str(row["condition"]): row for row in summaries}
    rows = []
    for cond in order:
        row = by_cond[cond]
        checkpoint = row.get("checkpoint", "")
        rows.append(
            {
                "condition": cond,
                "success": int(row["success_count"]),
                "total": int(row["num_rollouts"]),
                "rate": float(row["success_rate"]),
                "config": row.get("condition_config", {}),
                "checkpoint": Path(checkpoint).name if checkpoint else "",
            }
        )
    return rows


def load_keypoint_radius(group: str, keypoint: str, stat: str) -> float:
    with (HUMAN_V2 / "keypoint_spread_summary.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (
                row["group"] == group
                and row["keypoint"] == keypoint
                and row["coordinate"] == "plane_radius_to_group_mean"
                and row["stat"] == stat
            ):
                return float(row["value_m"])
    raise KeyError((group, keypoint, stat))


def load_orientation_event(group: str, event: str) -> dict:
    with (HUMAN_V2 / "orientation_event_summary.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["group"] == group and row["event"] == event:
                return row
    raise KeyError((group, event))


def load_temporal_human_rows() -> dict[str, dict]:
    with (HUMAN_V2 / "temporal_human_summary.csv").open("r", encoding="utf-8") as f:
        return {row["group"]: row for row in csv.DictReader(f)}


def load_vref_group() -> dict:
    with VREF_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["groups"]["P6P7_post_valid_order"]


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def pct1(value: float) -> str:
    return f"{value * 100:.1f}%"


def cm(value_m: float) -> str:
    return f"{value_m * 100:.1f}"


def add_textbox(slide, x, y, w, h, text, size=16, color=None, bold=False, align=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    p = tf.paragraphs[0]
    p.text = text
    if align is not None:
        p.alignment = align
    for paragraph in tf.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = color or COLORS["ink"]
    return shape


def add_title(slide, title, subtitle=None):
    add_textbox(slide, 0.55, 0.28, 12.2, 0.5, title, size=25, bold=True)
    if subtitle:
        add_textbox(slide, 0.57, 0.83, 12.1, 0.35, subtitle, size=12, color=COLORS["muted"])
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(1.20), Inches(12.2), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = COLORS["line"]
    line.line.fill.background()


def add_footer(slide, text="Week 2 DEMT parameter evidence"):
    add_textbox(slide, 0.55, 7.08, 8.2, 0.2, text, size=8, color=COLORS["muted"])


def add_bullets(slide, x, y, w, h, bullets, size=15, color=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    for idx, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = bullet
        p.font.size = Pt(size)
        p.font.color.rgb = color or COLORS["ink"]
        p.space_after = Pt(5)
    return shape


def add_callout(slide, x, y, w, h, title, body, fill, title_size=13, body_size=13):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    box.line.color.rgb = fill
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    tf.margin_left = Inches(0.13)
    tf.margin_right = Inches(0.13)
    tf.margin_top = Inches(0.08)
    p = tf.paragraphs[0]
    p.text = title
    p.font.bold = True
    p.font.size = Pt(title_size)
    p.font.color.rgb = COLORS["white"]
    p2 = tf.add_paragraph()
    p2.text = body
    p2.font.size = Pt(body_size)
    p2.font.color.rgb = COLORS["white"]
    return box


def add_table(slide, x, y, w, h, rows, col_widths=None, font_size=10, header_fill=None):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h))
    table = shape.table
    if col_widths:
        for idx, width in enumerate(col_widths):
            table.columns[idx].width = Inches(width)
    for r_idx, row in enumerate(rows):
        for c_idx, text in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = str(text)
            fill = COLORS["light"] if r_idx == 0 else COLORS["white"]
            if r_idx == 0 and header_fill:
                fill = header_fill
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill
            cell.margin_left = Inches(0.04)
            cell.margin_right = Inches(0.04)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            for paragraph in cell.text_frame.paragraphs:
                paragraph.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
                paragraph.font.size = Pt(font_size)
                paragraph.font.bold = r_idx == 0
                paragraph.font.color.rgb = COLORS["white"] if r_idx == 0 and header_fill else COLORS["ink"]
    return shape


def add_picture_fit(slide, image_path: Path, x, y, w, h):
    if not image_path.exists():
        add_callout(slide, x, y, w, h, "Missing figure", str(image_path), COLORS["red"], 11, 10)
        return None
    with Image.open(image_path) as im:
        iw, ih = im.size
    box_ratio = w / h
    img_ratio = iw / ih
    if img_ratio >= box_ratio:
        final_w = w
        final_h = w / img_ratio
        final_x = x
        final_y = y + (h - final_h) / 2
    else:
        final_h = h
        final_w = h * img_ratio
        final_x = x + (w - final_w) / 2
        final_y = y
    return slide.shapes.add_picture(str(image_path), Inches(final_x), Inches(final_y), width=Inches(final_w), height=Inches(final_h))


def add_percent_chart(slide, x, y, w, h, title, labels, values, color):
    chart_data = CategoryChartData()
    chart_data.categories = labels
    chart_data.add_series(title, values)
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), chart_data).chart
    chart.has_legend = False
    chart.value_axis.minimum_scale = 0.0
    chart.value_axis.maximum_scale = 1.0
    chart.value_axis.tick_labels.font.size = Pt(9)
    chart.category_axis.tick_labels.font.size = Pt(10)
    chart.plots[0].has_data_labels = True
    labels_obj = chart.plots[0].data_labels
    labels_obj.number_format = "0%"
    labels_obj.position = XL_LABEL_POSITION.OUTSIDE_END
    labels_obj.font.size = Pt(9)
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = color
    return chart


def add_two_series_chart(slide, x, y, w, h, title, labels, values_a, values_b, name_a, name_b):
    chart_data = CategoryChartData()
    chart_data.categories = labels
    chart_data.add_series(name_a, values_a)
    chart_data.add_series(name_b, values_b)
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), chart_data).chart
    chart.has_legend = True
    chart.legend.include_in_layout = False
    chart.value_axis.minimum_scale = 0.0
    chart.value_axis.maximum_scale = 1.0
    chart.value_axis.tick_labels.font.size = Pt(9)
    chart.category_axis.tick_labels.font.size = Pt(10)
    chart.plots[0].has_data_labels = True
    labels_obj = chart.plots[0].data_labels
    labels_obj.number_format = "0%"
    labels_obj.position = XL_LABEL_POSITION.OUTSIDE_END
    labels_obj.font.size = Pt(8)
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = COLORS["blue"]
    chart.series[1].format.fill.solid()
    chart.series[1].format.fill.fore_color.rgb = COLORS["red"]
    add_textbox(slide, x, y - 0.25, w, 0.22, title, size=11, bold=True, align=PP_ALIGN.CENTER)
    return chart


def build_deck() -> Path:
    spatial_id = load_rollout_summary(SPATIAL_ID_SUMMARY, SPATIAL_ORDER)
    spatial_ood = load_rollout_summary(SPATIAL_OOD_SUMMARY, SPATIAL_ORDER)
    orientation = load_rollout_summary(ORIENTATION_SUMMARY, ORIENTATION_ORDER)
    temporal_vref = load_rollout_summary(TEMPORAL_VREF_SUMMARY, TEMPORAL_VREF_ORDER)
    vref = load_vref_group()
    temporal_human = load_temporal_human_rows()

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # 1. Title
    slide = prs.slides.add_slide(blank)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLORS["dark"]
    bg.line.fill.background()
    add_textbox(slide, 0.78, 1.05, 11.8, 0.78, "Week 2 DEMT Parameter Evidence", size=34, color=COLORS["white"], bold=True)
    add_textbox(slide, 0.82, 1.95, 11.3, 0.45, "Human diagnostics + finite sensitivity checks for AR guidance values", size=20, color=RGBColor(191, 219, 254), bold=True)
    add_bullets(
        slide,
        0.86,
        3.00,
        11.6,
        1.7,
        [
            "Goal: answer whether the AR guidance parameters are arbitrary without claiming global optimality.",
            "Latest evidence: spatial funnel sweep, OOD stress test, orientation sensitivity, and P6/P7 v_ref temporal experiment.",
            "Recommended framing: bounded finite-candidate reasonableness under this robot, task family, learner, and N=30 budget.",
        ],
        size=18,
        color=COLORS["white"],
    )
    add_textbox(slide, 0.84, 6.55, 10.5, 0.3, "Prepared from Week 2 experiment outputs", size=12, color=RGBColor(209, 213, 219))

    # 2. Research question
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Research Framing", "The answer is bounded, not absolute")
    add_callout(slide, 0.75, 1.55, 5.8, 1.2, "Reviewer pressure", "Why these AR values instead of another radius, angle, or speed range?", COLORS["red"], 15, 15)
    add_callout(slide, 6.8, 1.55, 5.8, 1.2, "Defensible answer", "They are constrained finite candidates supported by human compatibility and learner sensitivity.", COLORS["green"], 15, 15)
    add_bullets(
        slide,
        0.9,
        3.25,
        11.6,
        1.55,
        [
            "Do not claim 25 cm / 15 deg / [0.5, 2.0] x v_ref are proven global optima.",
            "Do claim the P/R/V guidance dimensions are learner-relevant and human-trainable.",
            "Use Week 2 as evidence that the selected settings sit inside a plausible human-and-learner compatible design region.",
        ],
        size=18,
    )
    add_callout(slide, 1.0, 5.45, 11.25, 0.8, "One-line thesis", "DEMT parameters instantiate a structured guidance funnel; exact continuous optimization is future work.", COLORS["blue"], 13, 14)
    add_footer(slide)

    # 3. What changed this week
    slide = prs.slides.add_slide(blank)
    add_title(slide, "What Week 2 Added", "The evidence now links simulation, real human behavior, and rebuttal wording")
    rows = [
        ["Workstream", "New evidence", "Role in argument"],
        ["Human diagnostics", "P1/P2/P6/P7/P8 real-user keypoints, orientation, timing", "Human compatibility and behavior tightening"],
        ["Spatial", "S15-S35 fixed-ratio funnel + annulus OOD stress", "Wider spatial spread does not automatically improve robustness"],
        ["Orientation", "Reuse R00/R15/R30 + post-training orientation p95", "15 deg is human-compatible and more learnable than 30 deg"],
        ["Temporal", "P6/P7 v_ref-based V075/V050/V025 experiment", "[0.5, 2.0] x v_ref remains robust in this setup"],
    ]
    add_table(slide, 0.55, 1.55, 12.25, 2.7, rows, col_widths=[1.65, 5.0, 5.6], font_size=11, header_fill=COLORS["blue"])
    add_bullets(
        slide,
        0.95,
        4.65,
        11.0,
        1.15,
        [
            "The main scientific move is not another engineering pipeline; it is a tighter claim boundary.",
            "Spatial remains the weakest exact-number story; orientation is strongest; temporal v_ref is now much cleaner than the old T ladder.",
        ],
        size=17,
    )
    add_footer(slide)

    # 4. Human spatial diagnostics
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Human Spatial Diagnostics", "Post-training demonstrations tighten, but one keypoint does not prove 25 cm optimality")
    groups = ["P1_target_pre_skill1", "P2_target_pre_skill2", "P6_target_post_skill1", "P7_target_post_skill2"]
    names = ["P1 pre", "P2 pre", "P6 post", "P7 post"]
    rows = [["Group", "early approach p90", "early approach p95", "pre-grasp p95"]]
    for name, group in zip(names, groups):
        rows.append(
            [
                name,
                f"{cm(load_keypoint_radius(group, 'corridor_crossing', 'p90'))} cm",
                f"{cm(load_keypoint_radius(group, 'corridor_crossing', 'p95'))} cm",
                f"{cm(load_keypoint_radius(group, 'pregrasp_keypoint', 'p95'))} cm",
            ]
        )
    add_table(slide, 0.65, 1.45, 6.05, 2.15, rows, col_widths=[1.35, 1.6, 1.6, 1.5], font_size=11, header_fill=COLORS["green"])
    add_picture_fit(slide, HUMAN_SPATIAL_PNG, 7.0, 1.45, 5.4, 3.0)
    add_bullets(
        slide,
        0.85,
        4.15,
        11.4,
        1.35,
        [
            "P6/P7 post-training early approach p95 is 9.5 / 6.7 cm, much tighter than P1/P2 pre-training.",
            "But P1/P2 being mostly inside a 25 cm outer envelope cannot by itself justify 25 cm.",
            "Use spatial human data as compatibility/tightening evidence; use paper MPCV/EDSR for the core spatial claim.",
        ],
        size=15,
    )
    add_footer(slide)

    # 5. Human orientation and timing diagnostics
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Human Orientation and Timing Diagnostics", "Useful compatibility evidence for R/V guidance")
    p6_grasp = load_orientation_event("P6_target_post_skill1", "closest_grasp")
    p6_close = load_orientation_event("P6_target_post_skill1", "first_close")
    p7_grasp = load_orientation_event("P7_target_post_skill2", "closest_grasp")
    p7_close = load_orientation_event("P7_target_post_skill2", "first_close")
    rows = [
        ["Group/event", "p95 to group mean", "15deg coverage"],
        ["P6 closest grasp", f"{float(p6_grasp['angle_to_group_mean_p95_deg']):.1f} deg", pct1(float(p6_grasp["coverage_15deg"]))],
        ["P6 first close", f"{float(p6_close['angle_to_group_mean_p95_deg']):.1f} deg", pct1(float(p6_close["coverage_15deg"]))],
        ["P7 closest grasp", f"{float(p7_grasp['angle_to_group_mean_p95_deg']):.1f} deg", pct1(float(p7_grasp["coverage_15deg"]))],
        ["P7 first close", f"{float(p7_close['angle_to_group_mean_p95_deg']):.1f} deg", pct1(float(p7_close["coverage_15deg"]))],
    ]
    add_table(slide, 0.65, 1.45, 5.55, 2.35, rows, col_widths=[2.25, 1.75, 1.55], font_size=11, header_fill=COLORS["purple"])
    temp_rows = [["Group", "duration coverage [0.5,2.0]", "speed coverage [0.5,2.0]"]]
    for group, name in [
        ("P1_target_pre_skill1", "P1 pre"),
        ("P2_target_pre_skill2", "P2 pre"),
        ("P6_target_post_skill1", "P6 post"),
        ("P7_target_post_skill2", "P7 post"),
    ]:
        row = temporal_human[group]
        temp_rows.append(
            [
                name,
                pct1(float(row["duration_ratio_coverage_0p5_2p0"])),
                pct1(float(row["mean_speed_ratio_coverage_0p5_2p0"])),
            ]
        )
    add_table(slide, 6.55, 1.45, 6.1, 2.35, temp_rows, col_widths=[1.35, 2.4, 2.35], font_size=11, header_fill=COLORS["amber"])
    add_picture_fit(slide, HUMAN_ORN_PNG, 0.9, 4.2, 4.9, 1.75)
    add_bullets(
        slide,
        6.35,
        4.15,
        5.8,
        1.45,
        [
            "Orientation: post-training P6/P7 grasp/close orientations lie mostly within 15 deg of group mean.",
            "Temporal: [0.5, 2.0] is a broad human-compatible relative window, but the stronger result is the v_ref rollout experiment.",
        ],
        size=14,
    )
    add_footer(slide)

    # 6. Spatial results
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Spatial Funnel Sweep", "Fixed-ratio S15-S35 results under paired starts")
    labels = [r["condition"] for r in spatial_id]
    id_values = [r["rate"] for r in spatial_id]
    ood_values = [r["rate"] for r in spatial_ood]
    add_two_series_chart(slide, 0.65, 1.65, 5.9, 3.0, "Rollout success", labels, id_values, ood_values, "shared r=0.35", "OOD annulus")
    rows = [["Cond.", "corridor", "pre-grasp", "shared r35", "OOD r35-r40"]]
    for id_row, ood_row in zip(spatial_id, spatial_ood):
        csr, pgr = SPATIAL_RADII[id_row["condition"]]
        rows.append(
            [
                id_row["condition"],
                f"{csr:.2f} m",
                f"{pgr:.3f} m",
                f"{id_row['success']}/{id_row['total']}",
                f"{ood_row['success']}/{ood_row['total']}",
            ]
        )
    add_table(slide, 6.85, 1.45, 5.9, 2.45, rows, col_widths=[0.8, 1.25, 1.35, 1.25, 1.25], font_size=10, header_fill=COLORS["blue"])
    add_picture_fit(slide, SPATIAL_LOSS_PNG, 7.05, 4.25, 5.45, 1.65)
    add_bullets(
        slide,
        0.85,
        4.95,
        5.7,
        1.0,
        [
            "More spatial variation did not reliably improve in-distribution success or OOD robustness.",
            "S35 is worst under OOD annulus; S15/S25 are the only competitive candidates there.",
            "Interpret spatial as a role-separated funnel claim, not exact 25 cm optimality.",
        ],
        size=13,
    )
    add_footer(slide)

    # 7. Orientation results
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Orientation Sensitivity", "This is the cleanest numeric story")
    labels = [r["condition"] for r in orientation]
    values = [r["rate"] for r in orientation]
    add_percent_chart(slide, 0.65, 1.55, 5.15, 3.15, "Rollout success", labels, values, COLORS["purple"])
    rows = [["Condition", "orientation variation", "success"]]
    for row in orientation:
        deg = float(row.get("config", {}).get("orientation_max_degrees", 0.0))
        label = "fixed 0 deg" if deg == 0 else f"+/-{deg:.0f} deg"
        rows.append([row["condition"], label, f"{row['success']}/{row['total']}"])
    add_table(slide, 6.25, 1.55, 3.95, 1.65, rows, col_widths=[1.25, 1.75, 0.95], font_size=11, header_fill=COLORS["purple"])
    add_picture_fit(slide, ORIENTATION_PNG, 6.25, 3.55, 5.95, 2.0)
    add_bullets(
        slide,
        0.85,
        4.95,
        5.1,
        1.0,
        [
            "R00/R15/R30 rollout = 7/10, 6/10, 4/10.",
            "P6/P7 post human p95 near grasp/close is roughly 13-14 deg.",
            "Allowed claim: 15 deg is human-achievable and more learner-compatible than 30 deg.",
        ],
        size=14,
    )
    add_footer(slide)

    # 8. Temporal vref setup
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Temporal v_ref Experiment", "Week 2 replaced the old T ladder with a human-referenced design")
    rows = [
        ["Reference group", "n", "mean total duration"],
        ["P6P7_post_valid_order", str(vref["n"]), f"{float(vref['mean_total_duration_s']):.2f} s"],
    ]
    add_table(slide, 0.75, 1.45, 5.2, 1.0, rows, col_widths=[2.65, 0.8, 1.75], font_size=12, header_fill=COLORS["teal"])
    phase = vref["phase_mean_durations_s"]
    phase_rows = [["Phase", "mean duration"]]
    for phase_name in ["start_to_corridor", "corridor_to_pregrasp", "pregrasp_to_first_close", "first_close_to_end"]:
        phase_rows.append([phase_name.replace("_", " "), f"{float(phase[phase_name]):.2f} s"])
    add_table(slide, 0.75, 2.85, 5.2, 2.15, phase_rows, col_widths=[3.35, 1.4], font_size=11, header_fill=COLORS["teal"])
    cond_rows = [
        ["Condition", "range"],
        ["V075_150", "[0.75, 1.50] x v_ref"],
        ["V050_200", "[0.50, 2.00] x v_ref"],
        ["V025_250", "[0.25, 2.50] x v_ref"],
    ]
    add_table(slide, 6.55, 1.45, 5.8, 1.65, cond_rows, col_widths=[1.55, 3.95], font_size=12, header_fill=COLORS["teal"])
    add_bullets(
        slide,
        6.75,
        3.65,
        5.4,
        1.6,
        [
            "This is the main temporal evidence for the paper-style [0.5, 2.0] x v_ref range.",
            "It is relative to a human reference trajectory, not a fixed metric speed threshold.",
            "The old T00/T25/T50/T75/T100 ladder should not be presented as the final temporal result.",
        ],
        size=15,
    )
    add_footer(slide)

    # 9. Temporal vref results
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Temporal v_ref Rollout Results", "[0.5, 2.0] x v_ref stays robust; wider variation starts to degrade")
    labels = [r["condition"] for r in temporal_vref]
    values = [r["rate"] for r in temporal_vref]
    add_percent_chart(slide, 0.65, 1.55, 5.15, 3.05, "Rollout success", labels, values, COLORS["teal"])
    rows = [["Condition", "range", "checkpoint", "success"]]
    range_text = {
        "V075_150": "[0.75, 1.50]",
        "V050_200": "[0.50, 2.00]",
        "V025_250": "[0.25, 2.50]",
    }
    for row in temporal_vref:
        rows.append([row["condition"], range_text[row["condition"]], row["checkpoint"], f"{row['success']}/{row['total']}"])
    add_table(slide, 6.05, 1.45, 6.75, 1.85, rows, col_widths=[1.25, 1.55, 2.75, 1.0], font_size=9, header_fill=COLORS["teal"])
    add_picture_fit(slide, TEMPORAL_VREF_PNG, 6.25, 3.65, 6.1, 2.05)
    add_bullets(
        slide,
        0.85,
        4.95,
        5.1,
        1.0,
        [
            "V075_150 and V050_200 both achieved 10/10.",
            "Only V025_250 dropped to 8/10.",
            "This strengthens the temporal claim compared with the old hand-written timing ladder.",
        ],
        size=14,
    )
    add_footer(slide)

    # 10. Synthesis
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Cross-Evidence Synthesis", "What we can and cannot claim")
    rows = [
        ["Dimension", "Human evidence", "Learner evidence", "Claim strength"],
        ["Spatial", "post keypoints tighten; 25 cm is permissive", "S sweep and OOD are mixed", "structure/funnel, not exact radius"],
        ["Orientation", "P6/P7 p95 ~= 13-14 deg", "R30 degrades vs R15", "strong finite-candidate support"],
        ["Temporal", "P6/P7 v_ref scaffold", "[0.5,2.0] x v_ref = 10/10", "clean broad-window support"],
    ]
    add_table(slide, 0.45, 1.45, 12.45, 2.55, rows, col_widths=[1.55, 3.8, 3.35, 3.75], font_size=10, header_fill=COLORS["green"])
    add_callout(slide, 0.85, 4.45, 5.75, 1.0, "Supported", "The parameters are defensible finite candidates under human and learner constraints.", COLORS["green"])
    add_callout(slide, 6.85, 4.45, 5.75, 1.0, "Not supported", "The current evidence does not prove exact global optimality over continuous AR parameters.", COLORS["red"])
    add_footer(slide)

    # 11. Rebuttal wording
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Recommended Wording", "Conservative enough for reviewers, concrete enough for rebuttal")
    quote = (
        "The submitted paper does not exhaustively optimize the continuous AR-parameter space. "
        "Instead, the Table 5 values instantiate DEMT-selected spatial, contact-orientation, "
        "and temporal structures. Week 2 evidence supports these values as bounded finite "
        "candidates for this robot, task family, learner, and N=30 demonstration budget: they "
        "are human-compatible and learner-aware, but not claimed as mathematical global optima."
    )
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.55), Inches(11.7), Inches(2.25))
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS["light"]
    shape.line.color.rgb = COLORS["line"]
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.25)
    tf.margin_right = Inches(0.25)
    tf.margin_top = Inches(0.15)
    p = tf.paragraphs[0]
    p.text = quote
    p.font.size = Pt(19)
    p.font.color.rgb = COLORS["ink"]
    add_bullets(
        slide,
        0.95,
        4.2,
        11.4,
        1.25,
        [
            "For spatial: emphasize the 25/5/3 cm funnel and full-trajectory consistency, not a single local 25 cm proof.",
            "For orientation: cite R00/R15/R30 plus P6/P7 post-training p95 ~= 13-14 deg.",
            "For temporal: cite the P6/P7 v_ref experiment, especially V050_200 = 10/10.",
        ],
        size=15,
    )
    add_footer(slide)

    # 12. Decisions and next work
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Decision and Next Work", "What to do with Week 2 evidence")
    rows = [
        ["Question", "Current answer", "Next action"],
        ["Use in rebuttal?", "Yes, as bounded evidence", "Keep wording conservative"],
        ["Need more spatial proof?", "Only if reviewer explicitly attacks 25 cm", "Run fixed-ratio funnel sweep E05"],
        ["Need more orientation proof?", "Current evidence is usable", "Optional R10/R20 bracket later"],
        ["Need more temporal proof?", "v_ref result is the clean version", "Optional larger n or second seed"],
    ]
    add_table(slide, 0.55, 1.5, 12.2, 2.45, rows, col_widths=[2.35, 4.2, 5.65], font_size=11, header_fill=COLORS["blue"])
    add_callout(slide, 0.85, 4.55, 11.6, 0.9, "Recommended position", "Use Week 2 as rebuttal/appendix support, not as a new claim of exhaustive parameter optimization.", COLORS["blue"])
    add_bullets(slide, 1.0, 5.75, 11.2, 0.65, ["For a future paper, the strongest addition is a coupled spatial funnel sweep plus a local orientation bracket."], size=15)
    add_footer(slide)

    # 13. Backup files
    slide = prs.slides.add_slide(blank)
    add_title(slide, "Backup: Exact Output Files", "Paths used to generate the deck")
    add_bullets(
        slide,
        0.75,
        1.45,
        11.9,
        4.8,
        [
            f"Spatial shared-start summary: {SPATIAL_ID_SUMMARY.relative_to(ROOT)}",
            f"Spatial OOD annulus summary: {SPATIAL_OOD_SUMMARY.relative_to(ROOT)}",
            f"Orientation summary: {ORIENTATION_SUMMARY.relative_to(ROOT)}",
            f"Temporal v_ref summary: {TEMPORAL_VREF_SUMMARY.relative_to(ROOT)}",
            f"Human diagnostics CSVs: {HUMAN_V2.relative_to(ROOT)}",
            f"P6/P7 v_ref reference: {VREF_JSON.relative_to(ROOT)}",
        ],
        size=12,
    )
    add_footer(slide)

    OUT_DIR.mkdir(exist_ok=True)
    prs.save(OUT_PATH)
    return OUT_PATH


if __name__ == "__main__":
    print(build_deck())
