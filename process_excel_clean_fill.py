import sys
from pathlib import Path
import pandas as pd
import numpy as np


def clean_and_forward_fill_excel(input_path: Path, output_path: Path) -> None:
    # 读取并基础清洗
    df = pd.read_excel(input_path, header=0)
    df = df.replace(r"^\s*$", np.nan, regex=True)
    df = df.dropna(axis=0, how="all")
    df = df.infer_objects(copy=False)

    # 列名去掉首尾空格
    df = df.rename(columns={c: c.strip() for c in df.columns})

    # 找到需要用到的 4 列
    import re

    def _find_required_columns(df_: pd.DataFrame) -> tuple[str, str, str, str]:
        norm = {c: re.sub(r"\s+", "", c, flags=re.UNICODE).lower() for c in df_.columns}
        rev = {v: k for k, v in norm.items()}

        def find_by_exact(key: str) -> str | None:
            return rev.get(key)

        def find_by_regex(patterns: list[str]) -> str | None:
            for c in df_.columns:
                s = c.lower()
                if all(re.search(p, s, flags=re.IGNORECASE) for p in patterns):
                    return c
            return None

        wmg = find_by_exact("w(mg)") or find_by_regex([r"^w\(mg\)"])
        wsi = find_by_exact("w(si)") or find_by_regex([r"^w\(si\)"])

        inv_mg = find_by_exact("1/dwdt_l(mg@liquid)") or find_by_regex(
            [r"1/dwdt_l\(", r"mg@liquid\)"]
        )
        inv_si = find_by_exact("1/dwdt_l(si@liquid)") or find_by_regex(
            [r"1/dwdt_l\(", r"si@liquid\)"]
        )

        if not (wmg and wsi and inv_mg and inv_si):
            msg = (
                "缺少必要列，需要：'w(MG)', 'w(SI)', "
                "'1/dwdT_L(MG@LIQUID)', '1/dwdT_L(SI@LIQUID)'，当前列为："
                f"{list(df_.columns)}"
            )
            raise ValueError(msg)

        return wmg, wsi, inv_mg, inv_si

    col_wmg, col_wsi, col_inv_mg, col_inv_si = _find_required_columns(df)

    # 转为数值型方便判断
    wmg = pd.to_numeric(df[col_wmg], errors="coerce")
    wsi = pd.to_numeric(df[col_wsi], errors="coerce")
    inv_mg_base = pd.to_numeric(df[col_inv_mg], errors="coerce")
    inv_si_base = pd.to_numeric(df[col_inv_si], errors="coerce")

    def quad_interp(x_known: np.ndarray, y_known: np.ndarray, x_target: float) -> float:
        """
        用二次多项式（Newton 前向差分等价形式）插值 / 外推。
        这里使用 polyfit 拟合 2 次多项式，数学上与 Newton 二次插值等价。
        """
        coeffs = np.polyfit(x_known, y_known, 2)
        return float(np.polyval(coeffs, x_target))

    # --------------------
    # 通用的第一、二步（两种方案共用）：
    #   第一步：w(MG)=0, w(SI)≠0 时，补 1/dwdT_L(MG@LIQUID)
    #   第二步：w(SI)=0, w(MG)≠0 时，补 1/dwdT_L(SI@LIQUID)
    # --------------------
    mg_targets = np.array([1.0, 2.0, 3.0], dtype=float)
    si_targets = np.array([1.0, 2.0, 3.0], dtype=float)

    # 在 base 的副本上做第一、二步
    inv_mg_common = inv_mg_base.copy()
    inv_si_common = inv_si_base.copy()

    # 第一步：w(MG)=0, w(SI)≠0 → 补 1/dwdT_L(MG@LIQUID)
    mask_step1 = inv_mg_common.isna() & np.isclose(wmg, 0.0, atol=1e-12) & ~np.isclose(
        wsi, 0.0, atol=1e-12
    )
    for idx in df[mask_step1].index:
        si_val = wsi.loc[idx]
        y_vals = []
        x_vals = []
        for m in mg_targets:
            m_mask = (
                np.isclose(wmg, m, atol=1e-12)
                & np.isclose(wsi, si_val, atol=1e-12)
                & ~inv_mg_common.isna()
            )
            if m_mask.any():
                x_vals.append(m)
                y_vals.append(inv_mg_common[m_mask].iloc[0])

        if len(y_vals) == 3:
            inv_mg_common.at[idx] = quad_interp(np.array(x_vals), np.array(y_vals), 0.0)

    # 第二步：w(SI)=0, w(MG)≠0 → 补 1/dwdT_L(SI@LIQUID)
    mask_step2 = inv_si_common.isna() & np.isclose(wsi, 0.0, atol=1e-12) & ~np.isclose(
        wmg, 0.0, atol=1e-12
    )
    for idx in df[mask_step2].index:
        mg_val = wmg.loc[idx]
        y_vals = []
        x_vals = []
        for s in si_targets:
            s_mask = (
                np.isclose(wsi, s, atol=1e-12)
                & np.isclose(wmg, mg_val, atol=1e-12)
                & ~inv_si_common.isna()
            )
            if s_mask.any():
                x_vals.append(s)
                y_vals.append(inv_si_common[s_mask].iloc[0])

        if len(y_vals) == 3:
            inv_si_common.at[idx] = quad_interp(np.array(x_vals), np.array(y_vals), 0.0)

    # 为两种方案各拷贝一份（区别只在第三步）
    inv_mg_scheme1 = inv_mg_common.copy()
    inv_si_scheme1 = inv_si_common.copy()
    inv_mg_scheme2 = inv_mg_common.copy()
    inv_si_scheme2 = inv_si_common.copy()

    # --------------------
    # 方案一（“之前的方案”）第三步：
    #   (w(MG)=0, w(SI)=0) 时：
    #     - 1/dwdT_L(MG@LIQUID)：在 w(SI)=0 下，沿 w(MG)=1,2,3 二次插值
    #     - 1/dwdT_L(SI@LIQUID)：在 w(MG)=0 下，沿 w(SI)=1,2,3 二次插值
    # --------------------
    mask_00_scheme1 = (
        inv_mg_scheme1.isna()
        & inv_si_scheme1.isna()
        & np.isclose(wmg, 0.0, atol=1e-12)
        & np.isclose(wsi, 0.0, atol=1e-12)
    )
    for idx in df[mask_00_scheme1].index:
        # MG@LIQUID：固定 w(SI)=0，沿 w(MG)=1,2,3
        y_vals_mg = []
        x_vals_mg = []
        for m in mg_targets:
            m_mask = (
                np.isclose(wsi, 0.0, atol=1e-12)
                & np.isclose(wmg, m, atol=1e-12)
                & ~inv_mg_scheme1.isna()
            )
            if m_mask.any():
                x_vals_mg.append(m)
                y_vals_mg.append(inv_mg_scheme1[m_mask].iloc[0])
        if len(y_vals_mg) == 3:
            inv_mg_scheme1.at[idx] = quad_interp(
                np.array(x_vals_mg), np.array(y_vals_mg), 0.0
            )

        # SI@LIQUID：固定 w(MG)=0，沿 w(SI)=1,2,3
        y_vals_si = []
        x_vals_si = []
        for s in si_targets:
            s_mask = (
                np.isclose(wmg, 0.0, atol=1e-12)
                & np.isclose(wsi, s, atol=1e-12)
                & ~inv_si_scheme1.isna()
            )
            if s_mask.any():
                x_vals_si.append(s)
                y_vals_si.append(inv_si_scheme1[s_mask].iloc[0])
        if len(y_vals_si) == 3:
            inv_si_scheme1.at[idx] = quad_interp(
                np.array(x_vals_si), np.array(y_vals_si), 0.0
            )

    # --------------------
    # 方案二（你新给出的第二个方案）第三步：
    #   (w(MG)=0, w(SI)=0) 时：
    #     - 1/dwdT_L(MG@LIQUID)：在 w(MG)=0 下，沿 w(SI)=1,2,3 二次插值
    #     - 1/dwdT_L(SI@LIQUID)：在 w(SI)=0 下，沿 w(MG)=1,2,3 二次插值
    # --------------------
    mask_00_scheme2 = (
        inv_mg_scheme2.isna()
        & inv_si_scheme2.isna()
        & np.isclose(wmg, 0.0, atol=1e-12)
        & np.isclose(wsi, 0.0, atol=1e-12)
    )
    for idx in df[mask_00_scheme2].index:
        # MG@LIQUID：固定 w(MG)=0，沿 w(SI)=1,2,3
        y_vals_mg = []
        x_vals_mg = []
        for s in si_targets:
            s_mask = (
                np.isclose(wmg, 0.0, atol=1e-12)
                & np.isclose(wsi, s, atol=1e-12)
                & ~inv_mg_scheme2.isna()
            )
            if s_mask.any():
                x_vals_mg.append(s)
                y_vals_mg.append(inv_mg_scheme2[s_mask].iloc[0])
        if len(y_vals_mg) == 3:
            inv_mg_scheme2.at[idx] = quad_interp(
                np.array(x_vals_mg), np.array(y_vals_mg), 0.0
            )

        # SI@LIQUID：固定 w(SI)=0，沿 w(MG)=1,2,3
        y_vals_si = []
        x_vals_si = []
        for m in mg_targets:
            m_mask = (
                np.isclose(wsi, 0.0, atol=1e-12)
                & np.isclose(wmg, m, atol=1e-12)
                & ~inv_si_scheme2.isna()
            )
            if m_mask.any():
                x_vals_si.append(m)
                y_vals_si.append(inv_si_scheme2[m_mask].iloc[0])
        if len(y_vals_si) == 3:
            inv_si_scheme2.at[idx] = quad_interp(
                np.array(x_vals_si), np.array(y_vals_si), 0.0
            )

    # 针对两个方案分别生成 DataFrame，并各自做一次“其余数值列”的线性插值
    def _finalize_df(df_src: pd.DataFrame, inv_mg_col: pd.Series, inv_si_col: pd.Series) -> pd.DataFrame:
        out_df = df_src.copy()
        out_df[col_inv_mg] = inv_mg_col
        out_df[col_inv_si] = inv_si_col

        if len(out_df) >= 1:
            first_data_row = out_df.iloc[:1].copy()
            remaining_rows = out_df.iloc[1:].copy()
            remaining_rows = remaining_rows.infer_objects(copy=False)
            remaining_rows = remaining_rows.interpolate(
                method="linear",
                axis=0,
                limit_direction="both",
                numeric_only=True,
            )
            out_df = pd.concat([first_data_row, remaining_rows], ignore_index=True)
        return out_df

    df_scheme1 = _finalize_df(df, inv_mg_scheme1, inv_si_scheme1)
    df_scheme2 = _finalize_df(df, inv_mg_scheme2, inv_si_scheme2)

    # 输出两个 Excel：
    #   - 方案一：保持原来的输出文件名（output_path）
    #   - 方案二：在文件名后加上 "_scheme2"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_scheme1.to_excel(output_path, index=False)

    output_path_scheme2 = output_path.with_name(
        f"{output_path.stem}_scheme2{output_path.suffix}"
    )
    df_scheme2.to_excel(output_path_scheme2, index=False)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python process_excel_clean_fill.py <excel_path>")
        sys.exit(1)

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(2)

    output_path = input_path.with_name(f"{input_path.stem}_cleaned_linear{input_path.suffix}")

    clean_and_forward_fill_excel(input_path, output_path)

    print(f"Cleaned file saved to: {output_path}")


if __name__ == "__main__":
    main()


