"""Streamlit app: plot an equation in x and y (e.g. x^2 + y^2 = 1) on a zoomable,
square graph-paper sheet.

Single file. Needs only streamlit and numpy (numpy comes with Streamlit),
so no requirements.txt is needed.

Run with:
    streamlit run plot_equation.py

The equation box is in the left column and the square graph sheet is on the
right. The graph is drawn in the browser (HTML canvas) with a marching-squares
contour of F(x, y) = left side - right side, so it is redrawn instantly while
you zoom (mouse wheel) and pan (drag). x and y always share the same scale.
"""

import ast
import json
import math
import re

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

PLOT_MAX = 720  # largest side (pixels) of the square graph sheet

# ---------------------------------------------------------------- expression parsing

# Names the user is allowed to use inside the equation
ALLOWED = {
    "x": None, "y": None,  # the variables, filled in at evaluation time
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

TOKEN_RE = re.compile(r"\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|[A-Za-z_]\w*|\S")


def _kind(tok):
    if tok[0].isdigit() or tok[0] == ".":
        return "num"
    if tok[0].isalpha() or tok[0] == "_":
        return "id"
    return tok


def add_implicit_multiplication(text):
    """Let people write 2x, 3(x+1), xy, x(y+1), (x+1)(x-1), 2pi ... like on paper."""
    expanded = []
    for tok in TOKEN_RE.findall(text):
        if len(tok) > 1 and tok not in ALLOWED and re.fullmatch(r"[xy]+", tok):
            for i, ch in enumerate(tok):  # 'xy' -> x*y
                if i:
                    expanded.append("*")
                expanded.append(ch)
        else:
            expanded.append(tok)

    out = []
    for tok in expanded:
        if out:
            prev, cur = _kind(out[-1]), _kind(tok)
            is_call = prev == "id" and callable(ALLOWED.get(out[-1])) and cur == "("
            if prev in ("num", "id", ")") and cur in ("id", "(") and not is_call:
                out.append("*")
            elif prev == "num" and cur == "num":
                out.append(" ")  # leave it to Python to report the syntax error
        out.append(tok)
    return "".join(out)


def prepare_equation(text):
    """'x^2 + y^2 = 1'  ->  '(x^2+y^2)-(1)'  (the curve is where this equals 0)."""
    s = add_implicit_multiplication(text)
    if not s.strip():
        raise ValueError("enter an equation")
    if re.search(r"(?<![<>!=])==(?!=)", s):
        raise ValueError("use a single '=' sign")
    sides = re.split(r"(?<![<>!=])=(?!=)", s)
    if len(sides) == 1:
        return sides[0]  # no '=': the expression is treated as 'expression = 0'
    if len(sides) != 2:
        raise ValueError("an equation can contain only one '=' sign")
    lhs, rhs = sides
    if not lhs.strip() or not rhs.strip():
        raise ValueError("both sides of '=' need an expression")
    return f"({lhs})-({rhs})"


def parse_expression(text):
    """Parse and validate the text. Returns a safe AST or raises ValueError."""
    tree = ast.parse(text.strip().replace("^", "**"), mode="eval")
    call_funcs = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"'{type(node).__name__}' is not allowed")
        if isinstance(node, ast.Name):
            if node.id not in ALLOWED:
                raise ValueError(f"unknown name '{node.id}'")
            if callable(ALLOWED[node.id]) and id(node) not in call_funcs:
                raise ValueError(f"'{node.id}' needs brackets, e.g. {node.id}(x)")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.keywords:
                raise ValueError("only simple function calls are allowed")
            if node.func.id in ("x", "y") or not callable(ALLOWED[node.func.id]):
                raise ValueError(f"'{node.func.id}' is not a function")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("only numbers are allowed as constants")
    return tree


# ---------------------------------------------------------------- AST -> JavaScript
# The validated AST is translated to JavaScript so the browser can re-evaluate
# F(x, y) while you zoom and pan.

JS_NAMES = {"x": "x", "y": "y", "pi": "Math.PI", "e": "Math.E", "E": "Math.E"}
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
  #wrap { position: relative; box-sizing: border-box; width: __MAX__px; height: __MAX__px;
          border: 1.5px solid #555; border-radius: 6px; overflow: hidden; background: #fbfff9; }
  canvas { display: block; cursor: crosshair; touch-action: none; }
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
const EXPR = __EXPR__;      // JavaScript source of F(x, y); the curve is where F = 0
const LABEL = __LABEL__;
const MAXSIZE = __MAX__;
const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

let compiled;
try { compiled = new Function("x", "y", "H", "mod", "return " + EXPR); }
catch (e) { compiled = function () { return NaN; }; }
const Hv = v => (v > 0 ? 1 : (v < 0 ? 0 : 0.5));
const modf = (a, b) => a - b * Math.floor(a / b);
function F(x, y) {
  try { const v = compiled(x, y, Hv, modf); return typeof v === "number" ? v : Number(v); }
  catch (e) { return NaN; }
}

const wrap = document.getElementById("wrap");
const cv = document.getElementById("c");
const ctx = cv.getContext("2d");
const base = document.createElement("canvas");   // cached sheet + curve
const bctx = base.getContext("2d");
let g = ctx;                                     // context the helpers draw on
let W = 0, Hh = 0, dpr = 1;
let s = 40, ox = 0, oy = 0;      // s = pixels per unit (same for x and y); (ox, oy) = pixel of the origin
let touched = false, mouse = null, drag = null, dirty = true;

function reset() { s = W / 12; ox = W / 2; oy = Hh / 2; dirty = true; }

function resize() {
  dpr = window.devicePixelRatio || 1;
  const size = Math.max(220, Math.min(MAXSIZE, document.documentElement.clientWidth));
  wrap.style.width = size + "px"; wrap.style.height = size + "px";
  W = Hh = Math.max(100, Math.min(wrap.clientWidth, wrap.clientHeight));   // square sheet
  cv.style.width = W + "px"; cv.style.height = Hh + "px";
  cv.width = base.width = Math.round(W * dpr);
  cv.height = base.height = Math.round(Hh * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!touched) reset();
  dirty = true;
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
function fmtVal(v) {
  if (Math.abs(v) < 1e-7 / s) v = 0;
  return Number(v.toPrecision(5)).toString();
}

function haloText(t, x, y, color, font, align, baseline) {
  g.font = font; g.textAlign = align; g.textBaseline = baseline;
  g.lineJoin = "round"; g.lineWidth = 3.5; g.strokeStyle = "rgba(251,255,249,0.92)";
  g.strokeText(t, x, y);
  g.fillStyle = color; g.fillText(t, x, y);
}

function rr(x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

function gridLines(step, color, width) {
  g.strokeStyle = color; g.lineWidth = width; g.beginPath();
  const k0 = Math.ceil((0 - ox) / s / step), k1 = Math.floor((W - ox) / s / step);
  for (let k = k0; k <= k1; k++) {
    const px = Math.round(ox + k * step * s) + 0.5; g.moveTo(px, 0); g.lineTo(px, Hh);
  }
  const j0 = Math.ceil((oy - Hh) / s / step), j1 = Math.floor(oy / s / step);
  for (let j = j0; j <= j1; j++) {
    const py = Math.round(oy - j * step * s) + 0.5; g.moveTo(0, py); g.lineTo(W, py);
  }
  g.stroke();
}

function drawSheet() {
  g.fillStyle = "#fbfff9"; g.fillRect(0, 0, W, Hh);
  const major = niceStep(90 / s), minor = major / 5;
  gridLines(minor, "#d7ecdc", 0.7);
  gridLines(major, "#8cc79b", 1.2);

  // axes through the origin
  g.strokeStyle = "#1b1b1b"; g.lineWidth = 2; g.beginPath();
  if (oy >= 0 && oy <= Hh) { g.moveTo(0, oy); g.lineTo(W, oy); }
  if (ox >= 0 && ox <= W) { g.moveTo(ox, 0); g.lineTo(ox, Hh); }
  g.stroke();

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

  // axis names
  const nf = "italic bold 15px " + FONT;
  if (oy >= 16 && oy <= Hh - 16) haloText("x", W - 8, oy - 6, "#222", nf, "right", "bottom");
  if (ox >= 16 && ox <= W - 16) haloText("y", ox + 8, 8, "#222", nf, "left", "top");
}

// Marching squares: draw the contour F(x, y) = 0 over the visible area.
function drawCurve() {
  const cs = 3;                                  // cell size in pixels
  const nx = Math.ceil(W / cs), ny = Math.ceil(Hh / cs), stride = nx + 1;
  const val = new Float64Array(stride * (ny + 1));
  for (let j = 0; j <= ny; j++) {
    const y = (oy - j * cs) / s;
    for (let i = 0; i <= nx; i++) {
      const v = F((i * cs - ox) / s, y);
      val[j * stride + i] = isFinite(v) ? v : NaN;
    }
  }

  g.save();
  g.beginPath(); g.rect(0, 0, W, Hh); g.clip();
  g.strokeStyle = "#d62728"; g.lineWidth = 2.6; g.lineCap = "round"; g.lineJoin = "round";
  g.beginPath();
  const seg = (a, b) => { g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); };

  for (let j = 0; j < ny; j++) {
    for (let i = 0; i < nx; i++) {
      const tl = val[j * stride + i], tr = val[j * stride + i + 1];
      const bl = val[(j + 1) * stride + i], br = val[(j + 1) * stride + i + 1];
      if (!(tl === tl && tr === tr && bl === bl && br === br)) continue;   // skip NaN cells
      const code = (tl > 0 ? 8 : 0) | (tr > 0 ? 4 : 0) | (br > 0 ? 2 : 0) | (bl > 0 ? 1 : 0);
      if (code === 0 || code === 15) continue;
      const x0 = i * cs, y0 = j * cs;
      const T = () => [x0 + cs * tl / (tl - tr), y0];
      const R = () => [x0 + cs, y0 + cs * tr / (tr - br)];
      const B = () => [x0 + cs * bl / (bl - br), y0 + cs];
      const L = () => [x0, y0 + cs * tl / (tl - bl)];
      switch (code) {
        case 1: case 14: seg(L(), B()); break;
        case 2: case 13: seg(B(), R()); break;
        case 3: case 12: seg(L(), R()); break;
        case 4: case 11: seg(T(), R()); break;
        case 6: case 9: seg(T(), B()); break;
        case 7: case 8: seg(L(), T()); break;
        case 5: {
          if ((tl + tr + br + bl) > 0) { seg(L(), T()); seg(B(), R()); }
          else { seg(T(), R()); seg(L(), B()); }
          break;
        }
        case 10: {
          if ((tl + tr + br + bl) > 0) { seg(T(), R()); seg(L(), B()); }
          else { seg(L(), T()); seg(B(), R()); }
          break;
        }
      }
    }
  }
  g.stroke();
  g.restore();
}

function renderBase() {
  g = bctx;
  bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawSheet();
  drawCurve();
  g = ctx;
}

function infoBox(text, y) {
  g.font = "bold 13px " + FONT;
  const w = Math.min(g.measureText(text).width + 24, W - 130);
  g.fillStyle = "rgba(255,255,255,0.88)"; rr(10, y, w, 26, 8); g.fill();
  g.strokeStyle = "rgba(0,0,0,0.15)"; g.lineWidth = 1; g.stroke();
  g.fillStyle = "#222"; g.textAlign = "left"; g.textBaseline = "middle";
  g.fillText(text, 22, y + 13, Math.max(20, w - 24));
}

// Snap the mouse to the nearest point of the curve (Newton projection onto F = 0).
function snap(mx, my) {
  let x = (mx - ox) / s, y = (oy - my) / s;
  const h = 0.5 / s;
  const grad = (a, b) => [(F(a + h, b) - F(a - h, b)) / (2 * h), (F(a, b + h) - F(a, b - h)) / (2 * h)];
  for (let it = 0; it < 14; it++) {
    const v = F(x, y);
    if (!isFinite(v)) return null;
    const [gx, gy] = grad(x, y), g2 = gx * gx + gy * gy;
    if (!(g2 > 0) || !isFinite(g2)) return null;
    x -= v * gx / g2; y -= v * gy / g2;
  }
  const v = F(x, y), [gx, gy] = grad(x, y), gn = Math.hypot(gx, gy);
  if (!isFinite(v) || !(gn > 0)) return null;
  if (Math.abs(v) / gn * s > 0.4) return null;            // did not converge -> not on the curve
  const px = ox + x * s, py = oy - y * s;
  if (Math.hypot(px - mx, py - my) > 30) return null;     // too far from the mouse
  return { x: x, y: y, px: px, py: py };
}

function drawCursor() {
  if (!mouse) return;
  const p = snap(mouse.x, mouse.y);
  if (!p) {
    infoBox("x = " + fmtVal((mouse.x - ox) / s) + "   y = " + fmtVal((oy - mouse.y) / s), 42);
    return;
  }
  infoBox("x = " + fmtVal(p.x) + "   y = " + fmtVal(p.y), 42);

  const axY = clamp(oy, 0, Hh), axX = clamp(ox, 0, W);
  const blue = "#1f4fd8";
  g.save();
  g.setLineDash([5, 4]); g.strokeStyle = blue; g.lineWidth = 1.4;
  g.beginPath();
  g.moveTo(p.px, p.py); g.lineTo(p.px, axY);
  g.moveTo(p.px, p.py); g.lineTo(axX, p.py);
  g.stroke();
  g.restore();

  g.beginPath(); g.arc(p.px, p.py, 5.5, 0, Math.PI * 2);
  g.fillStyle = "#d62728"; g.fill();
  g.lineWidth = 2; g.strokeStyle = "#fff"; g.stroke();

  const below = axY < Hh - 28, leftSide = axX > 80;
  haloText(fmtVal(p.x), p.px, below ? axY + 8 : axY - 8, blue, "bold 13px " + FONT,
           "center", below ? "top" : "bottom");
  haloText(fmtVal(p.y), leftSide ? axX - 8 : axX + 8, p.py, blue, "bold 13px " + FONT,
           leftSide ? "right" : "left", "middle");
}

function draw() {
  if (dirty) { renderBase(); dirty = false; }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.drawImage(base, 0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  g = ctx;
  infoBox(LABEL, 10);
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
  dirty = true;
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
    dirty = true;
  }
  draw();
});
function endDrag() { drag = null; cv.style.cursor = "crosshair"; }
cv.addEventListener("pointerup", endDrag);
cv.addEventListener("pointercancel", endDrag);
cv.addEventListener("pointerleave", () => { if (!drag) { mouse = null; draw(); } });
cv.addEventListener("dblclick", () => { touched = false; reset(); draw(); });
document.getElementById("reset").addEventListener("click", () => { touched = false; reset(); draw(); });

if (window.ResizeObserver) new ResizeObserver(resize).observe(document.documentElement);
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
        .replace("__MAX__", str(PLOT_MAX))
    )


# ---------------------------------------------------------------- the app

st.set_page_config(page_title="Equation plotter", page_icon="📈", layout="wide")
st.title("Plot an equation in x and y")

left, right = st.columns([1, 2], gap="large")

js_expr = None
with left:
    text = st.text_input(
        "Equation",
        value="x^2 + y^2 = 1",
        help="Use x and y. Powers: ^ or **. Multiplication can be written as 2x or 2*x.",
    )
    st.caption(
        "Examples: `x^2 + y^2 = 1`, `y = sin(x)`, `x^2/4 + y^2/9 = 1`, "
        "`x*y = 1`, `y^2 = x^3 - x`, `abs(x) + abs(y) = 3`"
    )
    st.caption(
        "Available: sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, exp, log, ln, log10, "
        "sqrt, abs, sign, floor, ceil, min, max, Heaviside, where(cond, a, b), pi, e. "
        "Without an '=' sign the expression is plotted as 'expression = 0'."
    )
    st.caption("Tip: for curves like y = 1/x, write `x*y = 1` for the cleanest result.")

    try:
        tree = parse_expression(prepare_equation(text))
        code = compile(tree, "<F(x,y)>", "eval")
        with np.errstate(all="ignore"):  # quick test run so mistakes show up here
            eval(code, {"__builtins__": {}},
                 dict(ALLOWED, x=np.linspace(-2, 2, 9)[:, None], y=np.linspace(-2, 2, 9)[None, :]))
        js_expr = to_js(tree)
    except Exception as err:
        st.error(f"Couldn't use that equation: {err}")

with right:
    if js_expr is not None:
        components.html(build_html(js_expr, text), height=PLOT_MAX + 6)
