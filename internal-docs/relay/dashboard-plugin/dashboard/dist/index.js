(function () {
  'use strict';
  const sdk = window.__HERMES_PLUGIN_SDK__;
  const React = sdk.React, h = React.createElement;
  function Agents() {
    const [data, setData] = React.useState(null);
    const [failed, setFailed] = React.useState(false);
    React.useEffect(function () {
      let cancelled = false, timer;
      async function update() {
        try {
          const next = await sdk.fetchJSON('/api/plugins/naquuuu-activity/activity');
          if (!cancelled) { setData(next); setFailed(false); }
        } catch (_) { if (!cancelled) setFailed(true); }
        if (!cancelled) timer = setTimeout(update, 10000);
      }
      update();
      return function () { cancelled = true; clearTimeout(timer); };
    }, []);
    const tasks = data && data.tasks || {};
    return h('section', {className: 'nq-activity', 'aria-labelledby': 'nq-title'},
      h('header', {className: 'nq-heading'},
        h('div', null, h('p', {className: 'nq-eyebrow'}, 'OpenCode workspace'),
          h('h1', {id: 'nq-title'}, 'Agent activity'),
          h('p', {className: 'nq-intro'}, 'Who is working and what needs attention.')),
        h('span', {className: 'nq-fresh', role: 'status'}, failed ? 'Connection lost' : !data ? 'Loading' : data.fresh ? 'Recent activity' : 'No recent activity')),
      h('div', {className: 'nq-summary'},
        ...[['Queued', tasks.pending || 0], ['In progress', tasks.in_progress || 0], ['Completed', tasks.completed || 0]].map(([label, n]) =>
          h('div', {key: label}, h('span', null, label), h('strong', null, n)))),
      data && !data.available ? h('p', {className: 'nq-empty'}, 'No OpenCode session recorded on this host yet.') : null,
      h('div', {className: 'nq-grid'}, ...(data && data.agents || []).map(a =>
        h('article', {className: 'nq-card', key: a.name, 'data-status': a.status},
          h('div', {className: 'nq-card-head'}, h('h2', null, a.name), h('span', {className: 'nq-state'}, a.status)),
          h('p', null, a.description),
          h('dl', {className: 'nq-counts'}, ...[['Tasks', a.tasks], ['Tools', a.tools], ['Files', a.files], ['Errors', a.errors]].map(([label,n]) =>
            h('div', {key: label}, h('dt', null, label), h('dd', null, n))))))),
      h('p', {className: 'nq-note'}, 'This view tracks OpenCode work. Hermes conversations stay in Sessions.'));
  }
  window.__HERMES_PLUGINS__.register('naquuuu-activity', Agents);
})();
