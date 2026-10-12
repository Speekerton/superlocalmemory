// od-polish.js: presentation helpers. No product logic, no API calls.
//
//   - labels each table cell with its column name so tables can reflow into
//     stacked cards on narrow screens (CSS in theme-slm.css);
//   - adds the mascot to empty states that are rendered by other panes;
//   - places a small mascot at the bottom of the sidebar.
(function () {
  'use strict';

  function labelTables(root) {
    (root || document).querySelectorAll('table.tbl, table.table').forEach(function (t) {
      var heads = [];
      var hr = t.tHead && t.tHead.rows[0];
      if (!hr) return;
      for (var i = 0; i < hr.cells.length; i++) heads.push((hr.cells[i].textContent || '').trim());
      t.classList.add('slm-stack');
      for (var b = 0; b < t.tBodies.length; b++) {
        var rows = t.tBodies[b].rows;
        for (var r = 0; r < rows.length; r++) {
          var cells = rows[r].cells;
          if (cells.length === 1 && cells[0].colSpan > 1) continue;
          for (var c = 0; c < cells.length; c++) {
            if (!cells[c].hasAttribute('data-label') && heads[c]) cells[c].setAttribute('data-label', heads[c]);
          }
        }
      }
    });
  }

  var EMPTY = [
    ['No peers connected', 'peek'],
    ['No sessions connected right now', 'peek'],
    ['No mesh activity recorded', 'peek'],
    ['No multi-agent memory yet', 'laptop'],
    ['No skill lineage yet', 'pointing'],
    ['No skill performance data yet', 'pointing'],
    ['No memories found', 'magnifier'],
    ['No stored memory matched', 'magnifier'],
    ['No messages from this peer yet', 'peek']
  ];

  function decorateEmpty(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll('.tab-pane div, .tab-pane p, .tab-pane h3, .tab-pane h4, .tab-pane li');
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.children.length > 2 || n.hasAttribute('data-mascot') || n.closest('[data-mascot]')) continue;
      var txt = (n.textContent || '').trim();
      if (txt.length > 400) continue;
      for (var k = 0; k < EMPTY.length; k++) {
        if (txt.indexOf(EMPTY[k][0]) !== 0) continue;
        // an inner element carries the same message: decorate that one instead
        var pat = EMPTY[k][0];
        if (Array.prototype.some.call(n.children, function (c) { return (c.textContent || '').trim().indexOf(pat) === 0; })) break;
        var host = n;
        // lift to the block that holds the whole empty message
        if (host.tagName !== 'DIV' || host.children.length === 0) host = n.parentNode && n.parentNode.children.length <= 3 ? n.parentNode : n;
        if (host.hasAttribute('data-mascot') || host.querySelector('[data-mascot]') || host.querySelector('img.slm-empty-mascot')) break;
        host.setAttribute('data-mascot', EMPTY[k][1]);
        host.classList.add('slm-empty-host');
        var img = document.createElement('img');
        img.className = 'slm-empty-mascot-top';
        img.src = '/static/assets/mascot/' + EMPTY[k][1] + '-320.webp';
        img.alt = ''; img.width = 88; img.height = 88; img.loading = 'lazy';
        host.insertBefore(img, host.firstChild);
        break;
      }
    }
  }

  // A tab count that has not loaded yet reads "…": hide it until it has a number.
  function tidyCounts() {
    document.querySelectorAll('.tab .cnt').forEach(function (c) {
      var pending = (c.textContent || '').trim() === '\u2026';
      if (pending !== c.hasAttribute('hidden')) { if (pending) c.setAttribute('hidden', ''); else c.removeAttribute('hidden'); }
    });
  }

  function sidebarMascot() {
    var foot = document.getElementById('od-sidebar-foot');
    if (!foot || document.querySelector('.sidebar-mascot')) return;
    var img = document.createElement('img');
    img.className = 'sidebar-mascot';
    img.src = '/static/assets/mascot/hero-320.webp';
    img.alt = ''; img.width = 64; img.height = 64; img.loading = 'lazy';
    foot.parentNode.insertBefore(img, foot);
  }

  var pending = false;
  function run() { pending = false; labelTables(); decorateEmpty(); sidebarMascot(); tidyCounts(); }
  function schedule() { if (!pending) { pending = true; setTimeout(run, 150); } }
  function start() {
    run();
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
  }
  window.SLMPolish = { labelTables: labelTables };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(start, 80); });
  else setTimeout(start, 80);
}());
