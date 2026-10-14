/* Small behaviours for the server-rendered portal: theme toggle, chart
 * tooltips, LGA cards, and the quiet 60-second refresh of live pages. */
(function () {
  'use strict';

  var fmt = function (n) { return Number(n || 0).toLocaleString(); };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  // ---- Theme -------------------------------------------------------------
  document.addEventListener('click', function (e) {
    if (!e.target.closest('[data-theme-toggle]')) return;
    var dark = !document.documentElement.classList.contains('dark');
    document.documentElement.classList.toggle('dark', dark);
    try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (err) { /* private mode */ }
  });

  // ---- Tooltips (charts and map) ----------------------------------------
  var tip = document.getElementById('chart-tip');
  function tipHtml(d) {
    var head = '<div class="flex items-center justify-between gap-3"><p class="font-semibold text-slate-900 dark:text-white">' + esc(d.name) + '</p>' +
      (d.winner ? '<span class="rounded-full bg-gold-100 px-2 py-0.5 text-[10px] font-semibold text-brand-800 dark:bg-gold-400/20 dark:text-gold-200">' + esc(d.winner) + ' won</span>' : '') + '</div>';
    if (!d.total) return head + '<p class="mt-1 text-slate-400">No results yet</p>';
    var rows = (d.rows || []).map(function (r) {
      return '<div class="flex items-center justify-between gap-4"><span class="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">' +
        '<span class="inline-block size-2.5 rounded-full" style="background-color:' + esc(r.color) + '"></span>' +
        '<span class="' + (d.winner === r.abbr ? 'font-semibold text-slate-900 dark:text-white' : '') + '">' + esc(r.abbr) + '</span></span>' +
        '<span class="tabular-nums text-slate-700 dark:text-slate-200">' + fmt(r.votes) + '<span class="ml-1 text-slate-400">(' + Number(r.pct || 0).toFixed(1) + '%)</span></span></div>';
    }).join('');
    var foot = (d.rows || []).length > 1 ? '<div class="mt-2 flex items-center justify-between border-t border-slate-200 pt-1.5 text-slate-500 dark:border-white/10 dark:text-slate-400"><span>Total</span><span class="font-semibold tabular-nums text-slate-900 dark:text-white">' + fmt(d.total) + '</span></div>' : '';
    return head + '<div class="mt-2 space-y-1">' + rows + '</div>' + foot;
  }
  var tipFor = null;
  document.addEventListener('mousemove', function (e) {
    if (!tip) return;
    var el = e.target.closest && e.target.closest('[data-tip]');
    if (!el) {
      if (tipFor) { tip.classList.add('hidden'); dimMap(null); tipFor = null; }
      return;
    }
    if (el !== tipFor) {
      tipFor = el;
      try { tip.innerHTML = tipHtml(JSON.parse(el.getAttribute('data-tip'))); } catch (err) { return; }
      tip.classList.remove('hidden');
      dimMap(el.hasAttribute('data-map-shape') ? el : null);
    }
    var x = e.clientX + 16, y = e.clientY + 16, w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > window.innerWidth - 8) x = e.clientX - w - 16;
    if (y + h > window.innerHeight - 8) y = e.clientY - h - 16;
    tip.style.left = Math.max(8, x) + 'px';
    tip.style.top = Math.max(8, y) + 'px';
  });
  function dimMap(active) {
    document.querySelectorAll('[data-map-shape]').forEach(function (p) {
      p.style.opacity = active && p !== active ? '0.5' : '1';
      p.setAttribute('stroke-width', p === active ? '3' : '1.25');
    });
  }

  // Hovering a legend entry highlights that party's series
  document.addEventListener('mouseover', function (e) {
    var leg = e.target.closest && e.target.closest('[data-legend]');
    document.querySelectorAll('[data-series]').forEach(function (s) {
      s.style.opacity = leg && s.getAttribute('data-series') !== leg.getAttribute('data-legend') ? '0.25' : '';
    });
  });

  // ---- Toggle groups (LGA cards -> detail panel) --------------------------
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-toggle-group]');
    var close = e.target.closest('[data-close-group]');
    var group = btn ? btn.getAttribute('data-toggle-group') : close ? close.getAttribute('data-close-group') : null;
    if (!group) return;
    var target = btn ? btn.getAttribute('data-target') : null;
    var wasOpen = btn && btn.getAttribute('aria-pressed') === 'true';
    document.querySelectorAll('[data-toggle-group="' + group + '"]').forEach(function (b) {
      var on = !wasOpen && b === btn;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      var panel = document.getElementById(b.getAttribute('data-target'));
      if (panel) panel.hidden = !on;
    });
    if (btn && !wasOpen && target) {
      var p = document.getElementById(target);
      if (p) p.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });

  // ---- Live refresh -------------------------------------------------------
  // Pages marked data-refresh="N" re-fetch themselves every N seconds and swap
  // their [data-live] regions, keeping open panels and <details> as they were.
  var root = document.querySelector('[data-refresh]');
  if (root && window.fetch && window.DOMParser) {
    var every = parseInt(root.getAttribute('data-refresh'), 10) * 1000;
    setInterval(function () {
      if (document.hidden) return;
      fetch(window.location.href, { credentials: 'same-origin', headers: { 'X-Requested-With': 'refresh' } })
        .then(function (r) { return r.ok ? r.text() : null; })
        .then(function (html) {
          if (!html) return;
          var doc = new DOMParser().parseFromString(html, 'text/html');
          var pressed = Array.prototype.map.call(document.querySelectorAll('[aria-pressed="true"][data-target]'), function (b) { return b.getAttribute('data-target'); });
          var open = Array.prototype.map.call(document.querySelectorAll('details[open][data-keep-open]'), function (d) { return d.getAttribute('data-keep-open'); });
          document.querySelectorAll('[data-live]').forEach(function (el) {
            var fresh = doc.querySelector('[data-live="' + el.getAttribute('data-live') + '"]');
            if (fresh) el.replaceWith(fresh);
          });
          pressed.forEach(function (id) {
            var b = document.querySelector('[data-target="' + id + '"]');
            var p = document.getElementById(id);
            if (b && p) { b.setAttribute('aria-pressed', 'true'); p.hidden = false; }
          });
          open.forEach(function (k) {
            var d = document.querySelector('details[data-keep-open="' + k + '"]');
            if (d) d.open = true;
          });
          if (tip) tip.classList.add('hidden');
          tipFor = null;
        })
        .catch(function () { /* keep showing the last numbers */ });
    }, every);
  }
})();

/* Dashboard sidebar on small screens */
(function () {
  'use strict';
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-sidebar]');
    if (!t) return;
    var open = t.getAttribute('data-sidebar') === 'open';
    var bar = document.getElementById('sidebar');
    var back = document.getElementById('sidebar-backdrop');
    if (bar) bar.toggleAttribute('data-open', open);
    if (back) back.classList.toggle('hidden', !open);
  });
})();

/* Forms: selects that navigate on change, and the running ballot total */
(function () {
  'use strict';
  document.addEventListener('change', function (e) {
    var form = e.target.closest('form[data-autosubmit]');
    if (!form || e.target.tagName !== 'SELECT') return;
    // Picking a new LGA or ward starts the lower levels afresh.
    (e.target.getAttribute('data-resets') || '').split(' ').forEach(function (name) {
      var el = name && form.elements[name];
      if (el) el.disabled = true;
    });
    form.submit();
  });
  document.addEventListener('input', function (e) {
    var form = e.target.closest('form[data-votes]');
    if (!form) return;
    var total = 0;
    form.querySelectorAll('[data-vote]').forEach(function (i) {
      var v = parseInt(i.value, 10);
      if (v > 0) total += v;
    });
    var out = form.querySelector('[data-vote-total]');
    if (out) out.textContent = total.toLocaleString();
  });
})();

/* Clerk LGA pickers: select all / clear and the live "N selected" count */
(function () {
  'use strict';
  function count(form) {
    var n = form.querySelectorAll('input[name="lga_ids"]:checked').length;
    var out = form.querySelector('[data-lga-count]');
    if (out) out.textContent = n + (n === 1 ? ' LGA' : ' LGAs');
  }
  document.querySelectorAll('form[data-lga-picker]').forEach(count);
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-check-all]');
    if (!b) return;
    var form = b.closest('form');
    form.querySelectorAll('input[name="lga_ids"]').forEach(function (i) { i.checked = b.getAttribute('data-check-all') === '1'; });
    count(form);
  });
  document.addEventListener('change', function (e) {
    var form = e.target.closest('form[data-lga-picker]');
    if (form) count(form);
  });
})();
