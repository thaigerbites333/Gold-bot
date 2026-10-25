"""กราฟแท่งเทียน + แนวรับแนวต้าน (PNG base64 สำหรับฝังใน PDF)"""
import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402

from . import config  # noqa: E402

UP, DN = "#15803d", "#b91c1c"
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
EMA20, EMA50 = "#2563eb", "#d97706"


def candle_chart(df, title, a, bars=96, levels=True, plan=True, width=7.6, height=3.0):
    d = df.tail(bars)
    x = d.index.tz_convert(config.TZ_LOCAL).tz_localize(None)
    w = (x[1] - x[0]) * 0.62 if len(x) > 1 else 0.01

    fig, ax = plt.subplots(figsize=(width, height), dpi=170)
    up = d["close"] >= d["open"]
    for mask, col in [(up, UP), (~up, DN)]:
        ax.vlines(x[mask], d["low"][mask], d["high"][mask], color=col, linewidth=0.8)
        ax.bar(x[mask], (d["close"] - d["open"])[mask].abs().clip(lower=0.05),
               bottom=d[["open", "close"]].min(axis=1)[mask], width=w, color=col, linewidth=0)
    ax.plot(x, d["ema20"], color=EMA20, linewidth=1.4, label="EMA20")
    ax.plot(x, d["ema50"], color=EMA50, linewidth=1.4, label="EMA50")
    if d["ema200"].notna().all():
        ax.plot(x, d["ema200"], color="#7c3aed", linewidth=1.2, linestyle=(0, (4, 2)), label="EMA200")

    lo, hi = d["low"].min(), d["high"].max()
    pad = (hi - lo) * 0.06
    if levels:
        for lv in a["resistance"][:2]:
            if lo - pad < lv < hi + pad * 4:
                ax.axhline(lv, color=DN, linewidth=0.9, linestyle="--", alpha=0.8)
                ax.text(x[-1], lv, f"  R {lv:.2f}", color=DN, fontsize=7, va="center", ha="left")
        for lv in a["support"][:2]:
            if lo - pad * 4 < lv < hi + pad:
                ax.axhline(lv, color=UP, linewidth=0.9, linestyle="--", alpha=0.8)
                ax.text(x[-1], lv, f"  S {lv:.2f}", color=UP, fontsize=7, va="center", ha="left")
        p = a["plan"]
        if plan and p["side"] != "WAIT":
            for key, col, name in [("sl", "#991b1b", "SL"), ("tp2", "#166534", "TP")]:
                ax.axhline(p[key], color=col, linewidth=0.8, linestyle=":")
                ax.text(x[0], p[key], f"{name} {p[key]:.2f} ", color=col, fontsize=7, va="bottom", ha="left")

    last = d["close"].iloc[-1]
    ax.axhline(last, color=INK, linewidth=0.6, alpha=0.5)
    ax.text(x[-1], last, f"  {last:.2f}", fontsize=8, fontweight="bold", color="white", va="center", ha="left",
            bbox=dict(boxstyle="round,pad=0.25", fc=INK, ec="none"))

    ax.set_title(title, loc="left", fontsize=10, color=INK, fontweight="bold")
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=7, length=0)
    ax.yaxis.tick_right()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
    ax.legend(loc="upper left", fontsize=7, frameon=False, ncol=3)
    ax.margins(x=0.01)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
