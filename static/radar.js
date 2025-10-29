(function(){
  const qs = (id) => document.getElementById(id);
  const listEl   = qs('list');
  const imgEl    = qs('radar');
  const dbzEl    = qs('dbz');
  const prefixEl = qs('prefix');
  const linkEl   = qs('openLink');
  const msgEl    = qs('msg');

  function msg(s){ msgEl.textContent = s || ""; }

  async function listFiles() {
    try {
      msg("");
      listEl.innerHTML = "Loading...";
      const r = await fetch('/radar_files', {cache:'no-store'});
      if (!r.ok) throw new Error(`HTTP ${r.status} ${r.statusText}`);
      const data = await r.json();
      const pref = (prefixEl.value || '').trim().toUpperCase();
      const all = Array.isArray(data.files) ? data.files : [];
      const filtered = all.filter(f => pref ? f.toUpperCase().includes(pref) : true);
      const header = document.createElement('div');
      header.className = 'small';
      header.textContent = `Total: ${all.length} | Showing: ${filtered.length}`;
      listEl.innerHTML = '';
      listEl.appendChild(header);
      filtered.forEach(k => {
        const a = document.createElement('a');
        a.href = '#';
        a.textContent = k;
        a.style.display = 'block';
        a.onclick = (e) => { e.preventDefault(); showAuto(k); };
        listEl.appendChild(a);
      });
      if (filtered.length === 0) {
        const d = document.createElement('div');
        d.textContent = 'No matching items.';
        listEl.appendChild(d);
      }
    } catch (e) {
      listEl.textContent = 'Failed to list files: ' + e;
    }
  }

  function currentPathFromImg() {
    try {
      const u = new URL(imgEl.dataset.src || '', window.location.origin);
      const p = u.searchParams.get('path');
      return p ? decodeURIComponent(p) : null;
    } catch { return null; }
  }

  async function fetchAsImage(url) {
    const r = await fetch(url, {cache:'no-store'});
    if (!r.ok) {
      const txt = await r.text();
      throw new Error(`HTTP ${r.status} ${r.statusText}\n` + txt.slice(0,400));
    }
    const blob = await r.blob();                 // works even if server says application/json
    const objUrl = URL.createObjectURL(blob);
    imgEl.src = objUrl;
    imgEl.dataset.src = url;                     // remember source URL for re-render on DBZ change
    linkEl.href = url;
    linkEl.style.display = 'inline-block';
  }

  async function showResolved(path, dbz) {
    const url = '/radar_filter_q?path=' + encodeURIComponent(path) + '&threshold=' + dbz;
    await fetchAsImage(url);
    msg("");
  }

  async function showAuto(basePath) {
    msg("");
    imgEl.removeAttribute('src');
    linkEl.style.display = 'none';
    const dbz = parseInt(dbzEl.value || '23', 10);
    const candidates = [basePath];
    if (!/\.nc$/i.test(basePath)) {
      candidates.push(basePath + '.nc');
      if (!/\.mdv\.nc$/i.test(basePath)) candidates.push(basePath + '.mdv.nc');
    }
    let lastErr = null;
    for (const c of candidates) {
      try { await showResolved(c, dbz); return; } catch(e){ lastErr = e; }
    }
    msg('Could not render any candidate:\n' + candidates.join('\n') + '\n\nLast error: ' + lastErr);
  }

  function wire() {
    qs('refresh').onclick = listFiles;
    qs('quick').onclick   = () => showAuto('radar_3_data/KMLB_SDUS52_TZ0MCO_202405151906.nc');
    dbzEl.onchange        = () => { const cur = currentPathFromImg(); if (cur) showAuto(cur); };
    listFiles();
  }

  window.addEventListener('error', (e) => { msg('JS error: ' + e.message); });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }
})();
