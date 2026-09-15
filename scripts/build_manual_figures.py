# -*- coding: utf-8 -*-
"""Publication-style figures from test/ Al–Cu–Li COST datasets."""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "manual_figures"
MR_DIR = ROOT / "test/Extract Thermo-calc Results-Melting Range/Al-Cu-Li_COST/exp"
T0_DIR = ROOT / "test/Extract Thermo-calc Results-T0/Al-Cu-Li_COST/exp"
LMG_DIR = ROOT / "test/Extract Thermo-calc Results-Miscibility Gap/Liquid/Al-Cu-Li_COST/exp"
GIBBS_DIR = ROOT / "test/Extract Thermo-calc Results-Gibbs/Al-Cu-Li_COST/exp"
PANDAT_CSV = ROOT / (
    "test/Extract Pandat Results-P Ts (Lever Scheil)/Al-Cu-Li_COST/"
    "All table_Lever/Solidification Simulation_5_Default.csv"
)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "legend.fontsize": 8,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.15,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,
    }
)


def _save(name: str):
    FIG.mkdir(parents=True, exist_ok=True)
    plt.savefig(FIG / name)
    plt.close("all")
    print("figure", name)


def _exp_xy_blocks(path: Path):
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    label, pts, collecting = None, [], False
    for raw in lines:
        s = raw.strip()
        m = re.match(r"^\$\s*PLOTTED\s+COLUMNS\s+ARE\s*:\s*(.+)$", s, re.I)
        if m:
            if label and pts:
                yield label, pts
            label, pts, collecting = m.group(1).strip(), [], True
            continue
        if collecting and s.startswith("BLOCKEND"):
            if label and pts:
                yield label, pts
            label, pts, collecting = None, [], False
            continue
        if collecting and s and not s.startswith("$") and not s.startswith("BLOCK"):
            parts = s.replace("M", "").split()
            if len(parts) >= 2:
                try:
                    pts.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    pass
    if label and pts:
        yield label, pts


def _mr_temps(path: Path):
    temps, fracs = [], []
    for _lab, pts in _exp_xy_blocks(path):
        for t, f in pts:
            temps.append(t)
            fracs.append(f)
    if not temps:
        return None, None, None, None
    data = np.column_stack([temps, fracs])
    order = np.argsort(data[:, 0])
    data = data[order]
    liq = data[(data[:, 1] >= 1.0 - 1e-8) & (data[:, 1] <= 1.0 + 1e-8)]
    sol = data[np.round(data[:, 1], 10) == 0.0]
    t_liq = float(np.min(liq[:, 0])) if len(liq) else None
    t_sol = float(np.max(sol[:, 0])) if len(sol) else None
    return data[:, 0], data[:, 1], t_liq, t_sol


def _parse_w_cu_li(stem: str):
    mcu = re.search(r"(\d+(?:\.\d+)?)Cu", stem, re.I)
    mli = re.search(r"(\d+(?:\.\d+)?)Li", stem, re.I)
    if not mcu or not mli:
        return None, None
    return float(mcu.group(1)), float(mli.group(1))


def fig_npliquid():
    path = MR_DIR / "Al0.050Cu0.010Li_np-T.exp"
    t, f, t_liq, t_sol = _mr_temps(path)
    fig, ax = plt.subplots(figsize=(6.3, 3.9))
    ax.plot(t, f, color="#1f4e79", lw=1.35)
    if t_liq is not None:
        ax.axvline(t_liq, color="#c45911", ls="--", lw=0.9, label=rf"$T_\mathrm{{L}}={t_liq:.1f}$ K")
    if t_sol is not None:
        ax.axvline(t_sol, color="#2e7d4f", ls="--", lw=0.9, label=rf"$T_\mathrm{{S}}={t_sol:.1f}$ K")
    ax.set_xlabel(r"$T$ (K)")
    ax.set_ylabel(r"NP(LIQUID)")
    ax.set_ylim(-0.03, 1.05)
    ax.legend(frameon=False, loc="center right")
    ax.set_title(r"Al–5 wt% Cu–1 wt% Li  (COST, file Al0.050Cu0.010Li_np-T.exp)")
    _save("03_mr_npliquid.png")


def fig_mr_maps():
    recs = []
    for p in MR_DIR.glob("*_np-T.exp"):
        wcu, wli = _parse_w_cu_li(p.stem)
        if wcu is None:
            continue
        _t, _f, t_liq, t_sol = _mr_temps(p)
        if t_liq is None or t_sol is None:
            continue
        recs.append((wcu, wli, t_liq, t_sol, t_liq - t_sol))
    recs = np.array(recs, dtype=float)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.85))
    specs = (
        (2, r"Liquidus $T_\mathrm{L}$ (K)", "viridis"),
        (4, r"Melting range $T_\mathrm{L}-T_\mathrm{S}$ (K)", "YlOrRd"),
    )
    for ax, (col, title, cmap) in zip(axes, specs):
        sc = ax.tricontourf(recs[:, 0], recs[:, 1], recs[:, col], levels=14, cmap=cmap)
        ax.plot(recs[:, 0], recs[:, 1], "k.", ms=1.4, alpha=0.35)
        cb = fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.05)
        cb.ax.tick_params(labelsize=8)
        ax.set_xlabel(r"$w(\mathrm{Cu})$")
        ax.set_ylabel(r"$w(\mathrm{Li})$")
        ax.set_title(title)
        ax.set_aspect("auto")
    fig.suptitle("Extract Thermo-calc Results → Melting Range   ·   Al–Cu–Li COST", y=1.02, fontsize=11)
    fig.tight_layout()
    _save("04_mr_heatmaps.png")
    return recs


def fig_t0():
    fig, ax = plt.subplots(figsize=(6.4, 4.05))
    cmap = plt.cm.viridis
    files = sorted(T0_DIR.glob("*_T0.exp"))
    pts_all = []
    n = max(len(files) - 1, 1)
    for i, p in enumerate(files):
        m = re.search(r"(\d+(?:\.\d+)?)Li", p.name, re.I)
        wli = float(m.group(1)) if m else 0.0
        pts = []
        for _lab, block in _exp_xy_blocks(p):
            pts.extend(block)
        if not pts:
            continue
        arr = np.array(pts)
        arr = arr[arr[:, 0].argsort()]
        ax.plot(arr[:, 0], arr[:, 1], color=cmap(i / n), lw=1.2, label=rf"$w(\mathrm{{Li}})={wli:g}$")
        for x, y in arr:
            pts_all.append((x, wli, y))
    ax.set_xlabel(r"$w(\mathrm{Cu})$")
    ax.set_ylabel(r"$T_0$ (K)")
    ax.set_title(r"T-zero lines  ·  Al–Cu–Li COST  (*_T0.exp)")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    _save("05_t0_lines.png")

    pts_all = np.array(pts_all)
    fig, ax = plt.subplots(figsize=(6.4, 4.15))
    try:
        from scipy.interpolate import griddata

        gx = np.linspace(pts_all[:, 0].min(), pts_all[:, 0].max(), 80)
        gy = np.linspace(pts_all[:, 1].min(), pts_all[:, 1].max(), 50)
        GX, GY = np.meshgrid(gx, gy)
        GZ = griddata(pts_all[:, :2], pts_all[:, 2], (GX, GY), method="linear")
        cs = ax.contourf(GX, GY, GZ, levels=16, cmap="plasma")
        ax.contour(GX, GY, GZ, levels=8, colors="k", linewidths=0.35, alpha=0.55)
        fig.colorbar(cs, ax=ax, pad=0.02, fraction=0.05, label=r"$T_0$ (K)")
    except Exception:
        sc = ax.scatter(pts_all[:, 0], pts_all[:, 1], c=pts_all[:, 2], cmap="plasma", s=12)
        fig.colorbar(sc, ax=ax, pad=0.02, fraction=0.05, label=r"$T_0$ (K)")
    ax.set_xlabel(r"$w(\mathrm{Cu})$")
    ax.set_ylabel(r"$w(\mathrm{Li})$")
    ax.set_title(r"Interpolated $T_0$ surface (same files as Extract → T-zero → Plot T-zero Surface)")
    _save("05b_t0_surface.png")


def fig_lmg():
    fig, ax = plt.subplots(figsize=(5.15, 5.05))
    temps = [600, 700, 800, 900]
    colors = ["#215c98", "#2e7d4f", "#c45911", "#9b2c2c"]
    for T, c in zip(temps, colors):
        p = LMG_DIR / f"AlCuLi_{T}.exp"
        xs, ys = [], []
        for _lab, pts in _exp_xy_blocks(p):
            for x, y in pts:
                xs.append(x)
                ys.append(y)
        ax.plot(xs, ys, ",", color=c, label=f"{T} K")
        # denser overlay of every 8th point for visibility
        ax.plot(xs[::6], ys[::6], ".", color=c, ms=2.2)
    ax.set_xlabel(r"mole % Cu")
    ax.set_ylabel(r"mole % Li")
    ax.set_title("Liquid miscibility gap  ·  Al–Cu–Li COST")
    ax.legend(frameon=False, markerscale=2.4, loc="upper right")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal", adjustable="box")
    _save("06_lmg_liquid.png")


def _gibbs_gmr_maps(path: Path):
    series = {}
    for lab, pts in _exp_xy_blocks(path):
        m = re.search(r"GMR\(([^)]+)\)", lab, re.I)
        key = m.group(1).upper() if m else lab
        arr = np.array(pts)
        if arr.size == 0:
            continue
        arr = arr[arr[:, 0].argsort()]
        series[key] = arr
    return series


def fig_gibbs_curve():
    path = GIBBS_DIR / "AlCu-0.050Li_650T_Gibbs.exp"
    series = _gibbs_gmr_maps(path)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for name, arr in series.items():
        if "LIQUID" in name:
            ax.plot(arr[:, 0], arr[:, 1] / 1000.0, color="#215c98", label="LIQUID")
        elif "FCC" in name and "#2" not in name:
            ax.plot(arr[:, 0], arr[:, 1] / 1000.0, color="#9b2c2c", label="FCC_A1")
    ax.set_xlabel(r"$w(\mathrm{Cu})$")
    ax.set_ylabel(r"GMR (kJ mol$^{-1}$)")
    ax.set_title(r"$T=650$ K,  $w(\mathrm{Li})=0.050$   (AlCu-0.050Li_650T_Gibbs.exp)")
    ax.legend(frameon=False)
    _save("07_gibbs_gmr.png")


def fig_dg_field():
    rows = []
    for p in sorted(GIBBS_DIR.glob("*_900T_Gibbs.exp")):
        m = re.search(r"(\d+(?:\.\d+)?)Li", p.name, re.I)
        wli = float(m.group(1)) if m else 0.0
        series = _gibbs_gmr_maps(p)
        liq = next((v for k, v in series.items() if "LIQUID" in k), None)
        sol = next((v for k, v in series.items() if "FCC" in k), None)
        if liq is None or sol is None:
            continue
        sol_map = {round(float(x), 8): float(g) for x, g in sol}
        for x, gl in liq:
            gs = sol_map.get(round(float(x), 8))
            if gs is None:
                continue
            rows.append((float(x), wli, float(gs) - float(gl)))
    rows = np.array(rows)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    try:
        from scipy.interpolate import griddata

        gx = np.linspace(rows[:, 0].min(), rows[:, 0].max(), 90)
        gy = np.linspace(rows[:, 1].min(), rows[:, 1].max(), 40)
        GX, GY = np.meshgrid(gx, gy)
        GZ = griddata(rows[:, :2], rows[:, 2] / 1000.0, (GX, GY), method="linear")
        vmax = np.nanmax(np.abs(GZ))
        cs = ax.contourf(GX, GY, GZ, levels=18, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.contour(GX, GY, GZ, levels=[0], colors="k", linewidths=1.4)
        fig.colorbar(cs, ax=ax, pad=0.02, fraction=0.05, label=r"$\Delta G=G_{\mathrm{FCC}}-G_{\mathrm{L}}$ (kJ mol$^{-1}$)")
    except Exception:
        sc = ax.scatter(rows[:, 0], rows[:, 1], c=rows[:, 2] / 1000.0, cmap="RdBu_r", s=8)
        fig.colorbar(sc, ax=ax, label=r"$\Delta G$ (kJ mol$^{-1}$)")
    ax.set_xlabel(r"$w(\mathrm{Cu})$")
    ax.set_ylabel(r"$w(\mathrm{Li})$")
    ax.set_title(r"TriST input field at 900 K from all *_900T_Gibbs.exp  (black: $\Delta G=0$)")
    _save("09_trist_schematic.png")


def fig_pandat():
    import pandas as pd

    df = pd.read_csv(PANDAT_CSV, sep="\t", skiprows=[1])
    t = pd.to_numeric(df["T"], errors="coerce")
    fs = pd.to_numeric(df["fs"], errors="coerce")
    k_li = pd.to_numeric(df["w(LI@FCC_A1)"], errors="coerce") / pd.to_numeric(df["w(LI@LIQUID)"], errors="coerce").replace(0, np.nan)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.7))
    axes[0].plot(t, fs, color="#1f4e79")
    axes[0].set_xlabel(r"$T$ (K)")
    axes[0].set_ylabel(r"$f_\mathrm{s}$")
    axes[0].set_title("Lever solid fraction")
    mask = np.isfinite(k_li) & (fs > 0) & (fs < 0.999)
    axes[1].plot(t[mask], k_li[mask], color="#9b2c2c")
    axes[1].axhline(1.0, color="0.5", ls="--", lw=0.7)
    axes[1].set_xlabel(r"$T$ (K)")
    axes[1].set_ylabel(r"$k(\mathrm{Li})=w(\mathrm{Li@FCC})/w(\mathrm{Li@LIQUID})$")
    axes[1].set_title("Partition coefficient")
    fig.suptitle(r"Pandat All table_Lever  ·  Al–5 wt% Li (0 Cu), COST", y=1.03, fontsize=11)
    fig.tight_layout()
    _save("08_pandat_lever.png")


def main():
    fig_npliquid()
    fig_mr_maps()
    fig_t0()
    fig_lmg()
    fig_gibbs_curve()
    fig_dg_field()
    fig_pandat()
    # remove cartoon figures if still present
    for old in ("01_workflow.png", "02_menus.png"):
        p = FIG / old
        if p.exists():
            p.unlink()
    print("done", FIG)


if __name__ == "__main__":
    main()
