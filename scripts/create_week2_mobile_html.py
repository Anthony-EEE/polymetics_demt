from __future__ import annotations

import base64
import csv
import html
import json
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "outputs/week2_latest_work_summary_mobile.html"
DATASET = ROOT / "dataset"
HUMAN_V2 = ROOT / "outputs/week2_human_diagnostics_keypoints_v2"
HUMAN_QUICK = ROOT / "outputs/week2_human_diagnostics_keypoints_quick"
VREF_OUT = ROOT / "outputs/week2_human_phase_reference_p6p7_v2"

SPATIAL_ID_SUMMARY = DATASET / "ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel/summary_seed628_n10.json"
SPATIAL_OOD_SUMMARY = DATASET / "ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel/summary_seed628_n30.json"
ORIENTATION_SUMMARY = DATASET / "orn_mvp_full/policy_rollouts_seed628/summary_seed628_n10.json"
TEMPORAL_VREF_SUMMARY = DATASET / "temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/summary_seed628_n10.json"
VREF_JSON = VREF_OUT / "v_ref_phase_reference.json"

FIGURES = {
    "Human spatial keypoints": HUMAN_QUICK / "corridor_crossing_xz_center_radius_by_group.png",
    "Human orientation p95": HUMAN_QUICK / "orientation_p95_by_group.png",
    "Spatial S15-S35 loss": DATASET / "ar_guidance_spatial_S15_S35/loss.png",
    "Orientation R30 trace": DATASET / "orn_mvp_full/orientation_plots/orn_mvp_R30_ee_xyz_orientation.png",
    "Temporal v_ref summary": DATASET / "temporal_vref_p6p7_V075_V250/temporal_plots/temporal_V075_150_V025_250_summary.png",
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
TEMPORAL_ORDER = ["V075_150", "V050_200", "V025_250"]


def load_summary(path: Path, order: list[str]) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    by_cond = {row["condition"]: row for row in data["summaries"]}
    return [by_cond[cond] for cond in order]


def keypoint_radius(group: str, keypoint: str, stat: str) -> float:
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


def orientation_event(group: str, event: str) -> dict:
    with (HUMAN_V2 / "orientation_event_summary.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["group"] == group and row["event"] == event:
                return row
    raise KeyError((group, event))


def temporal_human_rows() -> dict[str, dict]:
    with (HUMAN_V2 / "temporal_human_summary.csv").open("r", encoding="utf-8") as f:
        return {row["group"]: row for row in csv.DictReader(f)}


def vref_group() -> dict:
    with VREF_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["groups"]["P6P7_post_valid_order"]


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def cm(value_m: float) -> str:
    return f"{value_m * 100:.1f} cm"


def esc(value) -> str:
    return html.escape(str(value))


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "\n".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def image_data_uri(path: Path, max_width: int = 1100) -> str:
    if not path.exists():
        return ""
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > max_width:
            scale = max_width / im.width
            im = im.resize((max_width, max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def figure_block(title: str, path: Path) -> str:
    uri = image_data_uri(path)
    if not uri:
        return f"<section class='card'><h2>{esc(title)}</h2><p>Missing figure: {esc(path)}</p></section>"
    return f"<section class='card'><h2>{esc(title)}</h2><img src='{uri}' alt='{esc(title)}'></section>"


def build_html() -> str:
    spatial_id = load_summary(SPATIAL_ID_SUMMARY, SPATIAL_ORDER)
    spatial_ood = load_summary(SPATIAL_OOD_SUMMARY, SPATIAL_ORDER)
    orientation = load_summary(ORIENTATION_SUMMARY, ORIENTATION_ORDER)
    temporal = load_summary(TEMPORAL_VREF_SUMMARY, TEMPORAL_ORDER)
    vref = vref_group()
    temporal_human = temporal_human_rows()

    spatial_rows = []
    for id_row, ood_row in zip(spatial_id, spatial_ood):
        cond = id_row["condition"]
        csr, pgr = SPATIAL_RADII[cond]
        spatial_rows.append(
            [
                cond,
                f"{csr:.2f} m",
                f"{pgr:.3f} m",
                f"{id_row['success_count']}/{id_row['num_rollouts']} = {pct(float(id_row['success_rate']))}",
                f"{ood_row['success_count']}/{ood_row['num_rollouts']} = {pct(float(ood_row['success_rate']))}",
            ]
        )

    orientation_rows = []
    for row in orientation:
        cfg = row.get("condition_config", {})
        deg = float(cfg.get("orientation_max_degrees", 0.0))
        label = "fixed default orientation" if deg == 0 else f"+/-{deg:.0f} deg full-trajectory sample"
        orientation_rows.append([row["condition"], label, f"{row['success_count']}/{row['num_rollouts']} = {pct(float(row['success_rate']))}"])

    temporal_rows = []
    ranges = {
        "V075_150": "[0.75, 1.50] x v_ref",
        "V050_200": "[0.50, 2.00] x v_ref",
        "V025_250": "[0.25, 2.50] x v_ref",
    }
    for row in temporal:
        temporal_rows.append([row["condition"], ranges[row["condition"]], f"{row['success_count']}/{row['num_rollouts']} = {pct(float(row['success_rate']))}"])

    human_spatial_rows = []
    for name, group in [
        ("P1 pre", "P1_target_pre_skill1"),
        ("P2 pre", "P2_target_pre_skill2"),
        ("P6 post", "P6_target_post_skill1"),
        ("P7 post", "P7_target_post_skill2"),
    ]:
        human_spatial_rows.append(
            [
                name,
                cm(keypoint_radius(group, "corridor_crossing", "p90")),
                cm(keypoint_radius(group, "corridor_crossing", "p95")),
                cm(keypoint_radius(group, "pregrasp_keypoint", "p95")),
            ]
        )

    human_orientation_rows = []
    for name, group, event in [
        ("P6 closest grasp", "P6_target_post_skill1", "closest_grasp"),
        ("P6 first close", "P6_target_post_skill1", "first_close"),
        ("P7 closest grasp", "P7_target_post_skill2", "closest_grasp"),
        ("P7 first close", "P7_target_post_skill2", "first_close"),
    ]:
        row = orientation_event(group, event)
        human_orientation_rows.append(
            [
                name,
                f"{float(row['angle_to_group_mean_p95_deg']):.1f} deg",
                pct(float(row["coverage_15deg"])),
            ]
        )

    human_temporal_rows = []
    for name, group in [
        ("P1 pre", "P1_target_pre_skill1"),
        ("P2 pre", "P2_target_pre_skill2"),
        ("P6 post", "P6_target_post_skill1"),
        ("P7 post", "P7_target_post_skill2"),
    ]:
        row = temporal_human[group]
        human_temporal_rows.append(
            [
                name,
                pct(float(row["duration_ratio_coverage_0p5_2p0"])),
                pct(float(row["mean_speed_ratio_coverage_0p5_2p0"])),
            ]
        )

    phase_rows = []
    for phase in ["start_to_corridor", "corridor_to_pregrasp", "pregrasp_to_first_close", "first_close_to_end"]:
        phase_rows.append([phase.replace("_", " "), f"{float(vref['phase_mean_durations_s'][phase]):.2f} s"])

    figures = "\n".join(figure_block(title, path) for title, path in FIGURES.items())

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Week 2 DEMT Parameter Evidence</title>
<style>
  :root {{
    --ink: #1f2937;
    --muted: #6b7280;
    --line: #d1d5db;
    --bg: #f8fafc;
    --blue: #2563eb;
    --green: #16a34a;
    --red: #dc2626;
    --amber: #b45309;
  }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.45;
  }}
  header {{
    background: #111827;
    color: white;
    padding: 28px 18px 24px;
  }}
  main {{
    max-width: 980px;
    margin: 0 auto;
    padding: 14px;
  }}
  h1 {{
    font-size: 28px;
    margin: 0 0 8px;
  }}
  h2 {{
    font-size: 21px;
    margin: 0 0 12px;
  }}
  h3 {{
    font-size: 16px;
    margin: 18px 0 8px;
  }}
  p {{
    margin: 8px 0;
  }}
  .card {{
    background: white;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 16px;
    margin: 14px 0;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  }}
  .takeaway {{
    border-left: 5px solid var(--blue);
    padding-left: 12px;
    font-weight: 600;
  }}
  .warning {{
    border-left: 5px solid var(--amber);
    padding-left: 12px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 12px;
  }}
  .pill {{
    display: inline-block;
    padding: 3px 8px;
    border-radius: 999px;
    background: #e0f2fe;
    color: #075985;
    font-size: 12px;
    font-weight: 700;
    margin-right: 6px;
  }}
  .table-wrap {{
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 620px;
    font-size: 13px;
  }}
  th, td {{
    border: 1px solid var(--line);
    padding: 8px;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    background: #eff6ff;
    font-weight: 700;
  }}
  img {{
    width: 100%;
    height: auto;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: white;
  }}
  ul {{
    padding-left: 20px;
  }}
  code {{
    background: #f3f4f6;
    padding: 1px 4px;
    border-radius: 4px;
  }}
</style>
</head>
<body>
<header>
  <h1>Week 2 DEMT Parameter Evidence</h1>
  <p>Mobile-readable version of the PPTX. Human diagnostics + finite sensitivity checks for AR guidance values.</p>
</header>
<main>
  <section class="card">
    <h2>Bottom Line</h2>
    <p class="takeaway">The Table 5 AR values are defensible bounded finite candidates for this robot, task family, learner, and N=30 budget. They are not proven global optima.</p>
    <p>Week 2 connects three pieces: real-human compatibility diagnostics, controlled learner sensitivity checks, and conservative rebuttal wording.</p>
    <p class="warning">Spatial is the weakest exact-number story; orientation is the cleanest; temporal is now strongest when framed with P6/P7 <code>v_ref</code>.</p>
  </section>

  <section class="card">
    <h2>What Week 2 Added</h2>
    <div class="grid">
      <p><span class="pill">Human</span> P1/P2/P6/P7/P8 real-user diagnostics for spatial keypoints, orientation, and timing.</p>
      <p><span class="pill">Spatial</span> S15-S35 fixed-ratio funnel sweep plus annulus OOD stress test.</p>
      <p><span class="pill">Orientation</span> R00/R15/R30 plus post-training p95 orientation concentration around 13-14 deg.</p>
      <p><span class="pill">Temporal</span> P6/P7 <code>v_ref</code>-anchored V075/V050/V025 experiment.</p>
    </div>
  </section>

  <section class="card">
    <h2>Human Spatial Diagnostics</h2>
    {table(["Group", "early approach p90", "early approach p95", "pre-grasp p95"], human_spatial_rows)}
    <p>Interpretation: post-training P6/P7 trajectories tighten strongly, but a single early keypoint does not prove 25 cm optimality. Use this as compatibility/tightening evidence.</p>
  </section>

  <section class="card">
    <h2>Human Orientation Diagnostics</h2>
    {table(["Group/event", "p95 to group mean", "15 deg coverage"], human_orientation_rows)}
    <p>Interpretation: 15 deg is human-compatible for post-training grasp/close behavior, especially when paired with R00/R15/R30 learner sensitivity.</p>
  </section>

  <section class="card">
    <h2>Human Temporal Diagnostics</h2>
    {table(["Group", "duration coverage [0.5,2.0]", "speed coverage [0.5,2.0]"], human_temporal_rows)}
    <p>Interpretation: [0.5, 2.0] is a broad human-compatible relative timing window, but the stronger learner evidence is the P6/P7 <code>v_ref</code> rollout below.</p>
  </section>

  <section class="card">
    <h2>Spatial S15-S35 Results</h2>
    {table(["Cond.", "corridor_start_radius", "pre_grasp_radius", "shared r=0.35", "OOD annulus r=0.35-0.40"], spatial_rows)}
    <p>Interpretation: wider spatial variation does not automatically improve either in-distribution success or OOD robustness. Spatial should be framed as a role-separated funnel, not exact 25 cm optimality.</p>
  </section>

  <section class="card">
    <h2>Orientation R00/R15/R30 Results</h2>
    {table(["Condition", "variation", "success"], orientation_rows)}
    <p>Interpretation: 30 deg degrades relative to 15 deg. This is the cleanest finite sensitivity story.</p>
  </section>

  <section class="card">
    <h2>Temporal P6/P7 v_ref Setup</h2>
    <p><strong>Reference:</strong> P6P7_post_valid_order, n={int(vref["n"])}, mean total duration={float(vref["mean_total_duration_s"]):.2f} s.</p>
    {table(["Phase", "mean duration"], phase_rows)}
  </section>

  <section class="card">
    <h2>Temporal v_ref Rollout Results</h2>
    {table(["Condition", "phase-duration range", "success"], temporal_rows)}
    <p>Interpretation: the policy remains robust at the paper-style <code>[0.5, 2.0] x v_ref</code> range; degradation appears only at the wider <code>[0.25, 2.5] x v_ref</code> range.</p>
  </section>

  <section class="card">
    <h2>Recommended Rebuttal Wording</h2>
    <p>The submitted paper does not exhaustively optimize the continuous AR-parameter space. Instead, the Table 5 values instantiate DEMT-selected spatial, contact-orientation, and temporal structures. Week 2 evidence supports these values as bounded finite candidates for this robot, task family, learner, and N=30 demonstration budget: they are human-compatible and learner-aware, but not claimed as mathematical global optima.</p>
  </section>

  <section class="card">
    <h2>Decision</h2>
    <ul>
      <li>Use Week 2 as rebuttal/appendix support, not as a new claim of exhaustive parameter optimization.</li>
      <li>If a reviewer explicitly attacks 25 cm, the next experiment should be a fixed-ratio spatial funnel sweep.</li>
      <li>Orientation is already usable; optional future work is R10/R20.</li>
      <li>Temporal should use the P6/P7 <code>v_ref</code> version, not the old T ladder.</li>
    </ul>
  </section>

  {figures}
</main>
</body>
</html>"""


def main() -> None:
    OUT_PATH.write_text(build_html(), encoding="utf-8")
    print(OUT_PATH)


if __name__ == "__main__":
    main()
