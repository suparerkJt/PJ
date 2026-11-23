"""Scientific graphing calculator for Streamlit (single file).

Needs only streamlit (no other packages, no requirements.txt).

Run with:
    streamlit run plot_calculator.py

Everything runs in the browser, so zooming, panning and typing feel instant:
  * Graph: several equations / inequalities at once (y = sin(x), x^2 + y^2 = 9,
    y > x^2, r = 2 + 2cos(theta) ...), zoom with the mouse wheel, drag to pan,
    click a curve to pin a point, automatic roots / intercepts / intersections.
  * Calculator: scientific keypad, RAD / DEG mode, Ans, history, n!, nCr, nPr,
    trig / inverse trig / hyperbolic functions, logs, roots and more.
"""

import streamlit as st
import streamlit.components.v1 as components

HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:transparent;color:#1d2a22;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:14px}
#app{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start;padding:2px}
.card{background:#fff;border:1px solid #c9d3cc;border-radius:10px;padding:10px}
#side{flex:0 0 340px;width:340px;max-width:100%;display:flex;flex-direction:column;gap:10px}
#plotcol{flex:1 1 380px;min-width:280px}
h3{margin:0;font-size:15px}
.bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.seg{display:inline-flex;border:1px solid #8a9a8f;border-radius:7px;overflow:hidden}
.seg button{border:0;background:#fff;padding:3px 10px;font-size:12px;cursor:pointer;color:#1d2a22}
.seg button.on{background:#2f7d4f;color:#fff}
.row{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.dot{width:20px;height:20px;border-radius:50%;border:2px solid;cursor:pointer;flex:0 0 20px;padding:0}
.row input,#calcIn{flex:1;min-width:0;padding:6px 8px;font-size:14px;border:1px solid #b5c2b9;
  border-radius:6px;font-family:ui-monospace,Menlo,Consolas,monospace;background:#fff;color:#1d2a22}
.row input:focus,#calcIn:focus{outline:2px solid #2f7d4f;border-color:#2f7d4f}
.del{border:0;background:none;font-size:16px;color:#777;cursor:pointer;padding:0 4px}
.err{color:#b3261e;font-size:12px;margin:-2px 0 4px 26px}
.link{border:1px dashed #8a9a8f;background:none;border-radius:6px;padding:4px 10px;
  font-size:12px;cursor:pointer;color:#2f7d4f;width:100%;margin-top:2px}
#calcIn{width:100%;font-size:15px}
#calcOut{min-height:34px;text-align:right;font-size:22px;font-weight:600;padding:4px 2px;word-break:break-all}
#calcOut.bad{color:#b3261e;font-size:13px;font-weight:400}
#hist{max-height:64px;overflow:auto;font-size:12px;color:#456;font-family:ui-monospace,Menlo,Consolas,monospace;margin-bottom:6px}
#hist div{cursor:pointer;padding:1px 2px;text-align:right}
#pad{display:grid;grid-template-columns:repeat(6,1fr);gap:4px}
#pad button{padding:7px 0;font-size:13px;border:1px solid #b5c2b9;background:#eaf1ec;border-radius:6px;cursor:pointer;color:#1d2a22}
#pad button:hover{background:#d9e8dd}
#pad button.num{background:#fff;font-weight:600}
#pad button.act{background:#2f7d4f;color:#fff;border-color:#2f7d4f}
#pad button.clr{background:#fbe9e7;border-color:#e0b4ae}
#wrap{position:relative;border:1.5px solid #555;border-radius:6px;overflow:hidden;background:#fbfff9;margin:0 auto}
canvas{display:block;cursor:crosshair;touch-action:none}
#hint{position:absolute;left:8px;bottom:8px;font-size:12px;color:#355;background:rgba(255,255,255,.82);
  padding:2px 9px;border-radius:10px;pointer-events:none}
.tools{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:center;margin-top:8px;font-size:12px}
.tools button{font-size:12px;padding:4px 10px;border:1px solid #888;border-radius:6px;background:#fff;color:#222;cursor:pointer}
.tools button:hover{background:#eef6ef}
.tools label{display:flex;align-items:center;gap:4px;cursor:pointer}
select{width:100%;padding:6px;border:1px solid #b5c2b9;border-radius:6px;background:#fff;color:#1d2a22;font-size:13px;margin-bottom:6px}
.crow{display:flex;align-items:center;gap:6px;margin-bottom:6px;font-size:13px;flex-wrap:wrap}
.crow button{font-size:12px;padding:4px 8px;border:1px solid #8a9a8f;border-radius:6px;background:#eaf1ec;color:#1d2a22;cursor:pointer}
.crow button:hover{background:#d9e8dd}
.crow input{width:62px;padding:4px 6px;font-size:13px;border:1px solid #b5c2b9;border-radius:6px;
  font-family:ui-monospace,Menlo,Consolas,monospace;background:#fff;color:#1d2a22}
.crow input:focus{outline:2px solid #2f7d4f;border-color:#2f7d4f}
.row input:disabled{background:#f1f4f2;color:#456}
#cOut{font-size:12.5px;line-height:1.5;min-height:18px;white-space:pre-wrap;word-break:break-word;
  font-family:ui-monospace,Menlo,Consolas,monospace}
#cOut.bad{color:#b3261e}
</style></head>
<body>
<div id="app">
  <div id="side">
    <div class="card">
      <div class="bar"><h3>Graph</h3>
        <div class="seg" id="modeSeg"><button data-m="rad" class="on">RAD</button><button data-m="deg">DEG</button></div>
      </div>
      <div id="rows"></div>
      <button class="link" id="addRow">+ Add equation</button>
    </div>
    <div class="card">
      <div class="bar"><h3>Calculus</h3><span style="font-size:11px;color:#678">for y = f(x) curves</span></div>
      <select id="cFn"></select>
      <div class="crow"><button id="bD1">f&prime;(x)</button><button id="bD2">f&Prime;(x)</button>
        <button id="bInt">&int; f dx</button><span style="font-size:11px;color:#678">(plots a new curve; &int; starts at a)</span></div>
      <div class="crow">x&#8320; <input id="x0" value="1"><button id="bTan">Tangent &amp; f&prime;(x&#8320;)</button></div>
      <div class="crow">a <input id="ia" value="0"> b <input id="ib" value="pi"><button id="bDef">&int;&#8336;&#7495; f dx</button></div>
      <div id="cOut"></div>
      <button class="link" id="cClear">Clear tangent &amp; shaded area</button>
    </div>
    <div class="card">
      <div class="bar"><h3>Calculator</h3><span style="font-size:11px;color:#678">Enter = evaluate</span></div>
      <input id="calcIn" placeholder="e.g. sin(30&deg;) + 2^10 / 5!" autocomplete="off" spellcheck="false">
      <div id="calcOut"></div>
      <div id="hist"></div>
      <div id="pad"></div>
    </div>
  </div>
  <div id="plotcol">
    <div id="wrap"><canvas id="c"></canvas>
      <div id="hint">Scroll to zoom &middot; drag to pan &middot; click a curve to pin a point</div>
    </div>
    <div class="tools">
      <label><input type="checkbox" id="kp" checked> Roots, intercepts &amp; intersections</label>
      <button id="clearPins">Clear pinned points</button>
      <button id="reset">Reset view</button>
    </div>
  </div>
</div>
<script>
"use strict";
// ==== PARSER BEGIN
let K = 1;          // trig unit: 1 = radians, PI/180 = degrees
let ANS = 0;

function gamma(z) {
  if (z < 0.5) return Math.PI / (Math.sin(Math.PI * z) * gamma(1 - z));
  z -= 1;
  const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
  let a = c[0]; const t = z + 7.5;
  for (let i = 1; i < 9; i++) a += c[i] / (z + i);
  return Math.sqrt(2 * Math.PI) * Math.pow(t, z + 0.5) * Math.exp(-t) * a;
}
function fact(n) {
  if (Number.isInteger(n)) {
    if (n < 0) return NaN;
    if (n > 170) return Infinity;
    let r = 1; for (let i = 2; i <= n; i++) r *= i; return r;
  }
  return gamma(n + 1);
}
function pw(a, b) {            // a^b, with real odd roots of negative numbers (e.g. (-8)^(1/3) = -2)
  if (a < 0 && !Number.isInteger(b)) {
    const inv = 1 / b;
    if (Math.abs(inv - Math.round(inv)) < 1e-9 && Math.abs(Math.round(inv)) % 2 === 1) return -Math.pow(-a, b);
    return NaN;
  }
  return Math.pow(a, b);
}
const cl = v => (Math.abs(v) < 1e-15 ? 0 : v);
function ncr(n, k) {
  if (!Number.isInteger(n) || !Number.isInteger(k) || n < 0 || k < 0) return NaN;
  if (k > n) return 0;
  k = Math.min(k, n - k); let r = 1;
  for (let i = 1; i <= k; i++) r = r * (n - k + i) / i;
  return Math.round(r);
}
function npr(n, k) {
  if (!Number.isInteger(n) || !Number.isInteger(k) || n < 0 || k < 0) return NaN;
  if (k > n) return 0;
  let r = 1; for (let i = 0; i < k; i++) r *= (n - i); return r;
}

const $f = {
  sin: v => cl(Math.sin(v * K)), cos: v => cl(Math.cos(v * K)), tan: v => Math.tan(v * K),
  sec: v => 1 / Math.cos(v * K), csc: v => 1 / Math.sin(v * K), cot: v => 1 / Math.tan(v * K),
  asin: v => Math.asin(v) / K, acos: v => Math.acos(v) / K, atan: v => Math.atan(v) / K,
  atan2: (a, b) => Math.atan2(a, b) / K,
  sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh, asinh: Math.asinh, acosh: Math.acosh, atanh: Math.atanh,
  exp: Math.exp, ln: Math.log, log: Math.log10, log2: Math.log2, log10: Math.log10,
  sqrt: Math.sqrt, cbrt: Math.cbrt, abs: Math.abs, sign: Math.sign,
  floor: Math.floor, ceil: Math.ceil, round: Math.round, min: Math.min, max: Math.max,
  mod: (a, b) => a - b * Math.floor(a / b), ncr: ncr, npr: npr, fact: fact, pw: pw
};
const FN = {};
Object.keys($f).forEach(k => { FN[k] = (["atan2", "min", "max", "mod", "ncr", "npr"].includes(k)) ? 2 : 1; });
delete FN.pw;
const ALIAS = { arcsin: "asin", arccos: "acos", arctan: "atan" };
const NAMES = Object.keys(FN).concat(Object.keys(ALIAS), ["pi", "tau", "e", "x", "y", "r", "theta", "ans"])
  .sort((a, b) => b.length - a.length);

function normalize(s) {
  return String(s).toLowerCase()
    .replace(/[×·⋅]/g, "*").replace(/÷/g, "/").replace(/[−–]/g, "-")
    .replace(/\*\*/g, "^").replace(/π/g, "pi").replace(/θ/g, "theta").replace(/τ/g, "tau")
    .replace(/√/g, " sqrt ").replace(/<=/g, "≤").replace(/>=/g, "≥").replace(/==/g, "=");
}

function tokenize(s) {
  s = normalize(s);
  const t = []; let i = 0, m;
  while (i < s.length) {
    const ch = s[i], rest = s.slice(i);
    if (/\s/.test(ch)) { i++; continue; }
    if ((m = /^(\d+\.?\d*|\.\d+)(e[+-]?\d+)?/.exec(rest))) { t.push({ t: "num", v: m[0] }); i += m[0].length; continue; }
    if ((m = /^(log10|log2|atan2)/.exec(rest))) { t.push({ t: "id", v: m[0] }); i += m[0].length; continue; }
    if (/[a-z]/.test(ch)) {
      const run = /^[a-z]+/.exec(rest)[0]; let k = 0;
      while (k < run.length) {
        const nm = NAMES.find(n => run.startsWith(n, k));
        if (!nm) throw new Error('Unknown name "' + run.slice(k) + '"');
        t.push({ t: "id", v: nm }); k += nm.length;
      }
      i += run.length; continue;
    }
    if ("+-*/^()!,°%".includes(ch)) { t.push({ t: "op", v: ch }); i++; continue; }
    throw new Error('Unexpected "' + ch + '"');
  }
  return t;
}

// Turns text into JavaScript source (only whitelisted names can appear in it).
function compileExpr(str) {
  const toks = tokenize(str);
  if (!toks.length) throw new Error("Empty expression");
  let p = 0; const used = new Set();
  const next = () => toks[p++];
  const isOp = v => toks[p] && toks[p].t === "op" && toks[p].v === v;
  const startsPrimary = () => { const k = toks[p]; return !!k && (k.t === "num" || k.t === "id" || (k.t === "op" && k.v === "(")); };
  const isFnTok = k => k && k.t === "id" && FN[ALIAS[k.v] || k.v] !== undefined;

  function expr() {
    let a = term();
    while (isOp("+") || isOp("-")) { const o = next().v; a = "(" + a + o + term() + ")"; }
    return a;
  }
  function term() {
    let a = unary();
    for (;;) {
      if (isOp("*") || isOp("/")) { const o = next().v; a = "(" + a + o + unary() + ")"; }
      else if (startsPrimary()) a = "(" + a + "*" + unary() + ")";   // implicit multiplication: 2x, 3(x+1)
      else break;
    }
    return a;
  }
  function unary() {
    if (isOp("-")) { next(); return "(-" + unary() + ")"; }
    if (isOp("+")) { next(); return unary(); }
    return power();
  }
  function power() {
    const a = postfix();
    if (isOp("^")) { next(); return "$f.pw(" + a + "," + unary() + ")"; }
    return a;
  }
  function postfix() {
    let a = primary();
    for (;;) {
      if (isOp("!")) { next(); a = "$f.fact(" + a + ")"; }
      else if (isOp("°")) { next(); a = "(" + a + "*" + (Math.PI / 180) + "/K)"; }
      else if (isOp("%")) { next(); a = "(" + a + "/100)"; }
      else break;
    }
    return a;
  }
  function primary() {
    const k = next();
    if (!k) throw new Error("Expression ends too early");
    if (k.t === "num") return "(" + parseFloat(k.v) + ")";
    if (k.t === "op" && k.v === "(") {
      const a = expr();
      if (!isOp(")")) throw new Error("Missing )");
      next(); return "(" + a + ")";
    }
    if (k.t === "id") {
      const n = k.v;
      if (n === "pi") return "(" + Math.PI + ")";
      if (n === "e") return "(" + Math.E + ")";
      if (n === "tau") return "(" + 2 * Math.PI + ")";
      if (n === "ans") return "ANS";
      if (n === "x" || n === "y" || n === "r" || n === "theta") { used.add(n); return n === "theta" ? "th" : n; }
      const name = ALIAS[n] || n, need = FN[name];
      let args = [];
      if (isOp("(")) {
        next();
        if (!isOp(")")) for (;;) { args.push(expr()); if (isOp(",")) { next(); continue; } break; }
        if (!isOp(")")) throw new Error("Missing )");
        next();
      } else {                                   // sin x, sin 2x, sqrt 9
        let a = unary();
        while (startsPrimary() && !isFnTok(toks[p])) a = "(" + a + "*" + unary() + ")";
        args = [a];
      }
      if (args.length !== need) throw new Error(name + "() needs " + need + " argument" + (need > 1 ? "s" : ""));
      return "$f." + name + "(" + args.join(",") + ")";
    }
    throw new Error('Unexpected "' + k.v + '"');
  }

  const src = expr();
  if (p < toks.length) throw new Error('Unexpected "' + toks[p].v + '"');
  return { src: src, used: used };
}

function splitRel(s) {            // split at = < > <= >= outside brackets
  let depth = 0, cur = ""; const parts = [], ops = [];
  for (const ch of s) {
    if (ch === "(") depth++; else if (ch === ")") depth--;
    if (depth === 0 && "=<>≤≥".includes(ch)) { parts.push(cur); ops.push(ch); cur = ""; } else cur += ch;
  }
  parts.push(cur);
  return { parts: parts, ops: ops };
}

// Returns {kind:'explicit'|'implicit'|'ineq', fn(x,y), op?} or {empty:true}; throws on errors.
function compileCurve(text) {
  const s = normalize(text);
  if (!s.trim()) return { empty: true };
  const sp = splitRel(s);
  if (sp.ops.length > 1) throw new Error("Only one = or inequality sign is allowed");
  const polar = u => u.has("r") || u.has("theta");
  const mk = (src, pol) => new Function("x", "y",
    (pol ? "const r=Math.hypot(x,y),th=Math.atan2(y,x)/K;" : "") + "return " + src);
  const A = compileExpr(sp.parts[0]);
  if (sp.ops.length === 0) {
    const pol = polar(A.used);
    return (A.used.has("y") || pol) ? { kind: "implicit", fn: mk(A.src, pol) } : { kind: "explicit", fn: mk(A.src, false) };
  }
  if (!sp.parts[1].trim()) throw new Error("Nothing on the right of " + sp.ops[0]);
  const B = compileExpr(sp.parts[1]), op = sp.ops[0];
  const pol = polar(A.used) || polar(B.used);
  if (op === "=") {
    if (A.src === "y" && !B.used.has("y") && !pol) return { kind: "explicit", fn: mk(B.src, false) };
    return { kind: "implicit", fn: mk("(" + A.src + ")-(" + B.src + ")", pol) };
  }
  return { kind: "ineq", op: op, fn: mk("(" + A.src + ")-(" + B.src + ")", pol) };
}
// ==== PARSER END

// ==== GRAPH ENGINE
const COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2"];
const MAXSIZE = 700;
const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
const cv = document.getElementById("c"), ctx = cv.getContext("2d");
const wrap = document.getElementById("wrap"), plotcol = document.getElementById("plotcol");
const base = document.createElement("canvas"), bctx = base.getContext("2d");
let g = ctx, W = 0, Hh = 0, dpr = 1;
let s = 60, ox = 0, oy = 0;          // s = pixels per unit (same for x and y); (ox, oy) = pixel of the origin
let touched = false, mouse = null, drag = null, down = null, dirty = true, lastSize = 0;
let curves = [], pins = [], nextColor = 0, showKP = true, nextId = 1, area = null, tangent = null;

function reset() { s = W / 12; ox = W / 2; oy = Hh / 2; }
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
  g.beginPath(); g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}

function gridLines(step, color, width) {
  g.strokeStyle = color; g.lineWidth = width; g.beginPath();
  const k0 = Math.ceil((0 - ox) / s / step), k1 = Math.floor((W - ox) / s / step);
  for (let k = k0; k <= k1; k++) { const px = Math.round(ox + k * step * s) + 0.5; g.moveTo(px, 0); g.lineTo(px, Hh); }
  const j0 = Math.ceil((oy - Hh) / s / step), j1 = Math.floor(oy / s / step);
  for (let j = j0; j <= j1; j++) { const py = Math.round(oy - j * step * s) + 0.5; g.moveTo(0, py); g.lineTo(W, py); }
  g.stroke();
}

function drawGridAndAxes() {
  const major = niceStep(90 / s), minor = major / 5;
  gridLines(minor, "#d7ecdc", 0.7);
  gridLines(major, "#8cc79b", 1.2);
  g.strokeStyle = "#1b1b1b"; g.lineWidth = 2; g.beginPath();
  if (oy >= 0 && oy <= Hh) { g.moveTo(0, oy); g.lineTo(W, oy); }
  if (ox >= 0 && ox <= W) { g.moveTo(ox, 0); g.lineTo(ox, Hh); }
  g.stroke();

  const axY = clamp(oy, 0, Hh), axX = clamp(ox, 0, W);
  const below = axY < Hh - 22, leftSide = axX > 46, tf = "11px " + FONT;
  const k0 = Math.ceil((0 - ox) / s / major), k1 = Math.floor((W - ox) / s / major);
  for (let k = k0; k <= k1; k++) {
    if (k === 0) continue;
    haloText(fmtTick(k * major, major), ox + k * major * s, below ? axY + 5 : axY - 5, "#222", tf, "center", below ? "top" : "bottom");
  }
  const j0 = Math.ceil((oy - Hh) / s / major), j1 = Math.floor(oy / s / major);
  for (let j = j0; j <= j1; j++) {
    if (j === 0) continue;
    haloText(fmtTick(j * major, major), leftSide ? axX - 6 : axX + 6, oy - j * major * s, "#222", tf, leftSide ? "right" : "left", "middle");
  }
  haloText("0", leftSide ? axX - 6 : axX + 6, below ? axY + 5 : axY - 5, "#222", tf, leftSide ? "right" : "left", below ? "top" : "bottom");
  const nf = "italic bold 15px " + FONT;
  if (oy >= 16 && oy <= Hh - 16) haloText("x", W - 8, oy - 6, "#222", nf, "right", "bottom");
  if (ox >= 16 && ox <= W - 16) haloText("y", ox + 8, 8, "#222", nf, "left", "top");
}

// Inequalities: tint the region where the inequality holds.
function drawShade(c) {
  const o = c.obj, cs = 4, gt = (o.op === ">" || o.op === "≥"), orEq = (o.op === "≤" || o.op === "≥");
  g.save(); g.globalAlpha = 0.18; g.fillStyle = c.color;
  for (let j = 0; j < Hh; j += cs) {
    const y = (oy - (j + cs / 2)) / s; let run = -1;
    for (let i = 0; i <= W; i += cs) {
      let ok = false;
      if (i < W) { const v = o.fn((i + cs / 2 - ox) / s, y); ok = gt ? v > 0 : v < 0; if (v === 0 && orEq) ok = true; }
      if (ok && run < 0) run = i;
      else if (!ok && run >= 0) { g.fillRect(run, j, i - run, cs); run = -1; }
    }
  }
  g.restore();
}

// y = f(x): sample every half pixel, lift the pen at asymptotes.
function drawExplicit(c) {
  const f = c.obj.fn;
  g.save(); g.beginPath(); g.rect(0, 0, W, Hh); g.clip();
  g.strokeStyle = c.color; g.lineWidth = 2.6; g.lineJoin = "round"; g.lineCap = "round";
  g.beginPath();
  let pen = false, prev = 0;
  for (let px = 0; px <= W; px += 0.5) {
    const v = f((px - ox) / s, 0);
    if (!isFinite(v)) { pen = false; continue; }
    let py = oy - v * s;
    if (py > 1e5) py = 1e5; else if (py < -1e5) py = -1e5;
    if (pen && Math.abs(py - prev) > Hh * 2) pen = false;
    if (pen) g.lineTo(px, py); else g.moveTo(px, py);
    pen = true; prev = py;
  }
  g.stroke(); g.restore();
}

// Implicit curves F(x, y) = 0 by marching squares.
function drawContour(fn, color, dashed) {
  const cs = 3, nx = Math.ceil(W / cs), ny = Math.ceil(Hh / cs), stride = nx + 1;
  const val = new Float64Array(stride * (ny + 1));
  for (let j = 0; j <= ny; j++) {
    const y = (oy - j * cs) / s;
    for (let i = 0; i <= nx; i++) { const v = fn((i * cs - ox) / s, y); val[j * stride + i] = isFinite(v) ? v : NaN; }
  }
  g.save(); g.beginPath(); g.rect(0, 0, W, Hh); g.clip();
  g.strokeStyle = color; g.lineWidth = 2.6; g.lineCap = "round"; g.lineJoin = "round";
  if (dashed) g.setLineDash([9, 6]);
  g.beginPath();
  const seg = (a, b) => { g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); };
  for (let j = 0; j < ny; j++) {
    for (let i = 0; i < nx; i++) {
      const tl = val[j * stride + i], tr = val[j * stride + i + 1];
      const bl = val[(j + 1) * stride + i], br = val[(j + 1) * stride + i + 1];
      if (!(tl === tl && tr === tr && bl === bl && br === br)) continue;
      const code = (tl > 0 ? 8 : 0) | (tr > 0 ? 4 : 0) | (br > 0 ? 2 : 0) | (bl > 0 ? 1 : 0);
      if (code === 0 || code === 15) continue;
      const x0 = i * cs, y0 = j * cs;
      const T = () => [x0 + cs * tl / (tl - tr), y0], R = () => [x0 + cs, y0 + cs * tr / (tr - br)];
      const B = () => [x0 + cs * bl / (bl - br), y0 + cs], L = () => [x0, y0 + cs * tl / (tl - bl)];
      switch (code) {
        case 1: case 14: seg(L(), B()); break;
        case 2: case 13: seg(B(), R()); break;
        case 3: case 12: seg(L(), R()); break;
        case 4: case 11: seg(T(), R()); break;
        case 6: case 9: seg(T(), B()); break;
        case 7: case 8: seg(L(), T()); break;
        case 5: if ((tl + tr + br + bl) > 0) { seg(L(), T()); seg(B(), R()); } else { seg(T(), R()); seg(L(), B()); } break;
        case 10: if ((tl + tr + br + bl) > 0) { seg(T(), R()); seg(L(), B()); } else { seg(L(), T()); seg(B(), R()); } break;
      }
    }
  }
  g.stroke(); g.restore();
}

// ---- roots, intercepts and intersections
function roots1D(fn, lo, hi, N) {
  const out = []; let px = lo, pv = fn(lo);
  for (let i = 1; i <= N; i++) {
    const xx = lo + (hi - lo) * i / N, v = fn(xx);
    if (isFinite(pv) && isFinite(v)) {
      if (v === 0) out.push(xx);
      else if (pv !== 0 && (pv < 0) !== (v < 0)) {
        let a = px, b = xx, fa = pv;
        for (let k = 0; k < 60; k++) {
          const m = (a + b) / 2, fm = fn(m);
          if (!isFinite(fm)) break;
          if ((fm < 0) === (fa < 0)) { a = m; fa = fm; } else b = m;
        }
        const m = (a + b) / 2, fm = fn(m);
        if (isFinite(fm) && Math.abs(fm) < 1e-6) out.push(m);   // rejects jumps across asymptotes
      }
    }
    px = xx; pv = v;
  }
  return out;
}

function keyPoints() {
  const pts = [], xl = -ox / s, xr = (W - ox) / s, yb = (oy - Hh) / s, yt = oy / s;
  const add = (x, y, color) => {
    if (pts.length >= 40 || !isFinite(x) || !isFinite(y)) return;
    const px = ox + x * s, py = oy - y * s;
    if (px < -4 || px > W + 4 || py < -4 || py > Hh + 4) return;
    for (const p of pts) if (Math.hypot(p.px - px, p.py - py) < 6) return;
    pts.push({ x: x, y: y, px: px, py: py, color: color });
  };
  const vis = curves.filter(c => c.visible && c.obj && (c.obj.kind === "explicit" || c.obj.kind === "implicit"));
  for (const c of vis) {
    const f = c.obj.fn;
    if (c.obj.kind === "explicit") {
      roots1D(x => f(x, 0), xl, xr, 600).forEach(r => add(r, 0, c.color));
      if (xl <= 0 && xr >= 0) add(0, f(0, 0), c.color);
    } else {
      roots1D(x => f(x, 0), xl, xr, 600).forEach(r => add(r, 0, c.color));
      roots1D(y => f(0, y), yb, yt, 600).forEach(r => add(0, r, c.color));
    }
  }
  const ex = vis.filter(c => c.obj.kind === "explicit");
  for (let i = 0; i < ex.length; i++) for (let j = i + 1; j < ex.length; j++) {
    const fi = ex[i].obj.fn, fj = ex[j].obj.fn;
    roots1D(x => fi(x, 0) - fj(x, 0), xl, xr, 600).forEach(r => add(r, fi(r, 0), "#222"));
  }
  return pts;
}

function drawKeyPoints(pts) {
  for (const p of pts) {
    g.beginPath(); g.arc(p.px, p.py, 4.5, 0, Math.PI * 2);
    g.fillStyle = "#fff"; g.fill(); g.lineWidth = 2; g.strokeStyle = p.color; g.stroke();
    const right = p.px > W - 100;
    haloText("(" + fmtVal(p.x) + ", " + fmtVal(p.y) + ")", right ? p.px - 7 : p.px + 7, p.py - 7,
      "#333", "11px " + FONT, right ? "right" : "left", "bottom");
  }
}

function renderBase() {
  g = bctx; bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.fillStyle = "#fbfff9"; g.fillRect(0, 0, W, Hh);
  for (const c of curves) if (c.visible && c.obj && c.obj.kind === "ineq") drawShade(c);
  drawGridAndAxes();
  drawArea();
  for (const c of curves) {
    if (!c.visible || !c.obj || !c.obj.kind) continue;
    if (c.obj.kind === "explicit") drawExplicit(c);
    else if (c.obj.kind === "implicit") drawContour(c.obj.fn, c.color, false);
    else drawContour(c.obj.fn, c.color, c.obj.op === "<" || c.obj.op === ">");
  }
  drawTangent();
  if (showKP) drawKeyPoints(keyPoints());
  g = ctx;
}

// ==== CURSOR, PINS, EVENTS
// Nearest point on any visible curve to the mouse (explicit: same x; implicit: Newton projection).
function snapPoint(mx, my) {
  let best = null;
  for (const c of curves) {
    if (!c.visible || !c.obj || !c.obj.kind) continue;
    const f = c.obj.fn; let cand = null;
    if (c.obj.kind === "explicit") {
      const x = (mx - ox) / s, v = f(x, 0);
      if (isFinite(v)) { const py = oy - v * s; cand = { x: x, y: v, px: mx, py: py, d: Math.abs(py - my) }; }
    } else {
      let x = (mx - ox) / s, y = (oy - my) / s; const h = 0.5 / s;
      const grad = (a, b) => [(f(a + h, b) - f(a - h, b)) / (2 * h), (f(a, b + h) - f(a, b - h)) / (2 * h)];
      let ok = true;
      for (let it = 0; it < 14; it++) {
        const v = f(x, y), gr = grad(x, y), g2 = gr[0] * gr[0] + gr[1] * gr[1];
        if (!isFinite(v) || !(g2 > 0) || !isFinite(g2)) { ok = false; break; }
        x -= v * gr[0] / g2; y -= v * gr[1] / g2;
      }
      if (ok) {
        const v = f(x, y), gr = grad(x, y), gn = Math.hypot(gr[0], gr[1]);
        if (isFinite(v) && gn > 0 && Math.abs(v) / gn * s < 0.4) {
          const px = ox + x * s, py = oy - y * s;
          cand = { x: x, y: y, px: px, py: py, d: Math.hypot(px - mx, py - my) };
        }
      }
    }
    if (cand && cand.d <= 30 && (!best || cand.d < best.d)) { cand.color = c.color; best = cand; }
  }
  return best;
}

function infoBox(text, y, color) {
  g.font = "bold 13px " + FONT;
  const w = Math.min(g.measureText(text).width + 34, W - 20);
  g.fillStyle = "rgba(255,255,255,0.9)"; rr(10, y, w, 26, 8); g.fill();
  g.strokeStyle = "rgba(0,0,0,0.15)"; g.lineWidth = 1; g.stroke();
  g.beginPath(); g.arc(23, y + 13, 5, 0, Math.PI * 2); g.fillStyle = color || "#999"; g.fill();
  g.fillStyle = "#222"; g.textAlign = "left"; g.textBaseline = "middle";
  g.fillText(text, 34, y + 13, Math.max(20, w - 44));
}

function drawOverlay() {
  for (const p of pins) {                                   // pinned points
    const px = ox + p.x * s, py = oy - p.y * s;
    if (px < -20 || px > W + 20 || py < -20 || py > Hh + 20) continue;
    g.beginPath(); g.arc(px, py, 5, 0, Math.PI * 2);
    g.fillStyle = p.color; g.fill(); g.lineWidth = 2; g.strokeStyle = "#fff"; g.stroke();
    const right = px > W - 110;
    haloText("(" + fmtVal(p.x) + ", " + fmtVal(p.y) + ")", right ? px - 8 : px + 8, py - 8,
      "#111", "bold 12px " + FONT, right ? "right" : "left", "bottom");
  }
  if (!mouse) return;
  const p = snapPoint(mouse.x, mouse.y);
  if (!p) { infoBox("x = " + fmtVal((mouse.x - ox) / s) + "   y = " + fmtVal((oy - mouse.y) / s), 10, "#999"); return; }
  infoBox("x = " + fmtVal(p.x) + "   y = " + fmtVal(p.y), 10, p.color);
  const axY = clamp(oy, 0, Hh), axX = clamp(ox, 0, W), blue = "#3a3a3a";   // dark grey cursor guides and axis values
  g.save(); g.setLineDash([5, 4]); g.strokeStyle = blue; g.lineWidth = 1.4; g.beginPath();
  g.moveTo(p.px, p.py); g.lineTo(p.px, axY); g.moveTo(p.px, p.py); g.lineTo(axX, p.py); g.stroke(); g.restore();
  g.beginPath(); g.arc(p.px, p.py, 5.5, 0, Math.PI * 2);
  g.fillStyle = p.color; g.fill(); g.lineWidth = 2; g.strokeStyle = "#fff"; g.stroke();
  const below = axY < Hh - 28, leftSide = axX > 80;
  haloText(fmtVal(p.x), p.px, below ? axY + 8 : axY - 8, blue, "bold 13px " + FONT, "center", below ? "top" : "bottom");
  haloText(fmtVal(p.y), leftSide ? axX - 8 : axX + 8, p.py, blue, "bold 13px " + FONT, leftSide ? "right" : "left", "middle");
}

function draw() {
  if (dirty) { renderBase(); dirty = false; }
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, cv.width, cv.height);
  ctx.drawImage(base, 0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); g = ctx;
  drawOverlay();
}
function redraw() { dirty = true; draw(); }

function resize() {
  dpr = window.devicePixelRatio || 1;
  const size = Math.max(260, Math.min(MAXSIZE, plotcol.clientWidth - 4));
  if (size === lastSize && W) return;
  lastSize = size;
  wrap.style.width = size + "px"; wrap.style.height = size + "px";
  W = Hh = wrap.clientWidth;
  cv.style.width = W + "px"; cv.style.height = Hh + "px";
  cv.width = base.width = Math.round(W * dpr); cv.height = base.height = Math.round(Hh * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!touched) reset();
  redraw();
}

cv.addEventListener("wheel", e => {
  e.preventDefault(); touched = true;
  const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  let k = Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015));
  const ns = clamp(s * k, 1e-8, 1e8); k = ns / s;
  ox = mx - (mx - ox) * k; oy = my - (my - oy) * k; s = ns;     // keep the point under the mouse fixed
  mouse = { x: mx, y: my }; redraw();
}, { passive: false });
cv.addEventListener("pointerdown", e => {
  cv.setPointerCapture(e.pointerId);
  drag = { x: e.clientX, y: e.clientY }; down = { x: e.clientX, y: e.clientY, moved: false };
});
cv.addEventListener("pointermove", e => {
  const r = cv.getBoundingClientRect();
  mouse = { x: e.clientX - r.left, y: e.clientY - r.top };
  if (drag) {
    if (!down.moved && Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4) { down.moved = true; cv.style.cursor = "grabbing"; }
    if (down.moved) { touched = true; ox += e.clientX - drag.x; oy += e.clientY - drag.y; dirty = true; }
    drag = { x: e.clientX, y: e.clientY };
  }
  draw();
});
function endDrag(e) {
  if (down && !down.moved && e && e.type === "pointerup" && mouse) {      // a click pins the nearest curve point
    const p = snapPoint(mouse.x, mouse.y);
    if (p && pins.length < 30) pins.push({ x: p.x, y: p.y, color: p.color });
  }
  drag = null; down = null; cv.style.cursor = "crosshair"; draw();
}
cv.addEventListener("pointerup", endDrag);
cv.addEventListener("pointercancel", endDrag);
cv.addEventListener("pointerleave", () => { if (!drag) { mouse = null; draw(); } });

// ==== EQUATION ROWS
const rowsEl = document.getElementById("rows"), calcIn = document.getElementById("calcIn");
const calcOut = document.getElementById("calcOut"), histEl = document.getElementById("hist");
let lastFocus = calcIn;

function recompile(c) {
  try { c.obj = compileCurve(c.text); c.err = ""; } catch (e) { c.obj = null; c.err = e.message; }
}
function addCurve(text) {
  const c = { id: nextId++, text: text, color: COLORS[nextColor++ % COLORS.length], visible: true, obj: null, err: "" };
  recompile(c); curves.push(c); return c;
}
function paintDot(dot, c) { dot.style.borderColor = c.color; dot.style.background = c.visible ? c.color : "transparent"; }
function buildRows() {
  rowsEl.innerHTML = "";
  curves.forEach((c, i) => {
    const row = document.createElement("div"); row.className = "row";
    const dot = document.createElement("button"); dot.className = "dot"; dot.title = "Show / hide"; paintDot(dot, c);
    dot.onclick = () => { c.visible = !c.visible; paintDot(dot, c); redraw(); };
    const inp = document.createElement("input");
    inp.value = c.derived ? c.label() : c.text; inp.disabled = !!c.derived; c.inpEl = inp; inp.placeholder = "y = x^2,  x^2+y^2=9,  y > x ..."; inp.spellcheck = false; inp.autocomplete = "off";
    inp.addEventListener("focus", () => { lastFocus = inp; });
    inp.addEventListener("input", () => { c.text = inp.value; recompile(c); c.errEl.textContent = c.err; c.errEl.style.display = c.err ? "" : "none"; refreshCalcUI(); redraw(); });
    const del = document.createElement("button"); del.className = "del"; del.textContent = "✕"; del.title = "Remove";
    del.onclick = () => { removeCurve(c); if (lastFocus === inp) lastFocus = calcIn; buildRows(); redraw(); };
    row.append(dot, inp, del); rowsEl.append(row);
    const er = document.createElement("div"); er.className = "err"; er.textContent = c.err; er.style.display = c.err ? "" : "none";
    c.errEl = er; rowsEl.append(er);
  });
  refreshCalcUI();
}
document.getElementById("addRow").onclick = () => {
  addCurve(""); buildRows(); redraw();
  const inputs = rowsEl.querySelectorAll("input"); inputs[inputs.length - 1].focus();
};
document.getElementById("clearPins").onclick = () => { pins = []; draw(); };
document.getElementById("reset").onclick = () => { touched = false; reset(); redraw(); };
document.getElementById("kp").onchange = e => { showKP = e.target.checked; redraw(); };
document.querySelectorAll("#modeSeg button").forEach(b => b.onclick = () => {
  K = b.dataset.m === "deg" ? Math.PI / 180 : 1;
  document.querySelectorAll("#modeSeg button").forEach(x => x.classList.toggle("on", x === b));
  redraw();
});

// ==== CALCULATOR
function fmtResult(v) {
  if (v === Infinity) return "∞"; if (v === -Infinity) return "−∞";
  if (v === 0) return "0";
  const n = parseFloat(v.toPrecision(12)), a = Math.abs(n);
  if (a >= 1e12 || a < 1e-9) return n.toExponential().replace("e+", "×10^").replace("e-", "×10^-");
  return String(n);
}
function runCalc() {
  const str = calcIn.value.trim(); if (!str) return;
  try {
    const r = compileExpr(str);
    if (r.used.size) throw new Error("This uses x / y / θ – type it in a graph row instead");
    const v = new Function("return " + r.src)();
    if (typeof v !== "number" || isNaN(v)) throw new Error("Undefined");
    ANS = v; calcOut.className = ""; calcOut.textContent = fmtResult(v);
    histList.unshift({ s: str, v: v }); if (histList.length > 8) histList.pop();
    histEl.innerHTML = "";
    histList.forEach(h => {
      const d = document.createElement("div"); d.textContent = h.s + " = " + fmtResult(h.v);
      d.onclick = () => { calcIn.value = h.s; calcIn.focus(); }; histEl.append(d);
    });
  } catch (e) { calcOut.className = "bad"; calcOut.textContent = e.message; }
}
const histList = [];
calcIn.addEventListener("focus", () => { lastFocus = calcIn; });
calcIn.addEventListener("keydown", e => { if (e.key === "Enter") runCalc(); });

function insertText(t) {
  const el = lastFocus || calcIn; el.focus();
  const a = el.selectionStart, b = el.selectionEnd;
  el.value = el.value.slice(0, a) + t + el.value.slice(b);
  el.setSelectionRange(a + t.length, a + t.length);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}
function editKey(kind) {
  const el = lastFocus || calcIn; el.focus();
  if (kind === "clear") el.value = "";
  else { let a = el.selectionStart; const b = el.selectionEnd;
    if (a === b && a > 0) a--; el.value = el.value.slice(0, a) + el.value.slice(b); el.setSelectionRange(a, a); }
  el.dispatchEvent(new Event("input", { bubbles: true }));
}
const PAD = [
  ["sin", "sin(", ""], ["cos", "cos(", ""], ["tan", "tan(", ""], ["ln", "ln(", ""], ["log", "log(", ""], ["AC", "clear", "clr"],
  ["sin⁻¹", "asin(", ""], ["cos⁻¹", "acos(", ""], ["tan⁻¹", "atan(", ""], ["eˣ", "e^(", ""], ["10ˣ", "10^(", ""], ["⌫", "back", "clr"],
  ["x", "x", ""], ["y", "y", ""], ["(", "(", ""], [")", ")", ""], ["^", "^", ""], ["θ", "theta", ""],
  ["7", "7", "num"], ["8", "8", "num"], ["9", "9", "num"], ["÷", "/", ""], ["x²", "^2", ""], ["|x|", "abs(", ""],
  ["4", "4", "num"], ["5", "5", "num"], ["6", "6", "num"], ["×", "*", ""], ["√", "sqrt(", ""], ["n!", "!", ""],
  ["1", "1", "num"], ["2", "2", "num"], ["3", "3", "num"], ["−", "-", ""], ["π", "pi", ""], ["e", "e", ""],
  ["0", "0", "num"], [".", ".", "num"], [",", ",", ""], ["+", "+", ""], ["Ans", "ans", ""], ["⏎", "enter", "act"],
  ["=", "=", ""], ["<", "<", ""], [">", ">", ""], ["≤", "≤", ""], ["≥", "≥", ""], ["°", "°", ""]
];
const padEl = document.getElementById("pad");
PAD.forEach(([label, val, cls]) => {
  const b = document.createElement("button"); b.textContent = label; if (cls) b.className = cls;
  b.addEventListener("mousedown", e => e.preventDefault());       // keep focus in the input
  b.onclick = () => { if (val === "enter") runCalc(); else if (val === "clear" || val === "back") editKey(val); else insertText(val); };
  padEl.append(b);
});

// ==== CALCULUS
const cFn = document.getElementById("cFn"), cOut = document.getElementById("cOut");
const x0In = document.getElementById("x0"), iaIn = document.getElementById("ia"), ibIn = document.getElementById("ib");
[x0In, iaIn, ibIn].forEach(el => el.addEventListener("focus", () => { lastFocus = el; }));

const fnOf = c => (c && c.obj && c.obj.kind === "explicit") ? (x => c.obj.fn(x, 0)) : null;
const srcName = c => c.derived ? c.label() : c.text.trim();
function say(msg, bad) { cOut.textContent = msg; cOut.className = bad ? "bad" : ""; }
function fmtD(v) {                                   // derivative / integral output: 8 significant digits
  if (!isFinite(v)) return fmtResult(v);
  if (Math.abs(v) < 1e-7) return "0";
  return fmtResult(parseFloat(v.toPrecision(8)));
}
// 5-point stencils (error ~h^4)
function d1(f, x) { const h = 1e-3 * Math.max(1, Math.abs(x)); return (8 * (f(x + h) - f(x - h)) - (f(x + 2 * h) - f(x - 2 * h))) / (12 * h); }
function d2(f, x) { const h = 1e-2 * Math.max(1, Math.abs(x)); return (-f(x + 2 * h) + 16 * f(x + h) - 30 * f(x) + 16 * f(x - h) - f(x - 2 * h)) / (12 * h * h); }
function simpsonN(f, a, b, n) {
  if (n % 2) n++;
  const h = (b - a) / n; let t = f(a) + f(b);
  for (let i = 1; i < n; i++) t += f(a + i * h) * (i % 2 ? 4 : 2);
  return t * h / 3;
}
function integrate(f, a, b) {                        // adaptive Simpson on 16 panels
  if (a === b) return 0;
  let sign = 1; if (a > b) { const t = a; a = b; b = t; sign = -1; }
  const rec = (a, b, fa, fm, fb, whole, eps, d) => {
    const m = (a + b) / 2, flm = f((a + m) / 2), frm = f((m + b) / 2);
    const left = (m - a) / 6 * (fa + 4 * flm + fm), right = (b - m) / 6 * (fm + 4 * frm + fb), delta = left + right - whole;
    if (!isFinite(delta)) return NaN;
    if (d <= 0 || Math.abs(delta) <= 15 * eps) return left + right + delta / 15;
    return rec(a, m, fa, flm, fm, left, eps / 2, d - 1) + rec(m, b, fm, frm, fb, right, eps / 2, d - 1);
  };
  let total = 0; const P = 16, w = (b - a) / P;
  for (let i = 0; i < P; i++) {
    const lo = a + i * w, hi = i === P - 1 ? b : lo + w, mid = (lo + hi) / 2;
    const fa = f(lo), fm = f(mid), fb = f(hi);
    if (!isFinite(fa + fm + fb)) return NaN;
    total += rec(lo, hi, fa, fm, fb, (hi - lo) / 6 * (fa + 4 * fm + fb), 1e-10 / P, 18);
  }
  return sign * total;
}
function evalNum(str) {
  const r = compileExpr(str);
  if (r.used.size) throw new Error("use a plain number (pi, 2*pi/3 ... are fine)");
  const v = new Function("return " + r.src)();
  if (typeof v !== "number" || !isFinite(v)) throw new Error("not a finite number");
  return v;
}

function selCurve() { const id = +cFn.value; return curves.find(c => c.id === id && fnOf(c)); }
function refreshCalcUI() {
  curves.forEach(c => { if (c.derived && c.inpEl) c.inpEl.value = c.label(); });
  const prev = cFn.value; cFn.innerHTML = "";
  curves.filter(c => fnOf(c)).forEach(c => {
    const o = document.createElement("option"); o.value = c.id; o.textContent = srcName(c); cFn.append(o);
  });
  if (!cFn.options.length) {
    const o = document.createElement("option"); o.textContent = "(add a function such as y = sin(x))"; o.disabled = true; cFn.append(o);
  } else if ([...cFn.options].some(o => o.value === prev)) cFn.value = prev;
}
function removeCurve(c) {
  const gone = new Set([c]); let again = true;
  while (again) { again = false; curves.forEach(d => { if (d.derived && gone.has(d.src) && !gone.has(d)) { gone.add(d); again = true; } }); }
  curves = curves.filter(d => !gone.has(d));
  if (area && gone.has(area.c)) area = null;
  if (tangent && gone.has(tangent.c)) tangent = null;
}

function addDerived(kind) {
  const src = selCurve();
  if (!src) return say("Pick a function y = f(x) first.", true);
  let a = 0;
  if (kind === "int") { try { a = evalNum(iaIn.value); } catch (e) { return say("Lower limit a: " + e.message, true); } }
  const get = () => fnOf(src); let fn, label;
  if (kind === "d1") { fn = x => { const f = get(); return f ? d1(f, x) : NaN; }; label = () => "d/dx [" + srcName(src) + "]"; }
  else if (kind === "d2") { fn = x => { const f = get(); return f ? d2(f, x) : NaN; }; label = () => "d²/dx² [" + srcName(src) + "]"; }
  else {
    fn = x => {
      const f = get(); if (!f) return NaN; if (x === a) return 0;
      return simpsonN(f, a, x, 2 * Math.ceil(clamp(Math.abs(x - a) * s / 6, 4, 60)));
    };
    label = () => "∫ from " + fmtVal(a) + " [" + srcName(src) + "] dx";
  }
  curves.push({ id: nextId++, text: "", label: label, derived: true, src: src, color: COLORS[nextColor++ % COLORS.length],
    visible: true, obj: { kind: "explicit", fn: x => fn(x) }, err: "" });
  buildRows(); cFn.value = String(src.id); redraw();
  say(kind === "int" ? "Plotted the antiderivative F(x) = ∫ from " + fmtVal(a) + " to x. Change a first to shift it."
                     : "Plotted the " + (kind === "d1" ? "first" : "second") + " derivative. Its roots are the " +
                       (kind === "d1" ? "turning points of f" : "inflection candidates of f") + " (see the marked points).");
}

function doTangent() {
  const c = selCurve(); if (!c) return say("Pick a function y = f(x) first.", true);
  let x0; try { x0 = evalNum(x0In.value); } catch (e) { return say("x₀: " + e.message, true); }
  const f = fnOf(c), y0 = f(x0), m = d1(f, x0);
  if (!isFinite(y0) || !isFinite(m)) return say("f is not defined or not differentiable at x₀.", true);
  const b = y0 - m * x0; tangent = { c: c, x0: x0 };
  say("f(x₀)  = " + fmtD(y0) + "\nf′(x₀) = " + fmtD(m) + "\nf″(x₀) = " + fmtD(d2(f, x0)) +
      "\ntangent: y = " + fmtD(m) + "·x " + (b < 0 ? "− " : "+ ") + fmtD(Math.abs(b)));
  redraw();
}
function doDefinite() {
  const c = selCurve(); if (!c) return say("Pick a function y = f(x) first.", true);
  let a, b; try { a = evalNum(iaIn.value); } catch (e) { return say("a: " + e.message, true); }
  try { b = evalNum(ibIn.value); } catch (e) { return say("b: " + e.message, true); }
  const f = fnOf(c), val = integrate(f, a, b);
  const abs = simpsonN(x => Math.abs(f(x)), Math.min(a, b), Math.max(a, b), 4000);
  if (!isFinite(val)) return say("The integral is undefined or diverges on [a, b].", true);
  area = { c: c, a: a, b: b };
  say("∫ from " + fmtD(a) + " to " + fmtD(b) + " of f dx = " + fmtD(val) +
      "\nArea between curve and x-axis = " + (isFinite(abs) ? fmtD(abs) : "n/a"));
  redraw();
}
document.getElementById("bD1").onclick = () => addDerived("d1");
document.getElementById("bD2").onclick = () => addDerived("d2");
document.getElementById("bInt").onclick = () => addDerived("int");
document.getElementById("bTan").onclick = doTangent;
document.getElementById("bDef").onclick = doDefinite;
document.getElementById("cClear").onclick = () => { tangent = null; area = null; say(""); redraw(); };

function drawArea() {                                // shaded region between f and the x-axis on [a, b]
  if (!area || !area.c.visible) return;
  const f = fnOf(area.c); if (!f) return;
  const lo = Math.min(area.a, area.b), hi = Math.max(area.a, area.b);
  const p0 = ox + lo * s, p1 = ox + hi * s;
  g.save(); g.beginPath(); g.rect(0, 0, W, Hh); g.clip();
  g.globalAlpha = 0.28; g.fillStyle = area.c.color; g.beginPath();
  let run = false, last = 0;
  for (let px = Math.max(0, Math.floor(p0)); px <= Math.min(W, Math.ceil(p1)) + 1; px++) {
    const v = f(clamp((px - ox) / s, lo, hi));
    if (!isFinite(v) || px > Math.ceil(p1) + 0.5) { if (run) { g.lineTo(last, oy); g.closePath(); run = false; } continue; }
    const py = clamp(oy - v * s, -1e5, 1e5);
    if (!run) { g.moveTo(px, oy); run = true; }
    g.lineTo(px, py); last = px;
  }
  if (run) { g.lineTo(last, oy); g.closePath(); }
  g.fill(); g.globalAlpha = 1;
  g.setLineDash([5, 4]); g.strokeStyle = area.c.color; g.lineWidth = 1.4; g.beginPath();
  g.moveTo(p0, 0); g.lineTo(p0, Hh); g.moveTo(p1, 0); g.lineTo(p1, Hh); g.stroke();
  g.restore();
}
function drawTangent() {
  if (!tangent || !tangent.c.visible) return;
  const f = fnOf(tangent.c); if (!f) return;
  const x0 = tangent.x0, y0 = f(x0), m = d1(f, x0);
  if (!isFinite(y0) || !isFinite(m)) return;
  g.save(); g.beginPath(); g.rect(0, 0, W, Hh); g.clip();
  g.strokeStyle = "#111"; g.lineWidth = 1.8; g.setLineDash([8, 5]); g.beginPath();
  g.moveTo(0, oy - (y0 + m * (-ox / s - x0)) * s); g.lineTo(W, oy - (y0 + m * ((W - ox) / s - x0)) * s); g.stroke();
  g.setLineDash([]); g.beginPath(); g.arc(ox + x0 * s, oy - y0 * s, 5, 0, Math.PI * 2);
  g.fillStyle = "#fff"; g.fill(); g.lineWidth = 2.2; g.stroke(); g.restore();
  haloText("slope " + fmtD(m), ox + x0 * s + 9, oy - y0 * s + 9, "#111", "bold 12px " + FONT, "left", "top");
}

// ==== START
addCurve("y = sin(x)"); addCurve("x^2 + y^2 = 9"); addCurve("y = x^2 / 4 - 2");
buildRows();
if (window.ResizeObserver) new ResizeObserver(resize).observe(plotcol);
window.addEventListener("resize", resize);
resize();
</script>
</body></html>
"""

st.set_page_config(page_title="Graphing calculator", page_icon="🧮", layout="wide")
st.markdown("<style>.block-container{padding-top:1.5rem;}</style>", unsafe_allow_html=True)
st.title("Scientific graphing calculator")
components.html(HTML, height=950, scrolling=True)
