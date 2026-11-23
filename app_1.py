"""Streamlit app: plot an arbitrary function x(t) -- single file, no extra packages.

Uses only streamlit, numpy and pandas (all of which come with Streamlit),
so no requirements.txt is needed.

Run with:
    streamlit run plot_xt_streamlit.py
"""

import ast

import numpy as np
import pandas as pd
import streamlit as st

# Names the user is allowed to use inside the expression
ALLOWED = {
    "t": None,  # the variable, filled in at evaluation time
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
    "where": np.where,                      # where(t < 0, 0, t)
    "Heaviside": lambda x: np.heaviside(x, 0.5),
    "heaviside": lambda x: np.heaviside(x, 0.5),
}

ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Compare, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.BitAnd, ast.BitOr, ast.Invert,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
)


def compile_function(text):
    """Validate the text and return a function x_of_t(tt) that works on numpy arrays."""
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
            if node.func.id == "t" or not callable(ALLOWED[node.func.id]):
                raise ValueError(f"'{node.func.id}' is not a function")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("only numbers are allowed as constants")

    code = compile(tree, "<x(t)>", "eval")

    def x_of_t(tt):
        env = dict(ALLOWED, t=tt)
        y = np.asarray(eval(code, {"__builtins__": {}}, env), dtype=float)
        return np.broadcast_to(y, np.shape(tt)).copy()  # handles constants like "5"

    return x_of_t


st.set_page_config(page_title="x(t) plotter", page_icon="📈")
st.title("Plot x(t)")

text = st.text_input(
    "x(t) =",
    value="sin(2*pi*t) * exp(-t/3)",
    help="Use t as the variable. Powers: ** or ^. Use * for multiplication (write 2*t, not 2t).",
)
st.caption(
    "Available: sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, exp, log, ln, log10, "
    "sqrt, abs, sign, floor, ceil, min, max, Heaviside, where(cond, a, b), pi, e. "
    "Example: where(t < 1, t, 1)"
)

col1, col2, col3 = st.columns(3)
t_min = col1.number_input("t start", value=0.0)
t_max = col2.number_input("t end", value=10.0)
n = col3.number_input("Points", min_value=10, max_value=100000, value=2000, step=100)

if t_max <= t_min:
    st.error("t end must be greater than t start.")
    st.stop()

try:
    x_of_t = compile_function(text)
    tt = np.linspace(t_min, t_max, int(n))
    with np.errstate(all="ignore"):
        xx = x_of_t(tt)
    xx[~np.isfinite(xx)] = np.nan  # gaps at singularities
except Exception as err:
    st.error(f"Couldn't use that expression: {err}")
    st.stop()

df = pd.DataFrame({"t": tt, "x(t)": xx})
st.line_chart(df, x="t", y="x(t)")
