"""Streamlit app: plot an arbitrary function f(x) on a graph-paper style sheet.

Single file. Uses only streamlit, numpy, pandas and altair, all of which are
installed together with Streamlit, so no requirements.txt is needed.

Run with:
    streamlit run plot_fx_streamlit.py
"""

import ast
import math

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------- expression parsing

# Names the user is allowed to use inside the expression
ALLOWED = {
    "x": None,  # the variable, filled in at evaluation time
    "pi": np.pi,
    "e": np.e,
    "E": np.e,
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "exp": np.exp, "log": np.log, "ln": np.log, "log10": np.log10,
    "sqrt": np.sqrt, "abs": np.abs, "sign": np.sign,
    "floor": np.floor, "ceil": np.ceil,
    "min": np.minimum, "max": np.maximum,
    "where": np.where,                      # where(x < 0, 0, x)
    "Heaviside": lambda v: np.heaviside(v, 0.5),
    "heaviside": lambda v: np.heaviside(v, 0.5),
}

ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Compare, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.BitAnd, ast.BitOr, ast.Invert,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
)


def compile_function(text):
    """Validate the text and return a function f(xx) that works on numpy arrays."""
    text = text.strip().replace("^", "**")
    if not text:
        raise ValueError("empty expression")

    tree = ast.parse(text, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"'{type(node).__name__}' is not allowed")
        if isinstance(node, ast.Name) and node.id not in ALLOWED:
            raise ValueError(f"unknown name '{node.id}'")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.keywords:
                raise ValueError("only simple function calls are allowed")
            if node.func.id == "x" or not callable(ALLOWED[node.func.id]):
                raise ValueError(f"'{node.func.id}' is not a function")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("only numbers are allowed as constants")

    code = compile(tree, "<f(x)>", "eval")

    def f(xx):
        env = dict(ALLOWED, x=xx)
        y = np.asarray(eval(code, {"__builtins__": {}}, env), dtype=float)
        return np.broadcast_to(y, np.shape(xx)).copy()  # handles constants like "5"

    return f


# ---------------------------------------------------------------- graph-paper helpers

def nice_step(span, target=10):
    """A 1/2/5 x 10^k step that gives roughly `target` divisions across `span`."""
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def grid_values(lo, hi, step):
    first = math.ceil(lo / step - 1e-9)
    last = math.floor(hi / step + 1e-9)
    return np.round(np.arange(first, last + 1) * step, 10)


def graph_sheet(df, xlo, xhi, ylo, yhi, width=None, height=560, equal=False):
    """Build the Altair chart: minor grid, major grid, axes through the origin, curve."""
    xstep = nice_step(xhi - xlo)
    ystep = xstep if equal else nice_step(yhi - ylo)  # equal scale -> square grid cells
    xmajor, ymajor = grid_values(xlo, xhi, xstep), grid_values(ylo, yhi, ystep)
    xminor, yminor = grid_values(xlo, xhi, xstep / 5), grid_values(ylo, yhi, ystep / 5)

    xscale = alt.Scale(domain=[xlo, xhi], nice=False, zero=False)
    yscale = alt.Scale(domain=[ylo, yhi], nice=False, zero=False)

    def vlines(values, color, width):
        return alt.Chart(pd.DataFrame({"v": values})).mark_rule(
            color=color, strokeWidth=width
        ).encode(x=alt.X("v:Q", scale=xscale, axis=None))

    def hlines(values, color, width):
        return alt.Chart(pd.DataFrame({"v": values})).mark_rule(
            color=color, strokeWidth=width
        ).encode(y=alt.Y("v:Q", scale=yscale, axis=None))

    minor_c, major_c, axis_c = "#cfe8d5", "#84c295", "#1b1b1b"
    layers = [
        vlines(xminor, minor_c, 0.6), hlines(yminor, minor_c, 0.6),
        vlines(xmajor, major_c, 1.1), hlines(ymajor, major_c, 1.1),
    ]
    if xlo <= 0 <= xhi:
        layers.append(vlines([0], axis_c, 2))
    if ylo <= 0 <= yhi:
        layers.append(hlines([0], axis_c, 2))

    label_style = dict(labelColor="#222", titleColor="#222", labelFontSize=11,
                       titleFontSize=13, domain=False, grid=False, format="~g")
    curve = alt.Chart(df).mark_line(color="#d62728", strokeWidth=2.6, clip=True).encode(
        x=alt.X("x:Q", scale=xscale,
                axis=alt.Axis(values=xmajor.tolist(), title="x", **label_style)),
        y=alt.Y("y:Q", scale=yscale,
                axis=alt.Axis(values=ymajor.tolist(), title="f(x)", **label_style)),
    )
    layers.append(curve)

    # ---- cursor: follows the mouse, snaps to the curve and projects onto both axes
    cdf = df.dropna()
    nearest = alt.selection_point(
        name="cursor", fields=["x"], nearest=True,
        on="pointerover", clear="pointerout", empty=False,
    )
    selector = (
        alt.Chart(cdf).mark_point()
        .encode(x=alt.X("x:Q", scale=xscale, axis=None), opacity=alt.value(0))
        .add_params(nearest)
    )

    x_axis_y = 0.0 if ylo <= 0 <= yhi else ylo   # where the x-axis sits (y value)
    y_axis_x = 0.0 if xlo <= 0 <= xhi else xlo   # where the y-axis sits (x value)
    show = alt.condition(nearest, alt.value(1), alt.value(0))
    cur_c = "#1f4fd8"
    base = alt.Chart(cdf)
    xe = alt.X("x:Q", scale=xscale, axis=None)
    ye = alt.Y("y:Q", scale=yscale, axis=None)

    vdrop = base.mark_rule(strokeDash=[5, 4], color=cur_c, strokeWidth=1.4, clip=True).encode(
        x=xe, y=ye, y2=alt.Y2(datum=x_axis_y), opacity=show)
    hdrop = base.mark_rule(strokeDash=[5, 4], color=cur_c, strokeWidth=1.4, clip=True).encode(
        x=xe, x2=alt.X2(datum=y_axis_x), y=ye, opacity=show)
    dot = base.mark_point(
        filled=True, size=100, color="#d62728", stroke="white", strokeWidth=1.5, clip=True
    ).encode(
        x=xe, y=ye, opacity=show,
        tooltip=[alt.Tooltip("x:Q", format=".4g"), alt.Tooltip("y:Q", title="f(x)", format=".4g")],
    )
    xlabel = base.mark_text(
        color=cur_c, fontWeight="bold", fontSize=13, clip=True,
        dy=-12 if x_axis_y == ylo else 14,
    ).encode(x=xe, y=alt.Y(datum=x_axis_y), text=alt.Text("x:Q", format=".4g"), opacity=show)
    ylabel = base.mark_text(
        color=cur_c, fontWeight="bold", fontSize=13, clip=True,
        align="left" if y_axis_x == xlo else "right",
        dx=8 if y_axis_x == xlo else -8,
    ).encode(x=alt.X(datum=y_axis_x), y=ye, text=alt.Text("y:Q", format=".4g"), opacity=show)

    layers.extend([vdrop, hdrop, dot, xlabel, ylabel, selector])

    return (
        alt.layer(*layers)
        .properties(height=height, **({"width": width} if width else {}))
        .configure_view(fill="#fbfff9", stroke="#555", strokeWidth=1.5)
    )


# ---------------------------------------------------------------- the app

st.set_page_config(page_title="f(x) plotter", page_icon="📈", layout="wide")
st.title("Plot f(x)")

text = st.text_input(
    "f(x) =",
    value="sin(x) * exp(-x/8)",
    help="Use x as the variable. Powers: ** or ^. Use * for multiplication (write 2*x, not 2x).",
)
st.caption(
    "Available: sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, exp, log, ln, log10, "
    "sqrt, abs, sign, floor, ceil, min, max, Heaviside, where(cond, a, b), pi, e. "
    "Example: where(x < 1, x, 1)"
)

c1, c2, c3 = st.columns(3)
x_min = c1.number_input("x min", value=-10.0)
x_max = c2.number_input("x max", value=10.0)
n = c3.number_input("Points", min_value=10, max_value=100000, value=3000, step=100)

PLOT_W, PLOT_H = 800, 560  # plot-area size in pixels (used for the equal-scale ratio)

equal_scale = st.checkbox("Same scale on x and y axes", value=True)
auto_y = st.checkbox("Automatic y position", value=True)
c4, c5 = st.columns(2)
y_min_in = c4.number_input("y min (bottom edge)", value=-7.0, disabled=auto_y)
y_max_in = c5.number_input("y max", value=7.0, disabled=auto_y or equal_scale)
if equal_scale:
    st.caption("With equal scale, the y span is set by the x range and the plot shape, "
               "so y max is calculated automatically.")

if x_max <= x_min:
    st.error("x max must be greater than x min.")
    st.stop()
if not auto_y and not equal_scale and y_max_in <= y_min_in:
    st.error("y max must be greater than y min.")
    st.stop()

try:
    f = compile_function(text)
    xx = np.linspace(x_min, x_max, int(n))
    with np.errstate(all="ignore"):
        yy = f(xx)
    yy[~np.isfinite(yy)] = np.nan  # gaps at singularities
except Exception as err:
    st.error(f"Couldn't use that expression: {err}")
    st.stop()

if auto_y:
    finite = yy[np.isfinite(yy)]
    if finite.size == 0:
        st.error("The function has no finite values on this x range.")
        st.stop()
    lo, hi = np.percentile(finite, [1, 99])
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    pad = 0.12 * (hi - lo)
    y_lo, y_hi = float(lo - pad), float(hi + pad)
else:
    y_lo, y_hi = float(y_min_in), float(y_max_in)

if equal_scale:
    # 1 unit on x must have the same pixel length as 1 unit on y
    y_span = (x_max - x_min) * PLOT_H / PLOT_W
    if auto_y:
        centre = (y_lo + y_hi) / 2
        y_lo, y_hi = centre - y_span / 2, centre + y_span / 2
    else:
        y_lo, y_hi = float(y_min_in), float(y_min_in) + y_span

# Break the line at huge jumps (e.g. tan(x) asymptotes) so no vertical streaks appear
jump = np.abs(np.diff(yy)) > 2 * (y_hi - y_lo)
yy[1:][jump] = np.nan

df = pd.DataFrame({"x": xx, "y": yy})
chart = graph_sheet(
    df, x_min, x_max, y_lo, y_hi,
    width=PLOT_W if equal_scale else None, height=PLOT_H, equal=equal_scale,
)
st.altair_chart(chart, use_container_width=not equal_scale, theme=None)
