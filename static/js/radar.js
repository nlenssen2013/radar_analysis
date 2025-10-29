(() => {
  const state = {
    currentSource: 's3',
    currentKey: null,
    threshold: 23,
    overlayEnabled: true,
    map: null,
    overlay: null,
    lastObjectUrl: null,
  };

  const sourceSelect = document.getElementById('sourceSelect');
  const prefixInput = document.getElementById('prefixInput');
  const limitInput = document.getElementById('limitInput');
  const thresholdSlider = document.getElementById('thresholdSlider');
  const thresholdInput = document.getElementById('thresholdInput');
  const listBtn = document.getElementById('listBtn');
  const fileList = document.getElementById('fileList');
  const overlayToggle = document.getElementById('overlayToggle');
  const radarImage = document.getElementById('radarImage');
  const mapContainer = document.getElementById('map');
  const quickTestBtn = document.getElementById('quickTest');
  const statusBar = document.getElementById('status');

  function showStatus(message, isError = false) {
    if (!message) {
      statusBar.classList.add('hidden');
      statusBar.textContent = '';
      return;
    }
    statusBar.textContent = message;
    statusBar.classList.toggle('hidden', false);
    statusBar.style.background = isError ? '#fee2e2' : '#fff7ed';
    statusBar.style.borderTopColor = isError ? '#fecaca' : '#fcd9bd';
    statusBar.style.color = isError ? '#991b1b' : '#9a3412';
  }

  function revokeObjectUrl() {
    if (state.lastObjectUrl) {
      URL.revokeObjectURL(state.lastObjectUrl);
      state.lastObjectUrl = null;
    }
  }

  function clearActiveListItem() {
    fileList.querySelectorAll('li').forEach((li) => li.classList.remove('active'));
  }

  function setActiveListItem(key) {
    clearActiveListItem();
    const match = Array.from(fileList.querySelectorAll('li')).find((li) => li.dataset.key === key);
    if (match) {
      match.classList.add('active');
      match.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  function ensureMap() {
    if (!state.map) {
      state.map = L.map(mapContainer).setView([27.6648, -81.5158], 6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(state.map);
    }
    return state.map;
  }

  function setDisplayMode(boundsAvailable) {
    const shouldShowMap = state.overlayEnabled && boundsAvailable;
    mapContainer.classList.toggle('hidden', !shouldShowMap);
    radarImage.classList.toggle('hidden', shouldShowMap);
    if (shouldShowMap) {
      ensureMap();
      setTimeout(() => state.map && state.map.invalidateSize(), 50);
    }
  }

  function renderOverlay(imageUrl, bounds) {
    const map = ensureMap();
    if (state.overlay) {
      state.overlay.remove();
      state.overlay = null;
    }

    if (!bounds) {
      setDisplayMode(false);
      radarImage.src = imageUrl;
      radarImage.alt = 'Radar product';
      return;
    }

    const leafletBounds = [
      [bounds.min_lat, bounds.min_lon],
      [bounds.max_lat, bounds.max_lon],
    ];

    state.overlay = L.imageOverlay(imageUrl, leafletBounds, { opacity: 0.85 });
    state.overlay.addTo(map);
    map.fitBounds(leafletBounds);
    setDisplayMode(true);
  }

  async function loadImage(key, options = {}) {
    if (!key) {
      return;
    }

    state.currentKey = key;
    if (!options.skipListHighlight) {
      setActiveListItem(key);
    }

    const threshold = Number(thresholdInput.value);
    state.threshold = threshold;

    const params = new URLSearchParams({
      source: state.currentSource,
      key,
    });
    if (!Number.isNaN(threshold)) {
      params.set('threshold', String(threshold));
    }

    showStatus('Fetching radar image…');
    revokeObjectUrl();

    try {
      const response = await fetch(`/api/file?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      const boundsHeader = response.headers.get('X-Radar-Bounds');
      const bounds = boundsHeader ? JSON.parse(boundsHeader) : null;
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      state.lastObjectUrl = objectUrl;
      if (bounds && overlayToggle.checked) {
        renderOverlay(objectUrl, bounds);
      } else {
        setDisplayMode(false);
        radarImage.src = objectUrl;
        radarImage.alt = `Radar product ${key}`;
      }
      showStatus(`Showing ${key}`);
    } catch (error) {
      console.error(error);
      showStatus(`Unable to load image: ${error.message}`, true);
    }
  }

  function buildListItem(key) {
    const li = document.createElement('li');
    li.textContent = key;
    li.dataset.key = key;
    li.addEventListener('click', () => loadImage(key));
    return li;
  }

  async function fetchKeys() {
    const source = sourceSelect.value;
    const prefix = prefixInput.value.trim();
    const limit = Number(limitInput.value) || 20;

    state.currentSource = source;

    const params = new URLSearchParams({ source, limit: String(limit) });
    if (prefix) {
      params.set('prefix', prefix);
    }

    showStatus('Loading file list…');
    fileList.innerHTML = '';

    try {
      const response = await fetch(`/api/files?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      const payload = await response.json();
      const keys = payload.keys || [];
      if (!keys.length) {
        showStatus('No files found for the provided filters.');
        return;
      }
      const fragment = document.createDocumentFragment();
      keys.forEach((key) => fragment.appendChild(buildListItem(key)));
      fileList.appendChild(fragment);
      showStatus(`Loaded ${keys.length} file(s). Click a file to render.`);
    } catch (error) {
      console.error(error);
      showStatus(`Unable to load file list: ${error.message}`, true);
    }
  }

  function syncThreshold(value) {
    thresholdSlider.value = value;
    thresholdInput.value = value;
  }

  function handleThresholdChange(value) {
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
      return;
    }
    syncThreshold(String(numeric));
    state.threshold = numeric;
    if (state.currentKey) {
      loadImage(state.currentKey, { skipListHighlight: true });
    }
  }

  function handleOverlayToggle() {
    state.overlayEnabled = overlayToggle.checked;
    if (!state.overlayEnabled) {
      if (state.overlay) {
        state.overlay.remove();
        state.overlay = null;
      }
      if (state.lastObjectUrl) {
        radarImage.src = state.lastObjectUrl;
        radarImage.classList.remove('hidden');
        mapContainer.classList.add('hidden');
      }
    } else if (state.currentKey) {
      loadImage(state.currentKey, { skipListHighlight: true });
    }
  }

  function runQuickTest() {
    sourceSelect.value = 's3';
    state.currentSource = 's3';
    const quickKey = 'TBW_N0B_2025_06_15_19_01_56';
    prefixInput.value = quickKey;
    syncThreshold('23');
    handleThresholdChange('23');
    loadImage(quickKey, { skipListHighlight: true });
    fileList.innerHTML = '';
    fileList.appendChild(buildListItem(quickKey));
    setActiveListItem(quickKey);
  }

  listBtn.addEventListener('click', fetchKeys);
  thresholdSlider.addEventListener('input', (event) => handleThresholdChange(event.target.value));
  thresholdInput.addEventListener('change', (event) => handleThresholdChange(event.target.value));
  sourceSelect.addEventListener('change', () => {
    state.currentSource = sourceSelect.value;
    state.currentKey = null;
    revokeObjectUrl();
    radarImage.classList.add('hidden');
    mapContainer.classList.add('hidden');
    fileList.innerHTML = '';
    showStatus('Select "Fetch files" to load products for the new source.');
  });
  overlayToggle.addEventListener('change', handleOverlayToggle);
  quickTestBtn.addEventListener('click', runQuickTest);

  // Initialize defaults
  syncThreshold(String(state.threshold));
  showStatus('Set filters then click "Fetch files" to begin.');
})();
