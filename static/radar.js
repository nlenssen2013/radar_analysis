(function () {
  const dom = {
    source: document.getElementById('sourceSelect'),
    prefix: document.getElementById('prefixSelect'),
    search: document.getElementById('searchSelect'),
    sort: document.getElementById('sortSelect'),
    refresh: document.getElementById('refreshBtn'),
    list: document.getElementById('radarList'),
    title: document.getElementById('selectedTitle'),
    meta: document.getElementById('selectedMeta'),
    updated: document.getElementById('selectedUpdated'),
    images: document.getElementById('images'),
    status: document.getElementById('status'),
  };

  const state = {
    source: dom.source.value,
    radars: [],
    selectedId: null,
    sortBy: dom.sort.value,
    prefixLocation: '',
    searchSelection: '',
  };

  function setStatus(message, isError = false) {
    if (!message) {
      dom.status.classList.add('hidden');
      dom.status.textContent = '';
      dom.status.classList.remove('error');
      return;
    }
    dom.status.textContent = message;
    dom.status.classList.remove('hidden');
    dom.status.classList.toggle('error', isError);
  }

  function formatTilt(tilt) {
    if (typeof tilt === 'number' && !Number.isNaN(tilt)) {
      return `${tilt.toFixed(1)}° tilt`;
    }
    return 'Tilt';
  }

  function toUtcText(timestamp) {
    if (!timestamp) {
      return null;
    }
    const ts = timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`;
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return `${date.toUTCString()}`;
  }

  function clearImages() {
    dom.images.innerHTML = '';
  }

  function populateSelect(select, options, preferredValue) {
    const currentValue = select.value;
    const desiredValue =
      preferredValue !== undefined && preferredValue !== null
        ? preferredValue
        : currentValue;

    select.innerHTML = '';
    options.forEach((option) => {
      const opt = document.createElement('option');
      opt.value = option.value;
      opt.textContent = option.label;
      if (option.value === desiredValue) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    if (!options.some((opt) => opt.value === desiredValue)) {
      select.value = options.length ? options[0].value : '';
    } else {
      select.value = desiredValue;
    }
  }

  function getLocationText(radar) {
    const city = (radar.city || '').trim();
    const stateCode = (radar.state || '').trim();
    if (city && stateCode) {
      return `${city}, ${stateCode}`;
    }
    if (city) {
      return city;
    }
    if (stateCode) {
      return stateCode;
    }
    return radar.location || 'Unknown location';
  }

  function buildLocationLabel(radar) {
    const location = getLocationText(radar);
    return `${location} — ${radar.radar_id}`;
  }

  function updateSelectors() {
    const uniqueLocations = new Set();
    state.radars.forEach((radar) => {
      uniqueLocations.add(getLocationText(radar));
    });

    const locationOptions = Array.from(uniqueLocations).sort((a, b) =>
      a.localeCompare(b)
    );

    const prefixOptions = [{ value: '', label: 'All locations' }];
    locationOptions.forEach((location) => {
      prefixOptions.push({ value: location, label: location });
    });
    populateSelect(dom.prefix, prefixOptions, state.prefixLocation);
    state.prefixLocation = dom.prefix.value;

    const searchOptions = [{ value: '', label: 'Select a radar…' }];
    const sortedRadars = state.radars.slice().sort((a, b) => {
      const labelA = buildLocationLabel(a);
      const labelB = buildLocationLabel(b);
      return labelA.localeCompare(labelB);
    });
    sortedRadars.forEach((radar) => {
      searchOptions.push({ value: radar.radar_id, label: buildLocationLabel(radar) });
    });
    populateSelect(dom.search, searchOptions, state.searchSelection);
    state.searchSelection = dom.search.value;
  }

  async function loadImage(img, key, view) {
    if (!key) {
      return;
    }
    const params = new URLSearchParams({
      source: state.source,
      key,
      view,
    });
    try {
      const response = await fetch(`/api/file?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      img.src = url;
      img.dataset.url = url;
      const metadataHeader = response.headers.get('X-Radar-Metadata');
      if (metadataHeader && view === 'zoom') {
        try {
          const metadata = JSON.parse(metadataHeader);
          if (metadata.title) {
            img.setAttribute('alt', metadata.title);
          }
        } catch (error) {
          console.debug('Unable to parse radar metadata header', error);
        }
      }
    } catch (error) {
      console.error(error);
      setStatus(`Failed to load radar image: ${error.message}`, true);
    }
  }

  function renderImages(radar) {
    clearImages();
    if (!radar || !Array.isArray(radar.products)) {
      return;
    }
    radar.products.forEach((product) => {
      const card = document.createElement('div');
      card.className = 'tilt-card';

      const heading = document.createElement('h3');
      const tiltLabel = formatTilt(product.tilt_degrees);
      heading.textContent = `${product.code} — ${tiltLabel}`;
      card.appendChild(heading);

      const stamp = toUtcText(product.timestamp);
      if (stamp) {
        const stampEl = document.createElement('div');
        stampEl.className = 'meta';
        stampEl.textContent = `Scan time: ${stamp}`;
        card.appendChild(stampEl);
      }

      const pair = document.createElement('div');
      pair.className = 'view-pair';

      ['overview', 'zoom'].forEach((view) => {
        const container = document.createElement('div');
        container.className = 'view';
        const title = document.createElement('div');
        title.className = 'view-title';
        title.textContent = view === 'overview' ? 'State overview' : 'Local zoom';
        const img = document.createElement('img');
        img.alt = `${product.code} ${view}`;
        img.loading = 'lazy';
        container.appendChild(title);
        container.appendChild(img);
        pair.appendChild(container);
        loadImage(img, product.key, view);
      });

      card.appendChild(pair);
      dom.images.appendChild(card);
    });
  }

  function updateSelection(radar) {
    if (!radar) {
      dom.title.textContent = 'Select a radar';
      dom.meta.textContent = '';
      dom.updated.style.display = 'none';
      clearImages();
      return;
    }

    const location = getLocationText(radar);
    dom.title.textContent = `${radar.radar_id}${location ? ' — ' + location : ''}`;

    const pieces = [];
    if (radar.product_name) {
      pieces.push(radar.product_name);
    }
    if (radar.elevation_degrees != null) {
      pieces.push(`${radar.elevation_degrees.toFixed(1)}° tilt`);
    }
    dom.meta.textContent = pieces.join(' • ');

    const updatedText = toUtcText(radar.product_time || radar.volume_time);
    if (updatedText) {
      dom.updated.textContent = `Updated ${updatedText}`;
      dom.updated.style.display = 'inline-flex';
    } else {
      dom.updated.style.display = 'none';
    }

    renderImages(radar);
  }

  function setActiveListItem() {
    const items = dom.list.querySelectorAll('li');
    items.forEach((li) => {
      li.classList.toggle('active', li.dataset.radarId === state.selectedId);
    });
  }

  function handleSelect(radarId) {
    state.selectedId = radarId;
    const radar = state.radars.find((item) => item.radar_id === radarId);
    setActiveListItem();
    updateSelection(radar);
  }

  function filteredRadars() {
    return state.radars.filter((radar) => {
      if (state.prefixLocation) {
        const location = getLocationText(radar);
        if (location !== state.prefixLocation) {
          return false;
        }
      }
      return true;
    });
  }

  function renderList() {
    const items = filteredRadars();

    dom.list.innerHTML = '';

    if (!items.length) {
      const placeholder = document.createElement('li');
      placeholder.textContent = 'No radar sites match the current filters.';
      placeholder.style.cursor = 'default';
      placeholder.style.color = '#64748b';
      dom.list.appendChild(placeholder);
      updateSelection(null);
      return;
    }

    items.forEach((radar) => {
      const li = document.createElement('li');
      li.dataset.radarId = radar.radar_id;

      const code = document.createElement('span');
      code.className = 'radar-code';
      code.textContent = radar.radar_id;
      li.appendChild(code);

      const location = document.createElement('span');
      location.className = 'radar-location';
      location.textContent = getLocationText(radar);
      li.appendChild(location);

      li.addEventListener('click', () => handleSelect(radar.radar_id));
      dom.list.appendChild(li);
    });

    if (!state.selectedId || !items.some((item) => item.radar_id === state.selectedId)) {
      state.selectedId = items[0].radar_id;
    }

    setActiveListItem();
    const selectedRadar = state.radars.find((item) => item.radar_id === state.selectedId);
    updateSelection(selectedRadar || null);
  }

  function sortRadars() {
    const sortBy = state.sortBy;
    state.radars.sort((a, b) => {
      if (sortBy === 'radar') {
        return a.radar_id.localeCompare(b.radar_id);
      }
      const nameA = getLocationText(a).toUpperCase();
      const nameB = getLocationText(b).toUpperCase();
      if (nameA && nameB) {
        return nameA.localeCompare(nameB);
      }
      if (nameA) return -1;
      if (nameB) return 1;
      return a.radar_id.localeCompare(b.radar_id);
    });
  }

  async function loadRadars(options = {}) {
    const { attemptedFallback = false } = options;

    const requestedSource = state.source;

    setStatus('Fetching latest radar scans…');
    clearImages();
    dom.title.textContent = 'Select a radar';
    dom.meta.textContent = '';
    dom.updated.style.display = 'none';

    const params = new URLSearchParams({
      source: state.source,
      include_metadata: 'true',
      limit: '200',
    });

    try {
      const response = await fetch(`/api/base_reflectivity/latest?${params.toString()}`);
      if (!response.ok) {
        if (response.status >= 500 && state.source !== 'local' && !attemptedFallback) {
          setStatus('Remote source failed. Switching to local cache…', true);
          state.source = 'local';
          dom.source.value = 'local';
          return loadRadars({ attemptedFallback: true });
        }
        throw new Error(`Server responded with ${response.status}`);
      }
      const payload = await response.json();
      const radars = Array.isArray(payload.radars) ? payload.radars : [];
      state.radars = radars;

      let fallbackMessage = '';
      if (payload.source && payload.source !== state.source) {
        state.source = payload.source;
        dom.source.value = payload.source;
        fallbackMessage = ` Remote source ${requestedSource.toUpperCase()} unavailable; showing ${payload.source.toUpperCase()} data.`;
      }

      sortRadars();
      updateSelectors();
      renderList();
      if (radars.length) {
        setStatus(
          `Loaded ${radars.length} radar site${radars.length === 1 ? '' : 's'} from ${state.source.toUpperCase()}.${fallbackMessage}`
        );
      } else {
        setStatus(
          'No radar data available. Try running scripts/ingest_last_hour.py and refresh.',
          true
        );
      }
    } catch (error) {
      console.error(error);
      if (!attemptedFallback && state.source !== 'local') {
        state.source = 'local';
        dom.source.value = 'local';
        setStatus('Falling back to local cache…', true);
        return loadRadars({ attemptedFallback: true });
      }
      setStatus(
        `Unable to fetch radar list: ${error.message}. Ensure the ingest script has run or try another source.`,
        true
      );
      state.radars = [];
      dom.list.innerHTML = '';
    }
  }

  function wireEvents() {
    dom.refresh.addEventListener('click', () => {
      state.selectedId = null;
      loadRadars();
    });

    dom.source.addEventListener('change', () => {
      state.source = dom.source.value;
      state.selectedId = null;
      state.prefixLocation = '';
      state.searchSelection = '';
      loadRadars();
    });

    dom.sort.addEventListener('change', () => {
      state.sortBy = dom.sort.value;
      sortRadars();
      renderList();
    });

    dom.prefix.addEventListener('change', () => {
      state.prefixLocation = dom.prefix.value;
      renderList();
    });

    dom.search.addEventListener('change', () => {
      state.searchSelection = dom.search.value;
      if (state.searchSelection) {
        handleSelect(state.searchSelection);
      }
    });
  }

  function init() {
    wireEvents();
    loadRadars();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
