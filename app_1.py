"""Streamlit app: plot an arbitrary function x(t).

Requires: streamlit, numpy, matplotlib, sympy
    pip install streamlit numpy matplotlib sympy

Run with:
    streamlit run app.py
"""

import numpy as np
import matplotlib.pyplot as plt
import sympy as sp
import streamlit as st
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

t = sp.Symbol("t", real=True)
TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)


def parse_function(text):
    """Turn a string like 'sin(2*pi*t)' into a numpy function of t."""
    expr = parse_expr(text, local_dict={"t": t}, transformations=TRANSFORMS)
    f = sp.lambdify(t, expr, modules=["numpy", {"Heaviside": lambda x: np.heaviside(x, 0.5)}])

    def x_of_t(tt):
        y = np.asarray(f(tt), dtype=float)
        return np.broadcast_to(y, np.shape(tt)).copy()  # handles constants like "5"

    return expr, x_of_t


st.set_page_config(page_title="x(t) plotter", page_icon="📈")
st.title("Plot x(t)")

text = st.text_input(
    "x(t) =",
    value="sin(2*pi*t) * exp(-t/3)",
    help="Use t as the variable. Powers: ** or ^. "
    "Available: sin, cos, tan, exp, log, sqrt, abs, pi, E, Heaviside, Piecewise",
)

col1, col2, col3 = st.columns(3)
t_min = col1.number_input("t start", value=0.0)
t_max = col2.number_input("t end", value=10.0)
n = col3.number_input("Points", min_value=10, max_value=100000, value=2000, step=100)

if t_max <= t_min:
    st.error("t end must be greater than t start.")
    st.stop()

try:
    expr, x_of_t = parse_function(text)
    tt = np.linspace(t_min, t_max, int(n))
    with np.errstate(all="ignore"):
        xx = x_of_t(tt)
    xx[~np.isfinite(xx)] = np.nan  # gaps at singularities
except Exception as err:
    st.error(f"Couldn't read that expression: {err}")
    st.stop()

st.latex(f"x(t) = {sp.latex(expr)}")

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(tt, xx, linewidth=2)
ax.axhline(0, color="gray", linewidth=0.8)
ax.axvline(0, color="gray", linewidth=0.8)
ax.set_xlabel("t")
ax.set_ylabel("x(t)")
ax.grid(True, alpha=0.3)
fig.tight_layout()
st.pyplot(fig)
