/* IGNIS LAB - the trained FLEX models, evaluated in the browser so the 3D chamber reacts instantly.
 * The numbers in window.IGNIS_MODEL_DATA are exported from the saved scikit-learn models by
 * ignis/simulation.py (web_model_payload); tests/test_core.py checks this file reproduces
 * Python's predictions and traffic light exactly. Do not edit the maths without re-running that test.
 *
 * window.IGNIS.predict(q) with q = {fuel: "Heptane"|"Methanol", p_atm, x_o2, x_co2, x_he, d0_mm} returns
 * {p_ext, k, k_half, burn_time_s, light, light_text, reasons, nearest, d_ext_mm, n_ext_runs,
 *  cool_flame_possible, tested_ranges}
 */
(function () {
  "use strict";
  var D = window.IGNIS_MODEL_DATA;
  var NUM = ["p_atm", "x_o2", "x_co2", "x_he", "d0_mm"];

  function inputValue(q, n) {                     // hep_<c> = <c> for Heptane, 0 otherwise (ignis/features.py)
    return n.indexOf("hep_") === 0 ? (q.fuel === "Heptane" ? q[n.slice(4)] : 0) : q[n];
  }

  function features(m, q) {                       // OneHotEncoder(fuel) then StandardScaler(numeric columns)
    var x = m.fuel_categories.map(function (c) { return q.fuel === c ? 1 : 0; });
    m.num.forEach(function (n, i) { x.push((inputValue(q, n) - m.mean[i]) / m.scale[i]); });
    return x;
  }

  function linear(m, q) {
    var x = features(m, q), s = m.intercept;
    for (var i = 0; i < x.length; i++) s += m.coef[i] * x[i];
    return s;
  }

  function fmt(v) { return Number(v).toPrecision(3).replace(/\.?0+$/, ""); }

  function median(a) {
    if (!a.length) return null;
    var s = a.slice().sort(function (x, y) { return x - y; }), h = Math.floor(s.length / 2);
    return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
  }

  function predict(qIn) {
    var q = {
      fuel: qIn.fuel, p_atm: +qIn.p_atm, x_o2: +qIn.x_o2, x_co2: +(qIn.x_co2 || 0),
      x_he: +(qIn.x_he || 0), d0_mm: +qIn.d0_mm
    };
    var ev = D.evidence[q.fuel];
    var pExt = 1 / (1 + Math.exp(-linear(D.clf, q)));
    var k = linear(D.k, q);

    // ---- traffic light: same rules as ignis/evidence.py evidence_lookup()
    var reasons = [];
    NUM.forEach(function (c) {
      var lo = ev.ranges[c][0], hi = ev.ranges[c][1], pad = D.tol * (hi - lo);
      if (!(q[c] >= lo - pad && q[c] <= hi + pad)) {
        reasons.push(c + " = " + fmt(q[c]) + " is outside the tested range " + fmt(lo) + "-" + fmt(hi));
      }
    });
    var z = NUM.map(function (n, i) { return (q[n] - ev.mean[i]) / ev.scale[i]; });
    var ranked = ev.runs.map(function (r) {
      var s = 0;
      for (var i = 0; i < z.length; i++) { var dz = r.z[i] - z[i]; s += dz * dz; }
      return { r: r, d: Math.sqrt(s) };
    }).sort(function (a, b) { return a.d - b.d; });
    var nearest = ranked.slice(0, 5).map(function (o) {
      var r = o.r;
      return { flex_id: r.flex_id, test_end: r.test_end, dext_mm: r.dext_mm, k_mm2_s: r.k_mm2_s,
               p_atm: r.p_atm, x_o2: r.x_o2, x_co2: r.x_co2, x_he: r.x_he, d0_mm: r.d0_mm,
               distance: Math.round(o.d * 100) / 100 };
    });
    var d0 = ranked[0].d, thr = ev.threshold, light, text;
    if (q.x_o2 + q.x_co2 + q.x_he > 1) {
      reasons.push("gas fractions add up to more than 1");
    }
    if (reasons.length) {
      light = "RED"; text = "RED - outside NASA's tested conditions: the model was never validated here";
    } else if (d0 > D.far * thr) {
      light = "RED"; text = "RED - no comparable NASA run: this combination of conditions was never tested";
      reasons.push("nearest run is " + d0.toFixed(2) + " scaled units away; 95% of real runs have a neighbour within " +
                   thr.toFixed(2) + " (each value is inside a tested range, but not together)");
    } else if (d0 > thr) {
      light = "AMBER"; text = "AMBER - inside the tested ranges, but no close NASA run";
      reasons.push("nearest run is " + d0.toFixed(2) + " scaled units away (95% of real runs have a neighbour within " +
                   thr.toFixed(2) + ")");
    } else {
      light = "GREEN"; text = "GREEN - close to real NASA runs";
    }
    var ext = nearest.filter(function (r) { return r.test_end === "Extinction" && r.dext_mm > 0; })
                     .map(function (r) { return r.dext_mm; });
    return {
      p_ext: pExt, k: k, k_half: D.k_half, burn_time_s: k > 0 ? q.d0_mm * q.d0_mm / k : null,
      light: light, light_text: text, reasons: reasons, nearest: nearest,
      d_ext_mm: median(ext), n_ext_runs: ext.length,
      cool_flame_possible: q.fuel === "Heptane" && pExt >= 0.5,
      tested_ranges: ev.ranges
    };
  }

  window.IGNIS = { predict: predict, data: D };
})();
