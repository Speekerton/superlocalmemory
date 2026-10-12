// One Memory health place: automatic improvement, safe repair, and undo.
(function () {
  'use strict';
  var timer = null;
  var mounted = null;
  var generation = 0;
  var requestNumber = 0;
  var activeRead = false;
  var mutationBusy = false;

  function el(tag, text) {
    var node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function call(method, payload) {
    var fetcher = window.slmFetch || window.fetch;
    return fetcher((method === 'POST' ? '/api/memory-health/action' : '/api/memory-health'), {
      method: method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: payload ? JSON.stringify(payload) : undefined
    }).then(function (r) {
      if (!r.ok) throw new Error('Memory health is temporarily unavailable.');
      return r.json();
    });
  }
  function button(parent, label, action) {
    var node = el('button', label);
    node.className = 'btn secondary';
    node.disabled = mutationBusy;
    node.addEventListener('click', function () {
      if (mutationBusy) return;
      mutationBusy = true;
      requestNumber += 1;
      node.disabled = true;
      call('POST', action).then(refresh).catch(function (error) {
        var message = el('p', error.message);
        message.setAttribute('role', 'alert');
        parent.appendChild(message);
      }).finally(function () { mutationBusy = false; refresh(); });
    });
    parent.appendChild(node);
  }
  function render(data) {
    if (!mounted || !mounted.isConnected) return;
    mounted.replaceChildren();
    var run = data.enrichment || {};
    var status = run.status || 'waiting_for_idle';
    mounted.appendChild(el('p', 'Improving your memories: ' + (run.processed || 0) +
                           ' of ' + (run.total || 0)));
    var words = {
      completed: 'Your memories have been checked. They will be checked again while idle.',
      paused: 'Improvements are paused. Your memories still work.',
      undone: 'These improvements were undone. Your memories still work.',
      waiting_for_idle: 'Improvements continue when you are not using your memories.',
      running: 'Descriptions are being improved automatically in the background.',
      queued: 'Improvements will start when you are not using your memories.'
    };
    mounted.appendChild(el('p', words[status] || 'Your memories still work.'));
    if (run.last_error) {
      mounted.appendChild(el('p', 'Some improvements are waiting: ' + run.last_error));
    }
    if (run.run_id && status === 'paused') {
      button(mounted, 'Resume', { action: 'resume', run_id: run.run_id });
    } else if (run.run_id && (status === 'queued' || status === 'running')) {
      button(mounted, 'Pause', { action: 'pause', run_id: run.run_id });
    }
    var repairs = data.repairs || [];
    var names = { 'entity-links': 'entity links', 'qjl-sketches': 'search sketches',
                  'refile-hidden': 'hidden memories' };
    repairs.forEach(function (repair) {
      mounted.appendChild(el('p', 'Found ' + repair.found + ' ' +
                             (names[repair.action] || 'issues') + '; fixed ' +
                             repair.fixed + ' automatically.'));
      if (repair.status !== 'undone' && repair.found > repair.fixed) {
        button(mounted, 'Fix ' + (repair.found - repair.fixed) + ' ' +
               (names[repair.action] || 'issues'), { action: 'repair', repair: repair.action });
      }
      if (repair.error) mounted.appendChild(el('p', repair.error));
    });
    var lastRepair = repairs.find(function (repair) {
      return repair.fixed > 0 && repair.status !== 'undone';
    });
    var newerRepair = lastRepair && (!run.changed ||
      Date.parse(lastRepair.created_at) > Date.parse(run.updated_at));
    var undoRun = newerRepair ? lastRepair.run_id :
      (status !== 'undone' && run.changed > 0 ? run.run_id : null);
    if (undoRun) button(mounted, 'Undo last improvement', { action: 'undo', run_id: undoRun });
  }
  function refresh() {
    if (!mounted || !mounted.isConnected || activeRead || mutationBusy) return;
    var target = mounted;
    var mountGeneration = generation;
    var sequence = ++requestNumber;
    activeRead = true;
    return call('GET').then(function (data) {
      if (generation === mountGeneration && requestNumber === sequence && mounted === target) {
        render(data);
      }
    }).catch(function (error) {
      if (generation === mountGeneration && requestNumber === sequence && mounted === target) {
        target.replaceChildren(el('p', error.message));
      }
    }).finally(function () {
      if (generation === mountGeneration) activeRead = false;
    });
  }
  window.odMountMemoryHealth = function (parent) {
    clearInterval(timer);
    generation += 1;
    activeRead = false;
    // One card: the automatic improvements and repairs (refreshed below) and
    // the upgrade store check (od-store-check.js renders into #store-check).
    var card = el('section');
    card.className = 'ng-glass';
    card.id = 'memory-health-card';
    card.style.padding = '20px';
    card.appendChild(el('h3', 'Memory health'));
    mounted = el('div');
    mounted.setAttribute('aria-live', 'polite');
    card.appendChild(mounted);
    var store = el('div');
    store.id = 'store-check';
    store.style.marginTop = '12px';
    card.appendChild(store);
    parent.prepend(card);
    if (window.odStoreCheck) window.odStoreCheck.init();
    refresh();
    timer = setInterval(function () {
      if (!mounted || !mounted.isConnected) {
        clearInterval(timer);
        return;
      }
      refresh();
    }, 5000);
  };
}());
