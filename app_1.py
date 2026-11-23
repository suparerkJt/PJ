"""Streamlit app: plot f(x) on a zoomable graph-paper sheet.

Single file. Needs only streamlit and numpy (numpy comes with Streamlit),
so no requirements.txt is needed.

Run with:
    streamlit run plot_fx_zoom.py

The graph itself is drawn in the browser (HTML canvas), so it can be redrawn
instantly while you zoom (mouse wheel) and pan (drag). x and y always share the
same scale. There are no min/max boxes: just zoom and pan to explore.
"""

import ast
import json
import math

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

PLOT_H = 600  # height of the graph sheet in pixels (width follows the page)

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


def parse_expression(text):
    """Parse and validate the text. Returns a safe AST or raises ValueError."""
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
    return tree


# ---------------------------------------------------------------- AST -> JavaScript
# The validated AST is translated to JavaScript so the browser can re-evaluate
# f(x) for every pixel while you zoom and pan.

JS_NAMES = {"x": "x", "pi": "Math.PI", "e": "Math.E", "E": "Math.E"}
JS_FUNCS = {
    "sin": "Math.sin", "cos": "Math.cos", "tan": "Math.tan",
    "asin": "Math.asin", "acos": "Math.acos", "atan": "Math.atan",
    "sinh": "Math.sinh", "cosh": "Math.cosh", "tanh": "Math.tanh",
    "exp": "Math.exp", "log": "Math.log", "ln": "Math.log", "log10": "Math.log10",
    "sqrt": "Math.sqrt", "abs": "Math.abs", "sign": "Math.sign",
    "floor": "Math.floor", "ceil": "Math.ceil",
    "min": "Math.min", "max": "Math.max",
    "Heaviside": "H", "heaviside": "H",
}
JS_CMP = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "===", ast.NotEq: "!=="}
JS_BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}


def to_js(node):
    if isinstance(node, ast.Expression):
        return to_js(node.body)
    if isinstance(node, ast.Constant):
        v = float(node.value)
        if not math.isfinite(v):
            raise ValueError("number too large")
        return repr(v)
    if isinstance(node, ast.Name):
        return JS_NAMES[node.id]
    if isinstance(node, ast.UnaryOp):
        a = to_js(node.operand)
        if isinstance(node.op, ast.USub):
            return f"(-{a})"
        if isinstance(node.op, ast.UAdd):
            return f"(+{a})"
        return f"(({a})?0:1)"  # Invert -> logical not
    if isinstance(node, ast.BinOp):
        left, right, op = to_js(node.left), to_js(node.right), type(node.op)
        if op in JS_BIN:
            return f"({left}{JS_BIN[op]}{right})"
        if op is ast.Pow:
            return f"Math.pow({left},{right})"
        if op is ast.Mod:
            return f"mod({left},{right})"
        if op is ast.FloorDiv:
            return f"Math.floor({left}/{right})"
        if op is ast.BitAnd:
            return f"((({left})&&({right}))?1:0)"
        if op is ast.BitOr:
            return f"((({left})||({right}))?1:0)"
    if isinstance(node, ast.Compare):
        operands = [to_js(node.left)] + [to_js(c) for c in node.comparators]
        parts = [f"({operands[i]}{JS_CMP[type(op)]}{operands[i + 1]})" for i, op in enumerate(node.ops)]
        return "(" + "&&".join(parts) + ")"
    if isinstance(node, ast.Call):
        name = node.func.id
        args = [to_js(a) for a in node.args]
        if name == "where":
            if len(args) != 3:
                raise ValueError("where() needs 3 arguments: where(condition, a, b)")
            return f"(({args[0]})?({args[1]}):({args[2]}))"
        if name in ("min", "max") and len(args) != 2:
            raise ValueError(f"{name}() needs exactly 2 arguments")
        return f"{JS_FUNCS[name]}({','.join(args)})"
    raise ValueError("unsupported expression")


def safe_json(value):
    """JSON string that is safe to drop inside a <script> tag."""
    return json.dumps(value).replace("</", "<\\/")


# ---------------------------------------------------------------- the graph sheet (HTML/JS)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; background: transparent;
               font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  #wrap { position: relative; width: 100%; height: __H__px; box-sizing: border-box;
          border: 1.5px solid #555; border-radius: 6px; overflow: hidden; background: #fbfff9; }
  canvas { display: block; width: 100%; height: 100%; cursor: crosshair; touch-action: none; }
  #reset { position: absolute; right: 10px; top: 10px; font-size: 12px; padding: 4px 10px;
           border: 1px solid #888; border-radius: 6px; background: #fff; color: #222; cursor: pointer; }
  #reset:hover { background: #eef6ef; }
  #hint { position: absolute; left: 10px; bottom: 8px; font-size: 12px; color: #355;
          background: rgba(255,255,255,.8); padding: 2px 9px; border-radius: 10px; pointer-events: none; }
</style></head>
<body>
<div id="wrap">
  <canvas id="c"></canvas>
  <button id="reset">Reset view</button>
  <div id="hint">Scroll to zoom &middot; drag to pan &middot; double-click to reset</div>
</div>
<script>
const EXPR = __EXPR__;
const LABEL = __LABEL__;
const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

let compiled;
try { compiled = new Function("x", "H", "mod", "return " + EXPR); }
catch (e) { compiled = function () { return NaN; }; }
const Hv = v => (v > 0 ? 1 : (v < 0 ? 0 : 0.5));
const modf = (a, b) => a - b * Math.floor(a / b);
function fx(x) {
  try { const y = compiled(x, Hv, modf); return typeof y === "number" ? y : Number(y); }
  catch (e) { return NaN; }
}

const cv = document.getElementById("c");
const ctx = cv.getContext("2d");
let W = 0, Hh = 0, dpr = 1;
let s = 40, ox = 0, oy = 0;      // s = pixels per unit (same for x and y); (ox, oy) = pixel of the origin
let touched = false, mouse = null, drag = null;

function reset() { s = W / 20; ox = W / 2; oy = Hh / 2; }

function resize() {
  dpr = window.devicePixelRatio || 1;
  W = Math.max(200, cv.clientWidth);
  Hh = Math.max(200, cv.clientHeight);
  cv.width = Math.round(W * dpr);
  cv.height = Math.round(Hh * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!touched) reset();
  draw();
}

function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }

function niceStep(raw) {
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [1, 2, 5, 10]) if (raw <= m * mag * 1.0000001) return m * mag;
  return 10 * mag;
}

function fmtTick(v, step) {
  if (Math.abs(v) < step * 1e-9) return "0";
  const dec = Math.max(0, Math.ceil(-Math.log10(step) - 1e-9));
  if (Math.abs(v) >= 1e7 || Math.abs(v) < 1e-5 || dec > 8)
    return Number(v.toPrecision(6)).toExponential().replace("e+", "e");
  return v.toFixed(Math.min(dec, 10));
}
function fmtVal(v) { return Number(v.toPrecision(5)).toString(); }

function haloText(t, x, y, color, font, align, base) {
  ctx.font = font; ctx.textAlign = align; ctx.textBaseline = base;
  ctx.lineJoin = "round"; ctx.lineWidth = 3.5; ctx.strokeStyle = "rgba(251,255,249,0.92)";
  ctx.strokeText(t, x, y);
  ctx.fillStyle = color; ctx.fillText(t, x, y);
}

function rr(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function gridLines(step, color, width) {
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
  const k0 = Math.ceil((0 - ox) / s / step), k1 = Math.floor((W - ox) / s / step);
  for (let k = k0; k <= k1; k++) {
    const px = Math.round(ox + k * step * s) + 0.5; ctx.moveTo(px, 0); ctx.lineTo(px, Hh);
  }
  const j0 = Math.ceil((oy - Hh) / s / step), j1 = Math.floor(oy / s / step);
  for (let j = j0; j <= j1; j++) {
    const py = Math.round(oy - j * step * s) + 0.5; ctx.moveTo(0, py); ctx.lineTo(W, py);
  }
  ctx.stroke();
}

function drawSheet() {
  ctx.fillStyle = "#fbfff9"; ctx.fillRect(0, 0, W, Hh);
  const major = niceStep(90 / s), minor = major / 5;
  gridLines(minor, "#d7ecdc", 0.7);
  gridLines(major, "#8cc79b", 1.2);

  // axes through the origin
  ctx.strokeStyle = "#1b1b1b"; ctx.lineWidth = 2; ctx.beginPath();
  if (oy >= 0 && oy <= Hh) { ctx.moveTo(0, oy); ctx.lineTo(W, oy); }
  if (ox >= 0 && ox <= W) { ctx.moveTo(ox, 0); ctx.lineTo(ox, Hh); }
  ctx.stroke();

  // tick labels (stay on screen even when an axis is panned out of view)
  const axY = clamp(oy, 0, Hh), axX = clamp(ox, 0, W);
  const below = axY < Hh - 22, leftSide = axX > 46;
  const tf = "11px " + FONT;
  const k0 = Math.ceil((0 - ox) / s / major), k1 = Math.floor((W - ox) / s / major);
  for (let k = k0; k <= k1; k++) {
    if (k === 0) continue;
    haloText(fmtTick(k * major, major), ox + k * major * s, below ? axY + 5 : axY - 5,
             "#222", tf, "center", below ? "top" : "bottom");
  }
  const j0 = Math.ceil((oy - Hh) / s / major), j1 = Math.floor(oy / s / major);
  for (let j = j0; j <= j1; j++) {
    if (j === 0) continue;
    haloText(fmtTick(j * major, major), leftSide ? axX - 6 : axX + 6, oy - j * major * s,
             "#222", tf, leftSide ? "right" : "left", "middle");
  }
  haloText("0", leftSide ? axX - 6 : axX + 6, below ? axY + 5 : axY - 5,
           "#222", tf, leftSide ? "right" : "left", below ? "top" : "bottom");
}

function drawCurve() {
  ctx.save();
  ctx.beginPath(); ctx.rect(0, 0, W, Hh); ctx.clip();
  ctx.strokeStyle = "#d62728"; ctx.lineWidth = 2.6; ctx.lineJoin = "round"; ctx.lineCap = "round";
  ctx.beginPath();
  let pen = false, prev = 0;
  for (let px = 0; px <= W; px += 0.5) {
    const y = fx((px - ox) / s);
    if (!isFinite(y)) { pen = false; continue; }
    let py = oy - y * s;
    if (py > 1e5) py = 1e5; else if (py < -1e5) py = -1e5;
    if (pen && Math.abs(py - prev) > Hh * 2) pen = false;   // break at asymptotes
    if (pen) ctx.lineTo(px, py); else ctx.moveTo(px, py);
    pen = true; prev = py;
  }
  ctx.stroke();
  ctx.restore();
}

function infoBox(text, y) {
  ctx.font = "bold 13px " + FONT;
  const w = Math.min(ctx.measureText(text).width + 24, W - 130);
  ctx.fillStyle = "rgba(255,255,255,0.88)"; rr(10, y, w, 26, 8); ctx.fill();
  ctx.strokeStyle = "rgba(0,0,0,0.15)"; ctx.lineWidth = 1; ctx.stroke();
  ctx.fillStyle = "#222"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
  ctx.fillText(text, 22, y + 13, Math.max(20, w - 24));
}

function drawCursor() {
  if (!mouse) return;
  const x = (mouse.x - ox) / s, y = fx(x);
  if (!isFinite(y)) { infoBox("x = " + fmtVal(x) + "   f(x) undefined", 42); return; }
  const py = oy - y * s;
  infoBox("x = " + fmtVal(x) + "   f(x) = " + fmtVal(y), 42);
  if (py < -40 || py > Hh + 40) return;

  const axY = clamp(oy, 0, Hh), axX = clamp(ox, 0, W);
  const blue = "#1f4fd8";
  ctx.save();
  ctx.setLineDash([5, 4]); ctx.strokeStyle = blue; ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(mouse.x, py); ctx.lineTo(mouse.x, axY);
  ctx.moveTo(mouse.x, py); ctx.lineTo(axX, py);
  ctx.stroke();
  ctx.restore();

  ctx.beginPath(); ctx.arc(mouse.x, py, 5.5, 0, Math.PI * 2);
  ctx.fillStyle = "#d62728"; ctx.fill();
  ctx.lineWidth = 2; ctx.strokeStyle = "#fff"; ctx.stroke();

  const below = axY < Hh - 28;
  haloText(fmtVal(x), mouse.x, below ? axY + 8 : axY - 8, blue, "bold 13px " + FONT,
           "center", below ? "top" : "bottom");
  const leftSide = axX > 80;
  haloText(fmtVal(y), leftSide ? axX - 8 : axX + 8, py, blue, "bold 13px " + FONT,
           leftSide ? "right" : "left", "middle");
}

function draw() {
  drawSheet();
  drawCurve();
  infoBox("f(x) = " + LABEL, 10);
  drawCursor();
}

// ---- mouse / touch interaction
cv.addEventListener("wheel", e => {
  e.preventDefault();
  touched = true;
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  let k = Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015));
  const ns = clamp(s * k, 1e-8, 1e8);
  k = ns / s;
  ox = mx - (mx - ox) * k;      // keep the point under the mouse fixed
  oy = my - (my - oy) * k;
  s = ns;
  mouse = { x: mx, y: my };
  draw();
}, { passive: false });

cv.addEventListener("pointerdown", e => {
  cv.setPointerCapture(e.pointerId);
  drag = { x: e.clientX, y: e.clientY };
  cv.style.cursor = "grabbing";
});
cv.addEventListener("pointermove", e => {
  const r = cv.getBoundingClientRect();
  mouse = { x: e.clientX - r.left, y: e.clientY - r.top };
  if (drag) {
    touched = true;
    ox += e.clientX - drag.x; oy += e.clientY - drag.y;
    drag = { x: e.clientX, y: e.clientY };
  }
  draw();
});
function endDrag() { drag = null; cv.style.cursor = "crosshair"; }
cv.addEventListener("pointerup", endDrag);
cv.addEventListener("pointercancel", endDrag);
cv.addEventListener("pointerleave", () => { if (!drag) { mouse = null; draw(); } });
cv.addEventListener("dblclick", () => { touched = false; reset(); draw(); });
document.getElementById("reset").addEventListener("click", () => { touched = false; reset(); draw(); });

if (window.ResizeObserver) new ResizeObserver(resize).observe(cv);
window.addEventListener("resize", resize);
resize();
</script>
</body></html>
"""


def build_html(js_expr, label):
    return (
        HTML_TEMPLATE
        .replace("__EXPR__", safe_json(js_expr))
        .replace("__LABEL__", safe_json(label.strip()))
        .replace("__H__", str(PLOT_H))
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

try:
    tree = parse_expression(text)
    code = compile(tree, "<f(x)>", "eval")
    with np.errstate(all="ignore"):  # quick test run so mistakes show up here
        eval(code, {"__builtins__": {}}, dict(ALLOWED, x=np.linspace(-2, 2, 9)))
    js_expr = to_js(tree)
except Exception as err:
    st.error(f"Couldn't use that expression: {err}")
    st.stop()

components.html(build_html(js_expr, text), height=PLOT_H + 6)
