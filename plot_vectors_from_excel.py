import sys
from pathlib import Path
from typing import Tuple
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.strip() for c in df.columns})
    return df


def _find_required_columns(df: pd.DataFrame) -> Tuple[str, str, str, str]:
    # Build a normalized lookup for exact quick matches
    norm = {c: re.sub(r"\s+", "", c, flags=re.UNICODE).lower() for c in df.columns}
    rev = {v: k for k, v in norm.items()}

    def find_by_exact(key: str) -> str | None:
        return rev.get(key)

    def find_by_regex(patterns: list[str]) -> str | None:
        for c in df.columns:
            s = c.lower()
            if all(re.search(p, s, flags=re.IGNORECASE) for p in patterns):
                return c
        return None

    wmg = find_by_exact("w(mg)") or find_by_regex([r"^w\(mg\)"])
    wsi = find_by_exact("w(si)") or find_by_regex([r"^w\(si\)"])

    inv_mg = find_by_exact("1/dwdt_l(mg@liquid)") or find_by_regex([
        r"1/dwdt_l\(", r"mg@liquid\)"
    ])
    inv_si = find_by_exact("1/dwdt_l(si@liquid)") or find_by_regex([
        r"1/dwdt_l\(", r"si@liquid\)"
    ])

    if not (wmg and wsi and inv_mg and inv_si):
        msg = (
            "Missing required columns. Need: 'w(MG)', 'w(SI)', "
            "'1/dwdT_L(MG@LIQUID)', '1/dwdT_L(Si@LIQUID)'. Found: "
            f"{list(df.columns)}"
        )
        raise ValueError(msg)

    return wmg, wsi, inv_mg, inv_si


def load_data(input_excel: Path) -> pd.DataFrame:
    df = pd.read_excel(input_excel, header=0)
    df = _standardize_columns(df)
    # drop fully empty rows
    df = df.replace(r"^\s*$", np.nan, regex=True).dropna(how="all")
    return df


def make_quiver_plots(input_excel: Path, out_prefix: str = "liquid_vectors") -> Tuple[Path, Path, Path]:
    df = load_data(input_excel)
    col_wmg, col_wsi, col_inv_dwdT_mg, col_inv_dwdT_si = _find_required_columns(df)

    # Use numeric conversion to avoid strings
    wmg = pd.to_numeric(df[col_wmg], errors="coerce")
    wsi = pd.to_numeric(df[col_wsi], errors="coerce")
    u = pd.to_numeric(df[col_inv_dwdT_mg], errors="coerce")
    v = pd.to_numeric(df[col_inv_dwdT_si], errors="coerce")

    valid = ~(wmg.isna() | wsi.isna() | u.isna() | v.isna())
    wmg, wsi, u, v = wmg[valid], wsi[valid], u[valid], v[valid]

    # Scale U and V to axis-aligned arrow lengths by ratio to column minima (example provided)
    denom_u = u.min()  # expected negative
    denom_v = v.min()  # expected negative
    # Avoid division by zero
    if denom_u == 0 or np.isnan(denom_u):
        raise ValueError("Column 1/dwdT_L(MG@LIQUID) has invalid minimum for scaling.")
    if denom_v == 0 or np.isnan(denom_v):
        raise ValueError("Column 1/dwdT_L(SI@LIQUID) has invalid minimum for scaling.")

    dx = u / denom_u  # horizontal arrow length
    dy = v / denom_v  # vertical arrow length

    # Clip arrow endpoints to the data domain so arrows do not exceed composition ranges
    x_min, x_max = float(wmg.min()), float(wmg.max())
    y_min, y_max = float(wsi.min()), float(wsi.max())

    # Figure 1: U arrows along x-axis
    fig1, ax1 = plt.subplots(figsize=(7, 6), dpi=140)
    x1 = np.clip(wmg.values + dx.values, x_min, x_max)
    u_plot = x1 - wmg.values  # adjusted dx after clipping
    ax1.quiver(wmg.values, wsi.values, u_plot, np.zeros_like(u_plot), angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:blue")
    ax1.set_xlabel(col_wmg)
    ax1.set_ylabel(col_wsi)
    ax1.set_title("U arrows (scaled by ratio to min of 1/dwdT_L(MG@LIQUID))")
    ax1.grid(True, ls=":", alpha=0.4)
    ax1.set_aspect("equal", adjustable="box")
    fig1.tight_layout()
    out1 = input_excel.with_name(f"{out_prefix}_U_horizontal.png")
    fig1.savefig(out1)
    plt.close(fig1)

    # Figure 2: V arrows along y-axis
    fig2, ax2 = plt.subplots(figsize=(7, 6), dpi=140)
    y1 = np.clip(wsi.values + dy.values, y_min, y_max)
    v_plot = y1 - wsi.values  # adjusted dy after clipping
    ax2.quiver(wmg.values, wsi.values, np.zeros_like(v_plot), v_plot, angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:orange")
    ax2.set_xlabel(col_wmg)
    ax2.set_ylabel(col_wsi)
    ax2.set_title("V arrows (scaled by ratio to min of 1/dwdT_L(SI@LIQUID))")
    ax2.grid(True, ls=":", alpha=0.4)
    ax2.set_aspect("equal", adjustable="box")
    fig2.tight_layout()
    out2 = input_excel.with_name(f"{out_prefix}_V_vertical.png")
    fig2.savefig(out2)
    plt.close(fig2)

    # Figure 3: Resultant Z vector from U and V per definition
    fig3, ax3 = plt.subplots(figsize=(7, 6), dpi=140)
    z_dx = u_plot
    z_dy = v_plot
    # Resultant length and angle check (implicitly given by components)
    ax3.quiver(wmg.values, wsi.values, z_dx, z_dy, angles="xy", scale_units="xy", scale=1, width=0.003, color="tab:green")
    ax3.set_xlabel(col_wmg)
    ax3.set_ylabel(col_wsi)
    ax3.set_title("Resultant Z = vector sum of U and V (scaled)")
    ax3.grid(True, ls=":", alpha=0.4)
    ax3.set_aspect("equal", adjustable="box")
    fig3.tight_layout()
    out3 = input_excel.with_name(f"{out_prefix}_Z_resultant.png")
    fig3.savefig(out3)
    plt.close(fig3)

    return out1, out2, out3


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python plot_vectors_from_excel.py <excel_path>")
        sys.exit(1)

    excel_path = Path(sys.argv[1]).expanduser().resolve()
    if not excel_path.exists():
        print(f"Input file not found: {excel_path}")
        sys.exit(2)

    out1, out2, out3 = make_quiver_plots(excel_path)
    print(f"Saved U horizontal: {out1}")
    print(f"Saved V vertical: {out2}")
    print(f"Saved Z resultant: {out3}")


if __name__ == "__main__":
    main()


