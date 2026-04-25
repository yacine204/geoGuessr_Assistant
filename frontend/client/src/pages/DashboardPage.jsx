import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet';
import { useAuth } from '../context/AuthContext';
import { analyzeImage } from '../services/analysisService';

const MAX_FILE_MB = 15;
const STORAGE_KEYS = {
  investigations: 'geoseer.investigations.v1',
  activeId: 'geoseer.active-investigation.v1',
  mapTheme: 'geoseer.map-theme.v1',
};

const TILE_LAYERS = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
  },
  light: {
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri',
  },
  terrain: {
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap, SRTM | &copy; OpenTopoMap',
    subdomains: 'abc',
  },
};

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function getTokenSubject(token) {
  if (!token || typeof token !== 'string') {
    return 'anonymous';
  }

  try {
    const [, payload] = token.split('.');
    if (!payload) {
      return 'anonymous';
    }

    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
    const decoded = JSON.parse(atob(padded));
    return decoded.sub || 'anonymous';
  } catch {
    return 'anonymous';
  }
}

function buildStorageKeys(subject) {
  const safeSubject = encodeURIComponent(subject || 'anonymous');

  return {
    investigations: `geoseer.${safeSubject}.investigations.v1`,
    activeId: `geoseer.${safeSubject}.active-investigation.v1`,
    mapTheme: `geoseer.${safeSubject}.map-theme.v1`,
  };
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function dataUrlToFile(dataUrl, fileName) {
  const [meta, base64] = dataUrl.split(',');
  const mimeMatch = meta.match(/data:(.*?);base64/);
  const mime = mimeMatch?.[1] || 'image/jpeg';
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);

  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return new File([bytes], fileName, { type: mime });
}

function randomId() {
  return `${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

function buildItem(file) {
  return {
    id: randomId(),
    fileName: file.name,
    title: file.name.replace(/\.[^.]+$/, '').slice(0, 42) || 'New investigation',
    imageDataUrl: '',
    status: 'uploading',
    uploadProgress: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    guessedCountry: '',
    confidence: null,
    summary: '',
    language: null,
    ocrText: '',
    topCountries: [],
    coordinates: null,
    errorMessage: '',
  };
}

function formatTime(ts) {
  const date = new Date(ts);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function statusLabel(status) {
  if (status === 'uploading') return 'Uploading';
  if (status === 'processing') return 'Analyzing';
  if (status === 'done') return 'Done';
  return 'Error';
}

function confidenceLabel(confidence) {
  if (typeof confidence !== 'number') {
    return 'N/A';
  }

  const normalized = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.round(normalized)}%`;
}

const HISTORY_ICONS = {
  message: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  pencil: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
    </svg>
  ),
  trash: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
    </svg>
  ),
};

function FitBounds({ points }) {
  const map = useMap();

  useEffect(() => {
    if (!points?.length) {
      return;
    }

    if (points.length === 1) {
      map.setView(points[0], 6);
      return;
    }

    map.fitBounds(points, { padding: [28, 28] });
  }, [map, points]);

  return null;
}

function extractCandidateCoordinates(entry) {
  if (!Array.isArray(entry?.raw?.candidates)) {
    return [];
  }

  return entry.raw.candidates
    .map((candidate, index) => {
      const lat = Number(candidate?.lat ?? candidate?.latitude ?? candidate?.coords?.lat);
      const lng = Number(candidate?.lng ?? candidate?.longitude ?? candidate?.coords?.lng);

      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return null;
      }

      return {
        id: `${entry.id}-${index}`,
        point: [lat, lng],
        label: candidate?.country || candidate?.label || `Alternate ${index + 1}`,
      };
    })
    .filter(Boolean)
    .slice(0, 3);
}

function MapView({ entry, mapTheme, onThemeChange }) {
  const primary = entry?.coordinates
    ? [entry.coordinates.lat, entry.coordinates.lng]
    : null;
  const alternates = extractCandidateCoordinates(entry);

  if (!primary) {
    return <p className="gs-note">No coordinates returned by backend for this result.</p>;
  }

  const tile = TILE_LAYERS[mapTheme] || TILE_LAYERS.dark;
  const points = [primary, ...alternates.map((alt) => alt.point)];

  return (
    <div className="gs-map-wrap">
      <div className="gs-map-result-head">
        <p>Map style</p>
        <div className="gs-map-theme-pills">
          {Object.keys(TILE_LAYERS).map((theme) => (
            <button
              key={theme}
              type="button"
              className={mapTheme === theme ? 'active' : ''}
              onClick={() => onThemeChange(theme)}
            >
              {theme}
            </button>
          ))}
        </div>
      </div>

      <MapContainer
        center={primary}
        zoom={6}
        className="gs-map"
        scrollWheelZoom
      >
        <TileLayer
          url={tile.url}
          attribution={tile.attribution}
          subdomains={tile.subdomains}
        />

        <CircleMarker
          center={primary}
          radius={9}
          pathOptions={{ color: '#f5f1e8', fillColor: '#f5f1e8', fillOpacity: 0.9, weight: 1.5 }}
        >
          <Popup>
            <strong>{entry.guessedCountry || 'Estimated location'}</strong>
            <br />
            {entry.coordinates.lat.toFixed(4)}, {entry.coordinates.lng.toFixed(4)}
          </Popup>
        </CircleMarker>

        {alternates.map((alt) => (
          <Fragment key={alt.id}>
            <Polyline
              positions={[primary, alt.point]}
              pathOptions={{ color: '#f5f1e8', opacity: 0.2, weight: 1, dashArray: '4 5' }}
            />
            <CircleMarker
              center={alt.point}
              radius={5}
              pathOptions={{ color: '#d9d4c7', fillColor: '#1c1c1c', fillOpacity: 1, weight: 1 }}
            >
              <Tooltip>{alt.label}</Tooltip>
            </CircleMarker>
          </Fragment>
        ))}

        <FitBounds points={points} />
      </MapContainer>
    </div>
  );
}

function UploadDock({ onPickFile, disabled, compact = false }) {
  const fileRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function pick(files) {
    const [file] = files || [];
    if (file) {
      onPickFile(file);
    }
  }

  return (
    <div
      className={`gs-upload-dock ${compact ? 'compact' : ''} ${dragging ? 'is-dragging' : ''}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) {
          setDragging(true);
        }
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        if (!disabled) {
          pick(event.dataTransfer.files);
        }
      }}
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(event) => {
          pick(event.target.files);
          event.target.value = '';
        }}
      />
      <button
        type="button"
        className="gs-upload-button"
        onClick={() => fileRef.current?.click()}
        disabled={disabled}
      >
        {compact ? 'Upload another image' : 'Drop an image, or click to upload'}
      </button>
      <p className="gs-upload-note">JPG, PNG, WEBP • GeoSeer accepts image input only</p>
    </div>
  );
}

function DashboardPage() {
  const { logout, token } = useAuth();
  const storageKeys = useMemo(() => buildStorageKeys(getTokenSubject(token)), [token]);
  const [items, setItems] = useState(() => loadJson(storageKeys.investigations, []));
  const [activeId, setActiveId] = useState(() => localStorage.getItem(storageKeys.activeId));
  const [mapTheme, setMapTheme] = useState(() => localStorage.getItem(storageKeys.mapTheme) || 'dark');
  const [sidebarOpen, setSidebarOpen] = useState(() => window.matchMedia('(min-width: 901px)').matches);
  const [pageError, setPageError] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [draftTitle, setDraftTitle] = useState('');

  const activeItem = useMemo(
    () => items.find((item) => item.id === activeId) || null,
    [items, activeId]
  );

  useEffect(() => {
    saveJson(storageKeys.investigations, items);
  }, [items, storageKeys.investigations]);

  useEffect(() => {
    if (activeId) {
      localStorage.setItem(storageKeys.activeId, activeId);
    } else {
      localStorage.removeItem(storageKeys.activeId);
    }
  }, [activeId, storageKeys.activeId]);

  useEffect(() => {
    localStorage.setItem(storageKeys.mapTheme, mapTheme);
  }, [mapTheme, storageKeys.mapTheme]);

  useEffect(() => {
    setItems(loadJson(storageKeys.investigations, []));
    setActiveId(localStorage.getItem(storageKeys.activeId));
    setMapTheme(localStorage.getItem(storageKeys.mapTheme) || 'dark');
    setEditingId(null);
    setDraftTitle('');
    setPageError('');
  }, [storageKeys]);

  function updateItem(id, updater) {
    setItems((previous) =>
      previous.map((item) => {
        if (item.id !== id) {
          return item;
        }

        const nextPatch = typeof updater === 'function' ? updater(item) : updater;
        return { ...item, ...nextPatch, updatedAt: Date.now() };
      })
    );
  }

  async function runAnalysisForItem(id, file) {
    updateItem(id, {
      status: 'processing',
      uploadProgress: 100,
      errorMessage: '',
    });

    try {
      const result = await analyzeImage(file, (progress) => {
        updateItem(id, {
          status: 'uploading',
          uploadProgress: progress,
        });
      });

      updateItem(id, {
        status: 'done',
        guessedCountry: result.guessedCountry,
        confidence: result.confidence,
        summary: result.summary,
        language: result.language,
        ocrText: result.ocrText,
        topCountries: result.topCountries,
        coordinates: result.coordinates,
        raw: result.raw,
        errorMessage: '',
      });
    } catch (requestError) {
      updateItem(id, {
        status: 'error',
        errorMessage: requestError.message || 'Image analysis failed',
      });
    }
  }

  async function handleFile(file) {
    setPageError('');

    if (!file) {
      return;
    }

    if (!file.type.startsWith('image/')) {
      setPageError('Only image files are allowed.');
      return;
    }

    const maxBytes = MAX_FILE_MB * 1024 * 1024;
    if (file.size > maxBytes) {
      setPageError(`Image is too large. Max size is ${MAX_FILE_MB}MB.`);
      return;
    }

    const imageDataUrl = await fileToDataUrl(file);
    const item = {
      ...buildItem(file),
      imageDataUrl,
    };

    setItems((previous) => [item, ...previous]);
    setActiveId(item.id);
    setSidebarOpen(window.matchMedia('(min-width: 901px)').matches);
    await runAnalysisForItem(item.id, file);
  }

  function removeItem(id) {
    setItems((previous) => {
      const next = previous.filter((item) => item.id !== id);
      if (id === activeId) {
        setActiveId(next[0]?.id || null);
      }
      return next;
    });
  }

  function clearAll() {
    setItems([]);
    setActiveId(null);
  }

  function retryItem(item) {
    if (!item.imageDataUrl) {
      setPageError('Original file is missing. Please upload the image again.');
      return;
    }

    const retryFile = dataUrlToFile(item.imageDataUrl, item.fileName || 'image.jpg');
    void runAnalysisForItem(item.id, retryFile);
  }

  function beginRename(item) {
    setEditingId(item.id);
    setDraftTitle(item.title || 'New investigation');
  }

  function commitRename(itemId) {
    const nextTitle = draftTitle.trim();
    if (nextTitle) {
      updateItem(itemId, { title: nextTitle });
    }
    setEditingId(null);
    setDraftTitle('');
  }

  return (
    <div className="gs-layout">
      <div
        className={`gs-sidebar-overlay ${sidebarOpen ? 'is-open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      <aside className={`gs-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="gs-sidebar-head">
          <div>
            <p className="gs-brand">GeoSeer</p>
            <p className="gs-subtle">Atlas of Inquiry</p>
          </div>
          <button type="button" className="gs-icon-btn mobile-only" onClick={() => setSidebarOpen(false)}>
            ✕
          </button>
        </div>

        <div className="gs-side-actions">
          <button className="gs-ghost-btn" type="button" onClick={() => setActiveId(null)}>
            + New Investigation
          </button>
          <button className="gs-ghost-btn" type="button" onClick={clearAll}>
            Clear All
          </button>
        </div>

        <ul className="gs-history-list">
          {items
            .slice()
            .sort((a, b) => b.updatedAt - a.updatedAt)
            .map((item) => (
              <li key={item.id}>
                <div className={`gs-history-item ${activeId === item.id ? 'active' : ''}`}>
                  {activeId === item.id ? <span className="gs-history-active-bar" /> : null}
                  <span className="gs-history-leading-icon" aria-hidden="true">
                    {HISTORY_ICONS.message}
                  </span>

                  {editingId === item.id ? (
                    <form
                      className="gs-rename-form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        commitRename(item.id);
                      }}
                    >
                      <input
                        value={draftTitle}
                        onChange={(event) => setDraftTitle(event.target.value)}
                        onBlur={() => commitRename(item.id)}
                        autoFocus
                      />
                    </form>
                  ) : (
                    <button
                      type="button"
                      className="gs-history-main"
                      onClick={() => setActiveId(item.id)}
                      title={item.title || item.fileName}
                    >
                      <span className="gs-history-title">{item.title || item.fileName}</span>
                    </button>
                  )}

                  <div className="gs-history-actions">
                    <button
                      type="button"
                      className="gs-mini-btn icon"
                      onClick={() => beginRename(item)}
                      aria-label="Rename investigation"
                      title="Rename"
                    >
                      {HISTORY_ICONS.pencil}
                    </button>
                    <button
                      type="button"
                      className="gs-mini-btn icon"
                      onClick={() => removeItem(item.id)}
                      aria-label="Delete investigation"
                      title="Delete"
                    >
                      {HISTORY_ICONS.trash}
                    </button>
                  </div>
                </div>
              </li>
            ))}
        </ul>

        <div className="gs-account-box">
          <button className="gs-ghost-btn" type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className={`gs-main ${sidebarOpen ? 'with-sidebar' : ''}`}>
        <header className="gs-main-head">
          <div className="gs-head-left">
            <button type="button" className="gs-icon-btn" onClick={() => setSidebarOpen((v) => !v)}>
              ☰
            </button>
            <div>
              <h1>{activeItem?.title || 'GeoSeer'}</h1>
              <p>Image-to-location assistant</p>
            </div>
          </div>

        </header>

        <section className="gs-content">
          {!activeItem ? (
            <div className="gs-empty">
              <span className="gs-badge">Image • to • location</span>
              <h2>Where was this taken?</h2>
              <p>
                Upload one photo and GeoSeer will estimate the location based on visual cues and
                display it in a map-ready result view.
              </p>
              <UploadDock onPickFile={(file) => void handleFile(file)} disabled={false} />
            </div>
          ) : (
            <div className="gs-thread">
              <article className="gs-user-card">
                <img src={activeItem.imageDataUrl} alt={activeItem.fileName} />
                <p>Field exhibit • {formatTime(activeItem.createdAt)}</p>
              </article>

              <article className="gs-assistant-card">
                <div className="gs-assistant-top">
                  <h3>GeoSeer Analysis</h3>
                  <span className={`gs-status gs-status--${activeItem.status}`}>
                    {statusLabel(activeItem.status)}
                  </span>
                </div>

                {activeItem.status === 'uploading' ? (
                  <p className="gs-note">Uploading image... {activeItem.uploadProgress}%</p>
                ) : null}

                {activeItem.status === 'processing' ? (
                  <p className="gs-note">Analyzing visual cues and geographic patterns...</p>
                ) : null}

                {activeItem.status === 'done' ? (
                  <div className="gs-result-grid">
                    <div className="gs-result-facts">
                      <p>
                        <strong>Estimated country:</strong> {activeItem.guessedCountry}
                      </p>
                      <p>
                        <strong>Confidence:</strong> {confidenceLabel(activeItem.confidence)}
                      </p>
                      <p>
                        <strong>Detected language:</strong> {activeItem.language || 'Unknown'}
                      </p>
                      {activeItem.topCountries.length > 0 ? (
                        <p>
                          <strong>Top candidates:</strong> {activeItem.topCountries.join(', ')}
                        </p>
                      ) : null}
                      {activeItem.ocrText ? (
                        <p>
                          <strong>OCR text:</strong> {activeItem.ocrText}
                        </p>
                      ) : null}
                      <p className="gs-quote">"{activeItem.summary}"</p>
                    </div>
                    <MapView
                      entry={activeItem}
                      mapTheme={mapTheme}
                      onThemeChange={setMapTheme}
                    />
                  </div>
                ) : null}

                {activeItem.status === 'error' ? (
                  <div className="gs-error-wrap">
                    <p>{activeItem.errorMessage || 'Analysis failed.'}</p>
                    <button type="button" className="gs-ghost-btn" onClick={() => retryItem(activeItem)}>
                      Retry analysis
                    </button>
                  </div>
                ) : null}

                {pageError ? <p className="gs-global-error">{pageError}</p> : null}
              </article>
            </div>
          )}
        </section>

      </main>
    </div>
  );
}

export default DashboardPage;
