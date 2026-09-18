# -*- coding: utf-8 -*-
"""Thermo-Calc Property Model Calculator — batch Data File generator.

Catalog follows Thermo-Calc 2026b General Models settings and
\"Working with Batch Calculations\" / \"About the Temperature Options for Property Models\".
Only numeric Param columns are written (phase / dropdown choices stay on the TC GUI).
"""

from __future__ import annotations

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import pandas as pd

from periodic_table import PERIODIC_TABLE


def _step_to_output_decimals(step):
    from decimal import Decimal

    try:
        d = Decimal(str(float(step))).normalize()
        if d == 0:
            return 8
        e = d.as_tuple().exponent
        return max(0, -e) if e < 0 else 0
    except Exception:
        return 8


def _composition_range_float64(lo, hi, step):
    lo, hi, step = float(lo), float(hi), float(step)
    if step <= 0:
        return np.array([lo], dtype=np.float64)
    out = []
    i = 0
    while True:
        x = lo + i * step
        if x > hi + 1e-12:
            break
        out.append(x)
        i += 1
        if i > 10_000_000:
            break
    return np.array(out, dtype=np.float64)


def _fmt_number(value, decimals):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if abs(v - round(v)) < 10 ** (-max(decimals, 0) - 2):
        return int(round(v))
    return round(v, decimals)


# ---------------------------------------------------------------------------
# General Models catalog (Thermo-Calc Property Model Calculator)
# ---------------------------------------------------------------------------
# temp_mode:
#   evaluation | annealing | freeze_in | start | none | custom_temperature_col
# sweep_temp_params: Param <name> columns filled from the temperature grid
# default_params: (Param name without \"Param \" prefix, default value or None)
# ---------------------------------------------------------------------------

TC_DATAFILE_MODELS = [
    {
        'id': 'custom_diffusion',
        'name_en': 'Custom / Diffusion (Temperature column)',
        'name_zh': '自定义 / 扩散系数（Temperature 列）',
        'blurb_en': (
            'Legacy layout used for mobility / diffusion batch grids: writes a Temperature '
            'column (plus Temperature unit), matching Ti–Al–Mn–1173K.xlsx style files.'
        ),
        'blurb_zh': (
            '扩散系数等批处理常用格式：写入 Temperature 列与 Temperature unit，'
            '与 Ti–Al–Mn–1173K.xlsx 一类文件一致。'
        ),
        'temp_mode': 'custom_temperature_col',
        'sweep_temp_params': [],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'coarsening',
        'name_en': 'Coarsening',
        'name_zh': '粗化 (Coarsening)',
        'blurb_en': (
            'Coarsening rate coefficient of a spherical precipitate. '
            'Batch numeric: Param Evaluation temperature. '
            'Select Matrix / Precipitate phases on the Thermo-Calc GUI.'
        ),
        'blurb_zh': (
            '球形析出相粗化速率系数。批处理数值列：Param Evaluation temperature。'
            '基体/析出相请在 Thermo-Calc 界面选择。'
        ),
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'cet',
        'name_en': 'Columnar to Equiaxed Transition (CET)',
        'name_zh': '柱状晶→等轴晶转变 (CET)',
        'blurb_en': (
            'CET from thermal gradient and growth rate. Numeric batch params: interfacial energy, '
            'nucleation sites/undercooling, equiaxed exponent, temperature gradient, growth rate. '
            'Primary phase is set on the GUI. Temperature grid optional (often composition-only).'
        ),
        'blurb_zh': (
            '由温度梯度与生长速率计算 CET。数值 Param：界面能、形核密度/过冷度、等轴指数、'
            '温度梯度、生长速率。初生相在 GUI 选择。温度网格可选（常仅扫成分）。'
        ),
        'temp_mode': 'none',
        'sweep_temp_params': [],
        'default_params': [
            ('Interfacial energy', 0.25),
            ('Number of nucleation sites', 2.0e15),
            ('Nucleation undercooling', 2.5),
            ('Equiaxed exponent', 3.0),
            ('Temperature gradient', 1000.0),
            ('Growth rate', 0.1),
        ],
        'needs_temp_grid': False,
    },
    {
        'id': 'crack_susceptibility',
        'name_en': 'Crack Susceptibility Coefficient',
        'name_zh': '裂纹敏感性系数 (CSC)',
        'blurb_en': (
            'Hot-tearing / crack susceptibility from Scheil results (Clyne–Davies, Kou, Easton). '
            'Batch: Param Start temperature. CSC model & Scheil options on the GUI.'
        ),
        'blurb_zh': (
            '基于 Scheil 的热裂/裂纹敏感性（Clyne–Davies、Kou、Easton）。'
            '批处理：Param Start temperature。CSC 模型与 Scheil 选项在 GUI 设置。'
        ),
        'temp_mode': 'start',
        'sweep_temp_params': ['Start temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'driving_force',
        'name_en': 'Driving Force',
        'name_zh': '驱动力 (Driving Force)',
        'blurb_en': (
            'Thermodynamic driving force for a phase. Batch: Param Evaluation temperature. '
            'Matrix / precipitate phases on the GUI.'
        ),
        'blurb_zh': (
            '相变热力学驱动力。批处理：Param Evaluation temperature。基体/析出相在 GUI 选择。'
        ),
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'equilibrium',
        'name_en': 'Equilibrium',
        'name_zh': '平衡 (Equilibrium)',
        'blurb_en': (
            'Single-equilibrium style Property Model. Batch: Param Evaluation temperature.'
        ),
        'blurb_zh': '单点平衡类性质模型。批处理：Param Evaluation temperature。',
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'equ_freeze_in',
        'name_en': 'Equilibrium with Freeze-in Temperature',
        'name_zh': '冻结温度平衡 (Freeze-in)',
        'blurb_en': (
            'Equilibrium at freeze-in T, properties at evaluation T. '
            'Batch sweeps Param Evaluation temperature; set Param Freeze-in temperature as a constant '
            '(or edit the Param table).'
        ),
        'blurb_zh': (
            '在冻结温度求平衡、在评价温度取性质。批处理扫描 Param Evaluation temperature；'
            'Param Freeze-in temperature 作常数（可在 Param 表中修改）。'
        ),
        'temp_mode': 'freeze_in',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [
            ('Freeze-in temperature', 800.0),
        ],
        'needs_temp_grid': True,
    },
    {
        'id': 'interfacial_energy',
        'name_en': 'Interfacial Energy',
        'name_zh': '界面能 (Interfacial Energy)',
        'blurb_en': (
            'Becker-type interfacial energy estimate. Batch: Param Evaluation temperature. '
            'Phases on the GUI.'
        ),
        'blurb_zh': 'Becker 型界面能估算。批处理：Param Evaluation temperature。相在 GUI 选择。',
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'liquidus_solidus',
        'name_en': 'Liquidus and Solidus Temperature',
        'name_zh': '液相线/固相线温度',
        'blurb_en': (
            'Equilibrium solidification range. Usually composition-only batch; numeric params: '
            'Low/High temperature limit, solid fraction, max. iterations. '
            'Liquid phase & checkboxes on the GUI.'
        ),
        'blurb_zh': (
            '平衡凝固区间。通常仅扫成分；数值 Param：低温/高温限、固相分数、最大迭代次数。'
            '液相与勾选项在 GUI 设置。'
        ),
        'temp_mode': 'none',
        'sweep_temp_params': [],
        'default_params': [
            ('Low temperature limit', 300.0),
            ('High temperature limit', 3000.0),
            ('Solid fraction for evaluating liquidus temperature', 0.001),
            ('Max. number of iterations', 10),
        ],
        'needs_temp_grid': False,
    },
    {
        'id': 'phase_transition',
        'name_en': 'Phase Transition',
        'name_zh': '相变点 (Phase Transition)',
        'blurb_en': (
            'Search phase transition by varying T or composition. '
            'Batch: Param Evaluation temperature (start of search when T is varied). '
            'Matrix / phase-to-form / search direction on the GUI.'
        ),
        'blurb_zh': (
            '变温或变成分搜索相变点。批处理：Param Evaluation temperature（变温搜索的起点）。'
            '基体/新相/搜索方向在 GUI 设置。'
        ),
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 'scheil',
        'name_en': 'Scheil',
        'name_zh': 'Scheil 凝固',
        'blurb_en': (
            'Scheil solidification Property Model. Batch: Param Start temperature '
            '(optional End temperature / Temperature below solidus as constants). '
            'Calculation type & advanced Scheil options on the GUI.'
        ),
        'blurb_zh': (
            'Scheil 凝固性质模型。批处理：Param Start temperature'
            '（End temperature / Temperature below solidus 可作为常数 Param）。'
            '计算类型与高级选项在 GUI 设置。'
        ),
        'temp_mode': 'start',
        'sweep_temp_params': ['Start temperature'],
        'default_params': [
            ('End temperature', 298.15),
        ],
        'needs_temp_grid': True,
    },
    {
        'id': 'spinodal',
        'name_en': 'Spinodal',
        'name_zh': '调幅分解 (Spinodal)',
        'blurb_en': (
            'Spinodal / miscibility-gap related Property Model. '
            'Batch: Param Evaluation temperature. Phase choices on the GUI.'
        ),
        'blurb_zh': '调幅/混溶隙相关模型。批处理：Param Evaluation temperature。相在 GUI 选择。',
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [],
        'needs_temp_grid': True,
    },
    {
        'id': 't_zero',
        'name_en': 'T-Zero Temperature',
        'name_zh': 'T0 温度 (T-Zero)',
        'blurb_en': (
            'T0 where two phases of equal composition have equal molar G. '
            'Batch: Param Evaluation temperature (search start when varying T). '
            'First/second phase & Energy addition on the GUI (Energy addition may also be a Param).'
        ),
        'blurb_zh': (
            '等成分两相摩尔 G 相等的 T0。批处理：Param Evaluation temperature（变温搜索起点）。'
            '第一/第二相在 GUI 选择；Energy addition 也可写入 Param。'
        ),
        'temp_mode': 'evaluation',
        'sweep_temp_params': ['Evaluation temperature'],
        'default_params': [
            ('Energy addition second phase', 0.0),
        ],
        'needs_temp_grid': True,
    },
    {
        'id': 'yield_strength',
        'name_en': 'Yield Strength',
        'name_zh': '屈服强度 (Yield Strength)',
        'blurb_en': (
            'Yield strength (simplified/advanced). Batch examples from Thermo-Calc docs: '
            'Param Annealing temperature, Param Evaluation temperature, '
            'Param Grain size, Param Critical radius (and Mean precipitate radius, etc.).'
        ),
        'blurb_zh': (
            '屈服强度。文档批处理示例：Param Annealing temperature、Param Evaluation temperature、'
            'Param Grain size、Param Critical radius（及平均析出半径等）。'
        ),
        'temp_mode': 'annealing',
        'sweep_temp_params': ['Annealing temperature'],
        'default_params': [
            ('Evaluation temperature', 298.15),
            ('Grain size', 50.0),
            ('Critical radius', 1.0e-8),
            ('Mean precipitate radius', 1.0e-8),
            ('Constant strength addition', 0.0),
        ],
        'needs_temp_grid': True,
    },
]


def model_by_id(model_id):
    for m in TC_DATAFILE_MODELS:
        if m['id'] == model_id:
            return m
    return TC_DATAFILE_MODELS[0]


def model_display_name(model, lang='en'):
    return model['name_zh'] if lang == 'zh' else model['name_en']


def model_blurb(model, lang='en'):
    return model['blurb_zh'] if lang == 'zh' else model['blurb_en']


def build_frames(
    bal_el,
    sweep_cfgs,
    temps,
    comp_unit,
    temp_unit,
    extra_cols,
    *,
    uppercase_el=False,
    write_temperature_col=False,
    sweep_temp_param_names=None,
    constrain_sum=True,
    exclude_zeros=True,
):
    """
    Returns (valid_combos, temps, rows_for_temp_fn, columns).
    sweep_temp_param_names: list of GUI parameter names (without \"Param \" prefix)
    that receive the temperature-grid value each row.
    """
    sweep_temp_param_names = list(sweep_temp_param_names or [])

    def _hdr(el):
        return el.upper() if uppercase_el else el

    bal_hdr = _hdr(bal_el)
    sweep_hdrs = [_hdr(c['element']) for c in sweep_cfgs]
    out_decimals = 2
    if sweep_cfgs:
        out_decimals = max(_step_to_output_decimals(c['step']) for c in sweep_cfgs)
        out_decimals = min(max(out_decimals, 0), 12)

    ranges = [
        _composition_range_float64(c['min'], c['max'], c['step'])
        for c in sweep_cfgs
    ]
    if ranges:
        mesh = np.meshgrid(*ranges, indexing='ij')
        combos = np.stack([m.flatten() for m in mesh], axis=1)
    else:
        combos = np.zeros((1, 0), dtype=np.float64)

    unit_total = 100.0 if 'pct' in (comp_unit or '').lower() else 1.0
    valid = []
    for combo in combos:
        s = float(np.sum(combo)) if len(combo) else 0.0
        if constrain_sum and s > unit_total + 1e-9:
            continue
        if exclude_zeros and len(combo) and np.all(np.abs(combo) < 1e-12):
            continue
        valid.append(combo)

    if not valid:
        return [], [], None, []

    temps = list(temps) if temps else [None]
    t_decimals = 0
    numeric_temps = [float(t) for t in temps if t is not None]
    if len(numeric_temps) >= 2:
        diffs = np.diff(sorted(numeric_temps))
        diffs = diffs[diffs > 1e-12]
        if len(diffs):
            t_decimals = min(max(_step_to_output_decimals(float(diffs.min())), 0), 12)
    elif numeric_temps:
        t_decimals = min(max(_step_to_output_decimals(float(numeric_temps[0])), 0), 12)

    base_cols = ['ID', bal_hdr] + sweep_hdrs + ['Composition unit', 'Temperature unit']
    if write_temperature_col:
        # insert Temperature before Temperature unit (matches DC_batch-ish layout)
        base_cols = ['ID', bal_hdr] + sweep_hdrs + [
            'Composition unit', 'Temperature', 'Temperature unit'
        ]

    sweep_headers = [f'Param {n}' for n in sweep_temp_param_names]
    extra_headers = [h for h, _ in extra_cols]
    # avoid duplicating a sweep temp param if user also listed it in extras
    extra_headers = [h for h in extra_headers if h not in sweep_headers]
    columns = base_cols + sweep_headers + extra_headers

    def _rows_for_temp(t_val):
        rows = []
        for i, combo in enumerate(valid, start=1):
            row = {
                'ID': i,
                bal_hdr: 'Bal',
                'Composition unit': comp_unit,
                'Temperature unit': temp_unit,
            }
            if write_temperature_col:
                row['Temperature'] = (
                    _fmt_number(t_val, t_decimals) if t_val is not None else ''
                )
            for j, h in enumerate(sweep_hdrs):
                row[h] = _fmt_number(combo[j], out_decimals)
            if t_val is not None:
                for ph in sweep_headers:
                    row[ph] = _fmt_number(t_val, t_decimals)
            for h, v in extra_cols:
                if h in sweep_headers:
                    continue
                row[h] = v
            rows.append(row)
        return pd.DataFrame(rows, columns=columns)

    return valid, temps, _rows_for_temp, columns


# Keep old name for any external callers / tests
_tc_datafile_build_frames = build_frames
_tc_datafile_fmt_number = _fmt_number


def open_tc_datafile_generator(app):
    """UI entry: app is ThermoQApp (needs .root, .tr, language helpers)."""
    win = tk.Toplevel(app.root)
    win.geometry('980x960')
    win.minsize(760, 680)
    app._present_tool_window(win, app.root)

    main_frame, canvas, _scroll_unbind = app._build_tool_window_scroll_area(
        win, padx=10, pady=10
    )

    title_label = ttk.Label(
        main_frame,
        text=app.tr('tcdata_heading', 'Thermo-Calc Batch Data File Generator'),
        font=('Arial', 14, 'bold'),
    )
    title_label.pack(pady=(0, 4))

    info_label = ttk.Label(
        main_frame,
        text=app.tr('tcdata_intro_models', app.tr('tcdata_intro', '')),
        wraplength=900,
        justify='left',
    )
    info_label.pack(pady=(0, 8), fill=tk.X)

    def _on_cfg_w(event):
        if event.width > 100:
            info_label.configure(wraplength=max(480, event.width - 60))
            model_blurb_lbl.configure(wraplength=max(360, event.width - 280))

    main_frame.bind('<Configure>', _on_cfg_w, add='+')

    # ----- Model selection -----
    model_frame = ttk.LabelFrame(
        main_frame, text=app.tr('tcdata_model_frame', 'General Model'), padding='10'
    )
    model_frame.pack(fill=tk.X, pady=5)

    model_row = ttk.Frame(model_frame)
    model_row.pack(fill=tk.BOTH, expand=True)

    model_list = tk.Listbox(model_row, height=8, exportselection=False, width=42)
    model_list.pack(side=tk.LEFT, fill=tk.Y)
    model_sb = ttk.Scrollbar(model_row, orient=tk.VERTICAL, command=model_list.yview)
    model_sb.pack(side=tk.LEFT, fill=tk.Y)
    model_list.configure(yscrollcommand=model_sb.set)

    model_right = ttk.Frame(model_row)
    model_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
    model_blurb_lbl = ttk.Label(model_right, text='', wraplength=560, justify='left')
    model_blurb_lbl.pack(anchor=tk.NW, fill=tk.X)
    temp_hint_lbl = ttk.Label(model_right, text='', wraplength=560, foreground='#445566')
    temp_hint_lbl.pack(anchor=tk.NW, fill=tk.X, pady=(8, 0))

    state = {'model_id': TC_DATAFILE_MODELS[0]['id']}

    def _lang():
        return getattr(app, 'language', 'en')

    def _refill_model_list(keep_id=None):
        keep_id = keep_id or state['model_id']
        model_list.delete(0, tk.END)
        sel = 0
        for i, m in enumerate(TC_DATAFILE_MODELS):
            model_list.insert(tk.END, model_display_name(m, _lang()))
            if m['id'] == keep_id:
                sel = i
        model_list.selection_clear(0, tk.END)
        model_list.selection_set(sel)
        model_list.see(sel)
        state['model_id'] = TC_DATAFILE_MODELS[sel]['id']
        _apply_model()

    def _current_model():
        return model_by_id(state['model_id'])

    def _temp_hint_text(m):
        mode = m.get('temp_mode')
        sweeps = m.get('sweep_temp_params') or []
        if mode == 'custom_temperature_col':
            return app.tr(
                'tcdata_temp_hint_custom',
                'Temperature grid → Temperature column (+ Temperature unit).',
            )
        if mode == 'none' or not sweeps:
            return app.tr(
                'tcdata_temp_hint_none',
                'No temperature sweep column (composition-only batch is typical). '
                'Optional temperature grid is ignored unless you add Param columns manually.',
            )
        names = ', '.join(f'Param {n}' for n in sweeps)
        return app.tr(
            'tcdata_temp_hint_param',
            'Temperature grid → {names} (Temperature unit column always written).',
        ).format(names=names)

    def _apply_model():
        m = _current_model()
        model_blurb_lbl.config(text=model_blurb(m, _lang()))
        temp_hint_lbl.config(text=_temp_hint_text(m))
        # reload default params into tree (replace only auto rows tagged)
        for item in list(params_tree.get_children()):
            tags = params_tree.item(item, 'tags')
            if 'auto' in tags:
                params_tree.delete(item)
        for name, val in m.get('default_params') or []:
            params_tree.insert(
                '', tk.END, values=(f'Param {name}', val), tags=('auto',)
            )
        needs = bool(m.get('needs_temp_grid', True))
        if needs:
            temp_frame.pack(fill=tk.X, pady=5, after=units_frame)
        else:
            # still allow optional T; keep visible but note optional
            temp_frame.pack(fill=tk.X, pady=5, after=units_frame)

    def _on_model_select(_evt=None):
        sel = model_list.curselection()
        if not sel:
            return
        state['model_id'] = TC_DATAFILE_MODELS[sel[0]]['id']
        _apply_model()

    model_list.bind('<<ListboxSelect>>', _on_model_select)

    # ----- Elements -----
    elements_frame = ttk.LabelFrame(
        main_frame, text=app.tr('tcdata_elem_cfg', 'Element Configuration'), padding='10'
    )
    elements_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    list_frame = ttk.Frame(elements_frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    elements_tree = ttk.Treeview(
        list_frame,
        columns=('Element', 'Role', 'Min', 'Max', 'Step'),
        show='headings',
        height=5,
    )
    for col, key, w in (
        ('Element', 'tcdata_tbl_element', 90),
        ('Role', 'tcdata_tbl_role', 120),
        ('Min', 'tcdata_tbl_min', 80),
        ('Max', 'tcdata_tbl_max', 80),
        ('Step', 'tcdata_tbl_step', 80),
    ):
        elements_tree.heading(col, text=app.tr(key, col))
        elements_tree.column(col, width=w, minwidth=50, stretch=True)
    elements_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    el_sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=elements_tree.yview)
    el_sb.pack(side=tk.RIGHT, fill=tk.Y)
    elements_tree.configure(yscrollcommand=el_sb.set)

    add_row = ttk.Frame(elements_frame)
    add_row.pack(fill=tk.X, pady=4)

    lbl_el = ttk.Label(add_row, text=app.tr('tcdata_lbl_element', 'Element:'))
    lbl_el.pack(side=tk.LEFT, padx=4)
    element_var = tk.StringVar()
    element_combo = ttk.Combobox(
        add_row, textvariable=element_var, values=sorted(PERIODIC_TABLE.keys()), width=8
    )
    element_combo.pack(side=tk.LEFT, padx=4)

    lbl_min = ttk.Label(add_row, text=app.tr('tcdata_lbl_min', 'Min:'))
    lbl_min.pack(side=tk.LEFT, padx=4)
    min_var = tk.StringVar(value='1')
    ttk.Entry(add_row, textvariable=min_var, width=8).pack(side=tk.LEFT, padx=2)
    lbl_max = ttk.Label(add_row, text=app.tr('tcdata_lbl_max', 'Max:'))
    lbl_max.pack(side=tk.LEFT, padx=4)
    max_var = tk.StringVar(value='25')
    ttk.Entry(add_row, textvariable=max_var, width=8).pack(side=tk.LEFT, padx=2)
    lbl_step = ttk.Label(add_row, text=app.tr('tcdata_lbl_step', 'Step:'))
    lbl_step.pack(side=tk.LEFT, padx=4)
    step_var = tk.StringVar(value='1')
    ttk.Entry(add_row, textvariable=step_var, width=8).pack(side=tk.LEFT, padx=2)

    as_bal_var = tk.BooleanVar(value=False)
    cb_as_bal = ttk.Checkbutton(
        add_row, text=app.tr('tcdata_as_balance', 'Add as Balance (Bal)'), variable=as_bal_var
    )
    cb_as_bal.pack(side=tk.LEFT, padx=8)

    btn_row = ttk.Frame(elements_frame)
    btn_row.pack(fill=tk.X, pady=2)

    def _role_labels():
        return (
            app.tr('tcdata_role_bal', 'Balance (Bal)'),
            app.tr('tcdata_role_sweep', 'Sweep'),
        )

    def _canon_el(raw):
        s = (raw or '').strip()
        if not s:
            return None
        for k in PERIODIC_TABLE:
            if k.upper() == s.upper():
                return k
        return None

    def add_element():
        el = _canon_el(element_var.get())
        if not el:
            messagebox.showerror(
                app.tr('dlg_error', 'Error'),
                app.tr('tcdata_err_element', 'Invalid element or numeric range.'),
            )
            return
        for item in elements_tree.get_children():
            if str(elements_tree.item(item)['values'][0]).upper() == el.upper():
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_err_dup', 'Element already in the list: {el}').format(el=el),
                )
                return
        bal_lbl, sweep_lbl = _role_labels()
        if as_bal_var.get():
            for item in elements_tree.get_children():
                vals = list(elements_tree.item(item)['values'])
                if vals[1] == bal_lbl or str(vals[1]).lower().startswith('bal') or '平衡' in str(vals[1]):
                    vals[1] = sweep_lbl
                    if vals[2] in ('', '-', None) or str(vals[2]).lower() == 'bal':
                        vals[2], vals[3], vals[4] = '1', '25', '1'
                    elements_tree.item(item, values=vals)
            elements_tree.insert('', 0, values=(el, bal_lbl, '-', '-', '-'))
            as_bal_var.set(False)
        else:
            try:
                lo, hi, st = float(min_var.get()), float(max_var.get()), float(step_var.get())
                if st <= 0 or lo > hi:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_err_element', 'Invalid element or numeric range.'),
                )
                return
            elements_tree.insert('', tk.END, values=(el, sweep_lbl, lo, hi, st))

    def remove_element():
        for item in elements_tree.selection():
            elements_tree.delete(item)

    def set_selected_bal():
        sel = elements_tree.selection()
        if not sel:
            return
        bal_lbl, sweep_lbl = _role_labels()
        target = sel[0]
        for item in elements_tree.get_children():
            vals = list(elements_tree.item(item)['values'])
            if item == target:
                vals[1] = bal_lbl
                vals[2], vals[3], vals[4] = '-', '-', '-'
            elif vals[1] == bal_lbl or str(vals[1]).lower().startswith('bal') or '平衡' in str(vals[1]):
                vals[1] = sweep_lbl
                if vals[2] in ('', '-', None):
                    vals[2], vals[3], vals[4] = '1', '25', '1'
            elements_tree.item(item, values=vals)
        vals = elements_tree.item(target)['values']
        elements_tree.delete(target)
        elements_tree.insert('', 0, values=vals)

    btn_add = ttk.Button(btn_row, text=app.tr('tcdata_add', 'Add Element'), command=add_element)
    btn_add.pack(side=tk.LEFT, padx=4)
    btn_remove = ttk.Button(
        btn_row, text=app.tr('tcdata_remove', 'Remove Selected'), command=remove_element
    )
    btn_remove.pack(side=tk.LEFT, padx=4)
    btn_set_bal = ttk.Button(
        btn_row, text=app.tr('tcdata_set_bal', 'Set Selected as Balance'), command=set_selected_bal
    )
    btn_set_bal.pack(side=tk.LEFT, padx=4)

    # ----- Units -----
    units_frame = ttk.LabelFrame(main_frame, text=app.tr('tcdata_units', 'Units'), padding='10')
    units_frame.pack(fill=tk.X, pady=5)
    urow = ttk.Frame(units_frame)
    urow.pack(fill=tk.X)
    lbl_cu = ttk.Label(urow, text=app.tr('tcdata_comp_unit', 'Composition unit:'))
    lbl_cu.pack(side=tk.LEFT, padx=4)
    comp_unit_var = tk.StringVar(value='mole_pct')
    ttk.Combobox(
        urow,
        textvariable=comp_unit_var,
        values=('mole_pct', 'mole_frac', 'mass_pct', 'mass_frac'),
        width=12,
        state='readonly',
    ).pack(side=tk.LEFT, padx=4)
    lbl_tu = ttk.Label(urow, text=app.tr('tcdata_temp_unit', 'Temperature unit:'))
    lbl_tu.pack(side=tk.LEFT, padx=12)
    temp_unit_var = tk.StringVar(value='K')
    ttk.Combobox(
        urow, textvariable=temp_unit_var, values=('K', 'C', 'F'), width=6, state='readonly'
    ).pack(side=tk.LEFT, padx=4)

    # ----- Temperature -----
    temp_frame = ttk.LabelFrame(main_frame, text=app.tr('tcdata_temp_cfg', 'Temperature'), padding='10')
    temp_frame.pack(fill=tk.X, pady=5)

    temp_mode_var = tk.StringVar(value='single')
    mrow = ttk.Frame(temp_frame)
    mrow.pack(fill=tk.X)
    lbl_tmode = ttk.Label(mrow, text=app.tr('tcdata_temp_mode', 'Mode:'))
    lbl_tmode.pack(side=tk.LEFT, padx=4)
    rb_single = ttk.Radiobutton(
        mrow, text=app.tr('tcdata_temp_single', 'Single value'), variable=temp_mode_var, value='single'
    )
    rb_single.pack(side=tk.LEFT, padx=4)
    rb_range = ttk.Radiobutton(
        mrow, text=app.tr('tcdata_temp_range', 'Range'), variable=temp_mode_var, value='range'
    )
    rb_range.pack(side=tk.LEFT, padx=4)
    rb_list = ttk.Radiobutton(
        mrow, text=app.tr('tcdata_temp_list', 'List'), variable=temp_mode_var, value='list'
    )
    rb_list.pack(side=tk.LEFT, padx=4)
    rb_none = ttk.Radiobutton(
        mrow, text=app.tr('tcdata_temp_none', 'None (composition only)'), variable=temp_mode_var, value='none'
    )
    rb_none.pack(side=tk.LEFT, padx=4)

    single_fr = ttk.Frame(temp_frame)
    range_fr = ttk.Frame(temp_frame)
    list_fr = ttk.Frame(temp_frame)

    lbl_tv = ttk.Label(single_fr, text=app.tr('tcdata_temp_value', 'T:'))
    lbl_tv.pack(side=tk.LEFT, padx=4)
    t_single_var = tk.StringVar(value='1173')
    ttk.Entry(single_fr, textvariable=t_single_var, width=12).pack(side=tk.LEFT, padx=4)

    lbl_tmin = ttk.Label(range_fr, text=app.tr('tcdata_temp_min', 'T min:'))
    lbl_tmin.pack(side=tk.LEFT, padx=4)
    t_min_var = tk.StringVar(value='1173')
    ttk.Entry(range_fr, textvariable=t_min_var, width=10).pack(side=tk.LEFT, padx=2)
    lbl_tmax = ttk.Label(range_fr, text=app.tr('tcdata_temp_max', 'T max:'))
    lbl_tmax.pack(side=tk.LEFT, padx=8)
    t_max_var = tk.StringVar(value='1573')
    ttk.Entry(range_fr, textvariable=t_max_var, width=10).pack(side=tk.LEFT, padx=2)
    lbl_tstep = ttk.Label(range_fr, text=app.tr('tcdata_temp_step', 'T step:'))
    lbl_tstep.pack(side=tk.LEFT, padx=8)
    t_step_var = tk.StringVar(value='100')
    ttk.Entry(range_fr, textvariable=t_step_var, width=10).pack(side=tk.LEFT, padx=2)

    lbl_tlist = ttk.Label(list_fr, text=app.tr('tcdata_temp_list_lbl', 'T list:'))
    lbl_tlist.pack(side=tk.LEFT, padx=4)
    t_list_var = tk.StringVar(value='1173, 1273, 1373, 1473, 1573')
    ttk.Entry(list_fr, textvariable=t_list_var, width=50).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)

    def _sync_temp_mode(*_a):
        single_fr.pack_forget()
        range_fr.pack_forget()
        list_fr.pack_forget()
        mode = temp_mode_var.get()
        if mode == 'range':
            range_fr.pack(fill=tk.X, pady=4)
        elif mode == 'list':
            list_fr.pack(fill=tk.X, pady=4)
        elif mode == 'none':
            pass
        else:
            single_fr.pack(fill=tk.X, pady=4)

    temp_mode_var.trace_add('write', _sync_temp_mode)
    _sync_temp_mode()

    one_file_per_t_var = tk.BooleanVar(value=True)
    cb_one_t = ttk.Checkbutton(
        temp_frame,
        text=app.tr('tcdata_one_file_per_t', 'One file per temperature'),
        variable=one_file_per_t_var,
    )
    cb_one_t.pack(anchor=tk.W, pady=2)

    uppercase_el_var = tk.BooleanVar(value=True)
    cb_upper = ttk.Checkbutton(
        temp_frame,
        text=app.tr('tcdata_uppercase_el', 'Uppercase element symbols in header'),
        variable=uppercase_el_var,
    )
    cb_upper.pack(anchor=tk.W, pady=2)

    # ----- Param / Exp -----
    params_frame = ttk.LabelFrame(
        main_frame, text=app.tr('tcdata_params', 'Param / Exp Columns'), padding='10'
    )
    params_frame.pack(fill=tk.X, pady=5)
    param_hint = ttk.Label(
        params_frame, text=app.tr('tcdata_param_hint', ''), wraplength=900, justify='left'
    )
    param_hint.pack(fill=tk.X, pady=(0, 4))

    param_list_fr = ttk.Frame(params_frame)
    param_list_fr.pack(fill=tk.X)
    params_tree = ttk.Treeview(
        param_list_fr, columns=('Header', 'Value'), show='headings', height=4
    )
    params_tree.heading('Header', text=app.tr('tcdata_tbl_header', 'Header'))
    params_tree.heading('Value', text=app.tr('tcdata_tbl_value', 'Value'))
    params_tree.column('Header', width=320, stretch=True)
    params_tree.column('Value', width=120, stretch=True)
    params_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
    p_sb = ttk.Scrollbar(param_list_fr, orient=tk.VERTICAL, command=params_tree.yview)
    p_sb.pack(side=tk.RIGHT, fill=tk.Y)
    params_tree.configure(yscrollcommand=p_sb.set)

    prow = ttk.Frame(params_frame)
    prow.pack(fill=tk.X, pady=4)
    lbl_pk = ttk.Label(prow, text=app.tr('tcdata_param_kind', 'Kind:'))
    lbl_pk.pack(side=tk.LEFT, padx=4)
    param_kind_var = tk.StringVar(value='Param')
    ttk.Combobox(
        prow, textvariable=param_kind_var, values=('Param', 'Exp'), width=8, state='readonly'
    ).pack(side=tk.LEFT, padx=2)
    lbl_pn = ttk.Label(prow, text=app.tr('tcdata_param_name', 'Name:'))
    lbl_pn.pack(side=tk.LEFT, padx=4)
    param_name_var = tk.StringVar()
    ttk.Entry(prow, textvariable=param_name_var, width=22).pack(side=tk.LEFT, padx=2)
    lbl_pv = ttk.Label(prow, text=app.tr('tcdata_param_value', 'Value:'))
    lbl_pv.pack(side=tk.LEFT, padx=4)
    param_value_var = tk.StringVar()
    ttk.Entry(prow, textvariable=param_value_var, width=12).pack(side=tk.LEFT, padx=2)

    def add_param_col():
        kind = param_kind_var.get().strip() or 'Param'
        name = param_name_var.get().strip()
        if not name:
            return
        header = f'{kind} {name}'.strip()
        try:
            val = float(param_value_var.get().strip())
        except ValueError:
            messagebox.showerror(
                app.tr('dlg_error', 'Error'),
                app.tr('tcdata_err_element', 'Invalid element or numeric range.'),
            )
            return
        params_tree.insert('', tk.END, values=(header, val), tags=('user',))
        param_name_var.set('')
        param_value_var.set('')

    def remove_param_col():
        for item in params_tree.selection():
            params_tree.delete(item)

    btn_padd = ttk.Button(prow, text=app.tr('tcdata_param_add', 'Add Column'), command=add_param_col)
    btn_padd.pack(side=tk.LEFT, padx=6)
    btn_prem = ttk.Button(
        prow, text=app.tr('tcdata_param_remove', 'Remove Selected'), command=remove_param_col
    )
    btn_prem.pack(side=tk.LEFT, padx=4)

    # ----- Constraints / Output -----
    cons_frame = ttk.LabelFrame(
        main_frame, text=app.tr('tcdata_constraints', 'Constraints'), padding='10'
    )
    cons_frame.pack(fill=tk.X, pady=5)
    constrain_sum_var = tk.BooleanVar(value=True)
    cb_sum = ttk.Checkbutton(
        cons_frame,
        text=app.tr('tcdata_sum_limit', 'Drop rows where Σ(non-Bal) exceeds unit total'),
        variable=constrain_sum_var,
    )
    cb_sum.pack(anchor=tk.W)
    exclude_zeros_var = tk.BooleanVar(value=True)
    cb_zero = ttk.Checkbutton(
        cons_frame,
        text=app.tr('tcdata_exclude_zeros', 'Exclude all-zero non-Bal compositions'),
        variable=exclude_zeros_var,
    )
    cb_zero.pack(anchor=tk.W)

    out_frame = ttk.LabelFrame(main_frame, text=app.tr('tcdata_output', 'Output'), padding='10')
    out_frame.pack(fill=tk.X, pady=5)
    orow = ttk.Frame(out_frame)
    orow.pack(fill=tk.X, pady=2)
    lbl_od = ttk.Label(orow, text=app.tr('tcdata_out_dir', 'Output folder:'))
    lbl_od.pack(side=tk.LEFT, padx=4)
    out_dir_var = tk.StringVar()
    ttk.Entry(orow, textvariable=out_dir_var, width=55).pack(
        side=tk.LEFT, padx=4, fill=tk.X, expand=True
    )

    def browse_out():
        p = filedialog.askdirectory(title=app.tr('tcdata_fd_out', 'Select output folder'))
        if p:
            out_dir_var.set(p)

    btn_obrowse = ttk.Button(orow, text=app.tr('pandat_browse', 'Browse'), command=browse_out)
    btn_obrowse.pack(side=tk.LEFT, padx=4)

    frow = ttk.Frame(out_frame)
    frow.pack(fill=tk.X, pady=2)
    lbl_fmt = ttk.Label(frow, text=app.tr('tcdata_out_fmt', 'Format:'))
    lbl_fmt.pack(side=tk.LEFT, padx=4)
    fmt_var = tk.StringVar(value='xlsx')
    ttk.Combobox(
        frow, textvariable=fmt_var, values=('xlsx', 'csv', 'both'), width=10, state='readonly'
    ).pack(side=tk.LEFT, padx=4)

    nrow = ttk.Frame(out_frame)
    nrow.pack(fill=tk.X, pady=2)
    lbl_pat = ttk.Label(nrow, text=app.tr('tcdata_name_pattern', 'Name pattern:'))
    lbl_pat.pack(side=tk.LEFT, padx=4)
    name_pat_var = tk.StringVar(value='{sys}-{T}{Tu}')
    ttk.Entry(nrow, textvariable=name_pat_var, width=30).pack(side=tk.LEFT, padx=4)
    name_hint = ttk.Label(
        nrow, text=app.tr('tcdata_name_hint', '{sys} / {T} / {Tu}'), foreground='#555'
    )
    name_hint.pack(side=tk.LEFT, padx=6)

    status_label = ttk.Label(
        main_frame, text=app.tr('tcdata_ready', 'Ready to generate'), foreground='blue'
    )
    status_label.pack(pady=8)

    def _parse_elements():
        bal_lbl = app.tr('tcdata_role_bal', 'Balance (Bal)')
        bal_el = None
        sweep = []
        for item in elements_tree.get_children():
            vals = elements_tree.item(item)['values']
            el = _canon_el(str(vals[0]))
            if not el:
                continue
            role = str(vals[1])
            is_bal = role == bal_lbl or role.lower().startswith('bal') or '平衡' in role
            if is_bal:
                bal_el = el
            else:
                sweep.append({
                    'element': el,
                    'min': float(vals[2]),
                    'max': float(vals[3]),
                    'step': float(vals[4]),
                })
        return bal_el, sweep

    def _parse_temps():
        mode = temp_mode_var.get()
        if mode == 'none':
            return [None]
        if mode == 'range':
            lo, hi, st = float(t_min_var.get()), float(t_max_var.get()), float(t_step_var.get())
            if st <= 0 or lo > hi:
                raise ValueError('bad T')
            return list(_composition_range_float64(lo, hi, st))
        if mode == 'list':
            parts = re.split(r'[,;\s]+', t_list_var.get().strip())
            vals = [float(p) for p in parts if p]
            if not vals:
                raise ValueError('bad T')
            return vals
        return [float(t_single_var.get())]

    def _extra_cols():
        out = []
        for item in params_tree.get_children():
            h, v = params_tree.item(item)['values']
            try:
                out.append((str(h), float(v)))
            except (TypeError, ValueError):
                out.append((str(h), v))
        return out

    def _sys_name(bal_el, sweep, uppercase):
        els = [bal_el] + [c['element'] for c in sweep]
        if uppercase:
            els = [e.upper() for e in els]
        return '-'.join(els)

    def _build_stem(pattern, sys_name, t_val, tu, one_per_t):
        pat = (pattern or '{sys}-{T}{Tu}').strip()
        t_txt = ''
        if t_val is not None and one_per_t:
            t_txt = f'{_fmt_number(t_val, 6)}'
        stem = (
            pat.replace('{sys}', sys_name)
            .replace('{T}', t_txt)
            .replace('{Tu}', tu if (t_val is not None and one_per_t) else '')
        )
        stem = re.sub(r'-{2,}', '-', stem).strip('-_ ')
        return stem or sys_name

    def _export_kwargs():
        m = _current_model()
        write_tcol = m.get('temp_mode') == 'custom_temperature_col'
        sweep_names = list(m.get('sweep_temp_params') or [])
        return write_tcol, sweep_names

    def preview_count():
        try:
            bal_el, sweep = _parse_elements()
            if not bal_el:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_need_bal', 'Please add exactly one Balance (Bal) element.'),
                )
                return
            if not sweep:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_need_sweep', 'Please add at least one swept element.'),
                )
                return
            temps = _parse_temps()
        except Exception:
            messagebox.showerror(
                app.tr('dlg_error', 'Error'),
                app.tr('tcdata_need_temp', 'Please enter a valid temperature configuration.'),
            )
            return
        write_tcol, sweep_names = _export_kwargs()
        # if no temp values and model needs sweep params, treat as one composition-only pass
        if temps == [None]:
            sweep_names = []
        valid, temps, _fn, _cols = build_frames(
            bal_el,
            sweep,
            temps,
            comp_unit_var.get(),
            temp_unit_var.get(),
            _extra_cols(),
            uppercase_el=uppercase_el_var.get(),
            write_temperature_col=write_tcol,
            sweep_temp_param_names=sweep_names,
            constrain_sum=constrain_sum_var.get(),
            exclude_zeros=exclude_zeros_var.get(),
        )
        ncomp = len(valid)
        nt = len([t for t in temps if t is not None]) or 1
        if one_file_per_t_var.get() and any(t is not None for t in temps):
            nfile, nrows = len([t for t in temps if t is not None]), ncomp * nt
        else:
            nfile, nrows = (1 if ncomp else 0), ncomp * nt
        msg = app.tr(
            'tcdata_preview_msg',
            '{ncomp} composition(s) × {nt} temperature(s) → {nrows} row(s); {nfile} file(s).',
        ).format(ncomp=ncomp, nt=nt, nrows=nrows, nfile=nfile)
        status_label.config(text=msg, foreground='blue')
        messagebox.showinfo(app.tr('tcdata_preview', 'Preview'), msg)

    def generate():
        try:
            bal_el, sweep = _parse_elements()
            if not bal_el:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_need_bal', 'Please add exactly one Balance (Bal) element.'),
                )
                return
            if not sweep:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_need_sweep', 'Please add at least one swept element.'),
                )
                return
            try:
                temps = _parse_temps()
            except Exception:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_need_temp', 'Please enter a valid temperature configuration.'),
                )
                return
            out_dir = out_dir_var.get().strip()
            if not out_dir or not os.path.isdir(out_dir):
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_need_outdir', 'Please select a valid output folder.'),
                )
                return

            status_label.config(
                text=app.tr('tcdata_generating', 'Generating…'), foreground='orange'
            )
            win.update()

            write_tcol, sweep_names = _export_kwargs()
            if temps == [None]:
                sweep_names = []

            valid, temps, rows_for_temp, _cols = build_frames(
                bal_el,
                sweep,
                temps,
                comp_unit_var.get(),
                temp_unit_var.get(),
                _extra_cols(),
                uppercase_el=uppercase_el_var.get(),
                write_temperature_col=write_tcol,
                sweep_temp_param_names=sweep_names,
                constrain_sum=constrain_sum_var.get(),
                exclude_zeros=exclude_zeros_var.get(),
            )
            if not valid:
                messagebox.showerror(
                    app.tr('dlg_error', 'Error'),
                    app.tr('tcdata_no_rows', 'No valid composition rows after applying constraints.'),
                )
                status_label.config(text=app.tr('tcdata_ready', 'Ready'), foreground='blue')
                return

            sys_name = _sys_name(bal_el, sweep, uppercase_el_var.get())
            tu = temp_unit_var.get()
            fmt = fmt_var.get()
            one_per = one_file_per_t_var.get() and any(t is not None for t in temps)
            written = []
            total_rows = 0

            def _save_df(df, stem):
                paths = []
                if fmt in ('xlsx', 'both'):
                    p = os.path.join(out_dir, f'{stem}.xlsx')
                    df.to_excel(p, index=False, engine='openpyxl')
                    paths.append(p)
                if fmt in ('csv', 'both'):
                    p = os.path.join(out_dir, f'{stem}.csv')
                    df.to_csv(p, index=False)
                    paths.append(p)
                return paths

            real_temps = [t for t in temps if t is not None]
            if one_per and real_temps:
                for t_val in real_temps:
                    df = rows_for_temp(t_val)
                    stem = _build_stem(name_pat_var.get(), sys_name, t_val, tu, True)
                    written.extend(_save_df(df, stem))
                    total_rows += len(df)
            else:
                frames = [rows_for_temp(t) for t in temps]
                df = pd.concat(frames, ignore_index=True)
                df['ID'] = np.arange(1, len(df) + 1)
                stem = _build_stem(name_pat_var.get(), sys_name, None, tu, False)
                if not stem or stem.endswith('-'):
                    stem = sys_name
                # include model id hint for non-diffusion models
                m = _current_model()
                if m['id'] != 'custom_diffusion' and m['id'] not in stem:
                    stem = f"{stem}-{m['id']}"
                written.extend(_save_df(df, stem))
                total_rows = len(df)

            nfile = len(written)
            path_preview = '\n'.join(written[:8])
            if len(written) > 8:
                path_preview += f'\n… (+{len(written) - 8})'
            done_msg = app.tr(
                'tcdata_done',
                'Done: {nfile} file(s), {nrows} row(s) total.\n{paths}',
            ).format(nfile=nfile, nrows=total_rows, paths=path_preview)
            status_label.config(text=done_msg.split('\n')[0], foreground='green')
            messagebox.showinfo(app.tr('tcdata_heading', 'Data File Generator'), done_msg)
        except Exception as e:
            import traceback

            status_label.config(text=str(e), foreground='red')
            messagebox.showerror(
                app.tr('dlg_error', 'Error'),
                f'{e}\n\n{traceback.format_exc()}',
            )

    action_fr = ttk.Frame(main_frame)
    action_fr.pack(pady=6)
    btn_preview = ttk.Button(
        action_fr, text=app.tr('tcdata_preview_btn', 'Count Rows'), command=preview_count
    )
    btn_preview.pack(side=tk.LEFT, padx=6)
    btn_gen = ttk.Button(
        action_fr, text=app.tr('tcdata_generate', 'Generate Data File(s)'), command=generate
    )
    btn_gen.pack(side=tk.LEFT, padx=6)
    btn_close = ttk.Button(action_fr, text=app.tr('ui_close', 'Close'), command=win.destroy)
    btn_close.pack(side=tk.LEFT, padx=6)

    def _refresh_tcdata_lang():
        try:
            if not win.winfo_exists():
                return
        except tk.TclError:
            return
        win.title(app.tr('tcdata_win_title', 'Thermo-Calc Batch Data File Generator'))
        title_label.config(text=app.tr('tcdata_heading', 'Thermo-Calc Batch Data File Generator'))
        info_label.config(text=app.tr('tcdata_intro_models', app.tr('tcdata_intro', '')))
        model_frame.config(text=app.tr('tcdata_model_frame', 'General Model'))
        _refill_model_list(state['model_id'])
        elements_frame.config(text=app.tr('tcdata_elem_cfg', 'Element Configuration'))
        for col, key in (
            ('Element', 'tcdata_tbl_element'),
            ('Role', 'tcdata_tbl_role'),
            ('Min', 'tcdata_tbl_min'),
            ('Max', 'tcdata_tbl_max'),
            ('Step', 'tcdata_tbl_step'),
        ):
            elements_tree.heading(col, text=app.tr(key, col))
        for item in elements_tree.get_children():
            vals = list(elements_tree.item(item)['values'])
            role = str(vals[1])
            is_bal = role.lower().startswith('bal') or '平衡' in role or 'Balance' in role
            bal_lbl, sweep_lbl = _role_labels()
            vals[1] = bal_lbl if is_bal else sweep_lbl
            elements_tree.item(item, values=vals)
        lbl_el.config(text=app.tr('tcdata_lbl_element', 'Element:'))
        lbl_min.config(text=app.tr('tcdata_lbl_min', 'Min:'))
        lbl_max.config(text=app.tr('tcdata_lbl_max', 'Max:'))
        lbl_step.config(text=app.tr('tcdata_lbl_step', 'Step:'))
        cb_as_bal.config(text=app.tr('tcdata_as_balance', 'Add as Balance (Bal)'))
        btn_add.config(text=app.tr('tcdata_add', 'Add Element'))
        btn_remove.config(text=app.tr('tcdata_remove', 'Remove Selected'))
        btn_set_bal.config(text=app.tr('tcdata_set_bal', 'Set Selected as Balance'))
        units_frame.config(text=app.tr('tcdata_units', 'Units'))
        lbl_cu.config(text=app.tr('tcdata_comp_unit', 'Composition unit:'))
        lbl_tu.config(text=app.tr('tcdata_temp_unit', 'Temperature unit:'))
        temp_frame.config(text=app.tr('tcdata_temp_cfg', 'Temperature'))
        lbl_tmode.config(text=app.tr('tcdata_temp_mode', 'Mode:'))
        rb_single.config(text=app.tr('tcdata_temp_single', 'Single value'))
        rb_range.config(text=app.tr('tcdata_temp_range', 'Range'))
        rb_list.config(text=app.tr('tcdata_temp_list', 'List'))
        rb_none.config(text=app.tr('tcdata_temp_none', 'None (composition only)'))
        lbl_tv.config(text=app.tr('tcdata_temp_value', 'T:'))
        lbl_tmin.config(text=app.tr('tcdata_temp_min', 'T min:'))
        lbl_tmax.config(text=app.tr('tcdata_temp_max', 'T max:'))
        lbl_tstep.config(text=app.tr('tcdata_temp_step', 'T step:'))
        lbl_tlist.config(text=app.tr('tcdata_temp_list_lbl', 'T list:'))
        cb_one_t.config(text=app.tr('tcdata_one_file_per_t', 'One file per temperature'))
        cb_upper.config(text=app.tr('tcdata_uppercase_el', 'Uppercase element symbols'))
        params_frame.config(text=app.tr('tcdata_params', 'Param / Exp Columns'))
        param_hint.config(text=app.tr('tcdata_param_hint', ''))
        params_tree.heading('Header', text=app.tr('tcdata_tbl_header', 'Header'))
        params_tree.heading('Value', text=app.tr('tcdata_tbl_value', 'Value'))
        lbl_pk.config(text=app.tr('tcdata_param_kind', 'Kind:'))
        lbl_pn.config(text=app.tr('tcdata_param_name', 'Name:'))
        lbl_pv.config(text=app.tr('tcdata_param_value', 'Value:'))
        btn_padd.config(text=app.tr('tcdata_param_add', 'Add Column'))
        btn_prem.config(text=app.tr('tcdata_param_remove', 'Remove Selected'))
        cons_frame.config(text=app.tr('tcdata_constraints', 'Constraints'))
        cb_sum.config(text=app.tr('tcdata_sum_limit', 'Drop over-limit rows'))
        cb_zero.config(text=app.tr('tcdata_exclude_zeros', 'Exclude all-zero'))
        out_frame.config(text=app.tr('tcdata_output', 'Output'))
        lbl_od.config(text=app.tr('tcdata_out_dir', 'Output folder:'))
        btn_obrowse.config(text=app.tr('pandat_browse', 'Browse'))
        lbl_fmt.config(text=app.tr('tcdata_out_fmt', 'Format:'))
        lbl_pat.config(text=app.tr('tcdata_name_pattern', 'Name pattern:'))
        name_hint.config(text=app.tr('tcdata_name_hint', '{sys} / {T} / {Tu}'))
        btn_preview.config(text=app.tr('tcdata_preview_btn', 'Count Rows'))
        btn_gen.config(text=app.tr('tcdata_generate', 'Generate Data File(s)'))
        btn_close.config(text=app.tr('ui_close', 'Close'))
        status_label.config(text=app.tr('tcdata_ready', 'Ready to generate'), foreground='blue')

    win.title(app.tr('tcdata_win_title', 'Thermo-Calc Batch Data File Generator'))
    app._register_tool_lang_refresh(_refresh_tcdata_lang)

    def _on_close():
        app._unregister_tool_lang_refresh(_refresh_tcdata_lang)
        try:
            if _scroll_unbind:
                _scroll_unbind()
        except Exception:
            pass
        win.destroy()

    win.protocol('WM_DELETE_WINDOW', _on_close)
    btn_close.config(command=_on_close)
    _refill_model_list()
    _refresh_tcdata_lang()
