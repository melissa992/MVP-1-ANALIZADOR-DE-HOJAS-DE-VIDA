import { useEffect, useState } from 'react';
import './App.css';
import VacancyForm from './components/VacancyForm';
import MatchingPanel from './components/matching/MatchingPanel';
import RankingDashboard from './components/ranking/RankingDashboard';
import {
  apiFetch,
  getAccessToken,
  getCurrentUser,
  getFileStatus,
  login,
  logout,
  retryFileProcessing,
} from './services/api';
import Login from './components/auth/Login';

function Workspace({ currentUser, onLogout }) {
  const [activeTab, setActiveTab] = useState('cvs');
  const [visitedTabs, setVisitedTabs] = useState(() => new Set(['cvs']));
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [responseResult, setResponseResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [extractionView, setExtractionView] = useState(null);
  const [extractingFileId, setExtractingFileId] = useState(null);
  const [profileView, setProfileView] = useState(null);
  const [analyzingFileId, setAnalyzingFileId] = useState(null);
  const [fileStatuses, setFileStatuses] = useState({});
  const [retryingFileId, setRetryingFileId] = useState(null);
  const [showRawProfile, setShowRawProfile] = useState(false);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setVisitedTabs((previousTabs) => new Set(previousTabs).add(tab));
  };

  useEffect(() => {
    const activeFileIds = Object.entries(fileStatuses)
      .filter(([, fileStatus]) => ['EXTRACTING', 'ANALYZING'].includes(fileStatus.status))
      .map(([fileId]) => fileId);
    if (activeFileIds.length === 0) return undefined;

    let isActive = true;
    const pollStatuses = async () => {
      const results = await Promise.all(
        activeFileIds.map(async (fileId) => {
          try {
            return [fileId, await getFileStatus(fileId)];
          } catch (error) {
            setErrorMsg(`No fue posible consultar el estado de ${fileId}: ${error.message}`);
            return null;
          }
        }),
      );

      if (!isActive) return;
      setFileStatuses((current) => {
        let changed = false;
        const updated = { ...current };
        results.forEach((result) => {
          if (!result) return;
          const [fileId, nextStatus] = result;
          const previousStatus = current[fileId];
          if (
            previousStatus?.status !== nextStatus.status ||
            previousStatus?.error_message !== nextStatus.error_message
          ) {
            updated[fileId] = nextStatus;
            changed = true;
          }
        });
        return changed ? updated : current;
      });
    };

    const intervalId = window.setInterval(pollStatuses, 1000);
    pollStatuses();
    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [fileStatuses]);

  const handleFileSelect = (e) => {
    const selected = Array.from(e.target.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (selected.length === 0) {
      setErrorMsg('Por favor selecciona únicamente archivos en formato PDF.');
      return;
    }
    if (selected.length > 20) {
      setErrorMsg('El límite máximo es de 20 archivos por carga.');
      return;
    }
    setErrorMsg('');
    setFiles(selected);
    setFileStatuses({});
    setResponseResult(null);
    setExtractionView(null);
    setProfileView(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (dropped.length === 0) {
      setErrorMsg('Los archivos deben estar en formato PDF.');
      return;
    }
    setErrorMsg('');
    setFiles(dropped);
    setFileStatuses({});
    setResponseResult(null);
    setExtractionView(null);
    setProfileView(null);
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setLoading(true);
    setErrorMsg('');
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const res = await apiFetch('/upload-cv/', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error en el servidor');

      setResponseResult(data);
      setFileStatuses(
        Object.fromEntries(
          (data.results || [])
            .filter((uploadedFile) => uploadedFile.file_id)
            .map((uploadedFile) => [
              uploadedFile.file_id,
              { status: 'PENDING', error_message: null },
            ]),
        ),
      );
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExtractText = async (uploadedFile) => {
    setExtractionView({ filename: uploadedFile.filename, loading: true });
    setExtractingFileId(uploadedFile.file_id);
    setFileStatuses((current) => ({
      ...current,
      [uploadedFile.file_id]: { status: 'EXTRACTING', error_message: null },
    }));

    try {
      const res = await apiFetch(`/extract-text/${encodeURIComponent(uploadedFile.file_id)}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'No fue posible extraer el texto.');

      setExtractionView({ filename: uploadedFile.filename, data });
      const fileStatus = await getFileStatus(uploadedFile.file_id);
      setFileStatuses((current) => ({ ...current, [uploadedFile.file_id]: fileStatus }));
    } catch (err) {
      setExtractionView({ filename: uploadedFile.filename, error: err.message });
      setFileStatuses((current) => ({
        ...current,
        [uploadedFile.file_id]: { status: 'FAILED', error_message: err.message },
      }));
    } finally {
      setExtractingFileId(null);
    }
  };

  const handleAnalyzeProfile = async (uploadedFile) => {
    setProfileView({ filename: uploadedFile.filename, loading: true });
    setAnalyzingFileId(uploadedFile.file_id);
    setShowRawProfile(false);
    setErrorMsg('');
    setFileStatuses((current) => ({
      ...current,
      [uploadedFile.file_id]: { status: 'EXTRACTING', error_message: null },
    }));

    try {
      const res = await apiFetch(`/analyze-cv/${encodeURIComponent(uploadedFile.file_id)}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'No fue posible analizar el CV.');

      setProfileView({ filename: uploadedFile.filename, data });
      setFileStatuses((current) => ({
        ...current,
        [uploadedFile.file_id]: { status: 'COMPLETED', error_message: null },
      }));
    } catch (err) {
      setProfileView({ filename: uploadedFile.filename, error: err.message });
      setFileStatuses((current) => ({
        ...current,
        [uploadedFile.file_id]: { status: 'FAILED', error_message: err.message },
      }));
    } finally {
      setAnalyzingFileId(null);
    }
  };

  const handleRetry = async (uploadedFile) => {
    setRetryingFileId(uploadedFile.file_id);
    setErrorMsg('');
    setFileStatuses((current) => ({
      ...current,
      [uploadedFile.file_id]: { status: 'EXTRACTING', error_message: null },
    }));

    try {
      const fileStatus = await retryFileProcessing(uploadedFile.file_id);
      setFileStatuses((current) => ({ ...current, [uploadedFile.file_id]: fileStatus }));
    } catch (err) {
      setFileStatuses((current) => ({
        ...current,
        [uploadedFile.file_id]: { status: 'FAILED', error_message: err.message },
      }));
    } finally {
      setRetryingFileId(null);
    }
  };

  const getStatusLabel = (status) => ({
    PENDING: 'En cola',
    EXTRACTING: 'Extrayendo',
    ANALYZING: 'Analizando',
    COMPLETED: 'Completado',
    FAILED: 'Error',
  }[status] || status);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="CV-Match AI, inicio">
          <span className="brand-mark" aria-hidden="true">CV</span>
          <span className="brand-copy">
            <strong>CV-Match</strong>
            <span>Talent intelligence</span>
          </span>
        </a>
        <div className="topbar-meta">
          <span className="status-indicator" aria-hidden="true" />
          <span>{currentUser.email}</span>
          <button type="button" className="logout-button" onClick={onLogout}>Cerrar sesión</button>
        </div>
      </header>

      <main className="workspace" id="top">
        {/* Selector de módulo / pestaña */}
        <nav className="flex items-center gap-2 p-1.5 bg-slate-200/60 backdrop-blur-xs rounded-xl mb-8 max-w-fit border border-slate-300/50" aria-label="Secciones del sistema">
          <button
            type="button"
            onClick={() => handleTabChange('cvs')}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wide transition-all cursor-pointer ${activeTab === 'cvs'
              ? 'bg-[#315e50] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
          >
            Carga de Hojas de Vida
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('vacancies')}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wide transition-all cursor-pointer ${activeTab === 'vacancies'
              ? 'bg-[#315e50] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
          >
            Registrar Vacantes
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('matching')}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wide transition-all cursor-pointer ${activeTab === 'matching'
              ? 'bg-[#315e50] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
          >
            Matching Engine
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('ranking')}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wide transition-all cursor-pointer ${activeTab === 'ranking'
              ? 'bg-[#315e50] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
          >
            Ranking de candidatos
          </button>
        </nav>

        {visitedTabs.has('ranking') && (
        <section hidden={activeTab !== 'ranking'}>
          <div>
            <section className="page-intro">
              <div>
                <p className="eyebrow">GESTIÓN DE TALENTO <span> / </span> Dashboard</p>
                <h1>Ranking de candidatos</h1>
                <p className="intro-copy">Compara los resultados de matching, filtra por score o habilidad y encuentra los perfiles con mayor ajuste.</p>
              </div>
              <span className="module-label"><span className="module-dot" /> Módulo 04</span>
            </section>
            <RankingDashboard />
          </div>
        </section>
        )}

        {visitedTabs.has('matching') && (
        <section hidden={activeTab !== 'matching'}>
          <div>
            <section className="page-intro">
              <div>
                <p className="eyebrow">MATCHING ENGINE <span> / </span> Score</p>
                <h1>Score de idoneidad</h1>
                <p className="intro-copy">Evalúa la compatibilidad entre un candidato y una vacante. Pega los JSON estructurados y obtén un score numérico preciso con desglose por eje.</p>
              </div>
              <span className="module-label"><span className="module-dot" /> Módulo 03</span>
            </section>
            <MatchingPanel />
          </div>
        </section>
        )}

        {visitedTabs.has('vacancies') && (
        <section hidden={activeTab !== 'vacancies'}>
          <div>
            <section className="page-intro">
              <div>
                <p className="eyebrow">GESTIÓN DE TALENTO <span> / </span> Vacantes</p>
                <h1>Registro de vacantes</h1>
                <p className="intro-copy">Registra las especificaciones de tus ofertas laborales para habilitar el screening y matching inteligente.</p>
              </div>
              <span className="module-label"><span className="module-dot" /> Módulo 02</span>
            </section>

            <VacancyForm />
          </div>
        </section>
        )}

        {visitedTabs.has('cvs') && (
        <section hidden={activeTab !== 'cvs'}>
          <>
            <section className="page-intro">
              <div>
                <p className="eyebrow">GESTIÓN DE CANDIDATURAS <span> / </span> INGESTA</p>
                <h1>Carga de hojas de vida</h1>
                <p className="intro-copy">Incorpora currículums para iniciar su análisis y organizar tus candidaturas.</p>
              </div>
              <span className="module-label"><span className="module-dot" /> Módulo 01</span>
            </section>

            <div className="content-grid">
              <section className="upload-panel" aria-labelledby="upload-heading">
                <div className="panel-heading">
                  <div>
                    <span className="step-label">PASO 1 DE 1</span>
                    <h2 id="upload-heading">Añade tus documentos</h2>
                    <p>Selecciona archivos PDF desde tu equipo o arrástralos al área de carga.</p>
                  </div>
                  <span className="pdf-badge">PDF</span>
                </div>

                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('hiddenFileInput').click()}
                  className="dropzone"
                >
                  <span className="upload-icon-wrap" aria-hidden="true">
                    <svg className="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 15.5v3A1.5 1.5 0 006.5 20h11a1.5 1.5 0 001.5-1.5v-3" />
                    </svg>
                  </span>
                  <span className="dropzone-title">Arrastra tus archivos aquí</span>
                  <span className="dropzone-subtitle">o <span className="browse-link">explora tu equipo</span></span>
                  <span className="dropzone-note">PDF · Hasta 20 archivos · Máximo 10 MB por archivo</span>
                  <input
                    id="hiddenFileInput"
                    type="file"
                    multiple
                    accept=".pdf"
                    className="visually-hidden"
                    onChange={handleFileSelect}
                  />
                </div>

                {errorMsg && (
                  <div className="error-message" role="alert">
                    <span className="error-icon" aria-hidden="true">!</span>
                    {errorMsg}
                  </div>
                )}

                {files.length > 0 && (
                  <div className="selected-files">
                    <div className="files-heading">
                      <h3>Archivos seleccionados <span className="file-count">{files.length}</span></h3>
                      <button onClick={() => setFiles([])} className="clear-button">Limpiar lista</button>
                    </div>

                    <div className="file-list">
                      {files.map((file, idx) => (
                        <div key={idx} className="file-row">
                          <span className="file-type-icon" aria-hidden="true">PDF</span>
                          <span className="file-name">{file.name}</span>
                          <span className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={handleUpload}
                      disabled={loading}
                      className="submit-button"
                    >
                      {loading ? (
                        <>
                          <svg className="spinner" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                            <circle className="spinner-track" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
                            <path className="spinner-head" fill="currentColor" d="M12 3a9 9 0 00-9 9h3a6 6 0 016-6V3z" />
                          </svg>
                          Procesando documentos...
                        </>
                      ) : (
                        `Analizar y registrar ${files.length} CV(s)`
                      )}
                    </button>
                  </div>
                )}

                {responseResult && (
                  <div className="result-panel">
                    <h3><span className="success-dot" /> Resultado de la carga</h3>
                    <div className="uploaded-results">
                      {(responseResult.results || []).map((uploadedFile, index) => (
                        <div className="uploaded-file-row" key={uploadedFile.file_id || `${uploadedFile.filename}-${index}`}>
                          <span className={`file-type-icon ${uploadedFile.status === 'error' ? 'file-type-error' : ''}`} aria-hidden="true">
                            {uploadedFile.status === 'success' ? 'PDF' : '!'}
                          </span>
                          <span className="uploaded-file-name" title={uploadedFile.filename}>{uploadedFile.filename}</span>
                          {uploadedFile.status === 'success' ? (
                            <>
                              {fileStatuses[uploadedFile.file_id] && (
                                <div
                                  className={`processing-status status-${fileStatuses[uploadedFile.file_id].status.toLowerCase()}`}
                                  title={fileStatuses[uploadedFile.file_id].error_message || undefined}
                                  role="status"
                                >
                                  {['PENDING', 'EXTRACTING', 'ANALYZING'].includes(fileStatuses[uploadedFile.file_id].status) && (
                                    <svg className="status-spinner" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                                      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity=".25" />
                                      <path fill="currentColor" d="M12 3a9 9 0 00-9 9h3a6 6 0 016-6V3z" />
                                    </svg>
                                  )}
                                  {getStatusLabel(fileStatuses[uploadedFile.file_id].status)}
                                </div>
                              )}
                              {fileStatuses[uploadedFile.file_id]?.status === 'FAILED' && (
                                <span className="status-error-message">
                                  {fileStatuses[uploadedFile.file_id].error_message}
                                </span>
                              )}
                              <div className="file-actions">
                                {fileStatuses[uploadedFile.file_id]?.status === 'FAILED' && (
                                  <button
                                    type="button"
                                    className="extract-button retry-button"
                                    onClick={() => handleRetry(uploadedFile)}
                                    disabled={Boolean(retryingFileId || extractingFileId || analyzingFileId)}
                                  >
                                    {retryingFileId === uploadedFile.file_id ? 'Reintentando...' : '🔄 Reintentar'}
                                  </button>
                                )}
                                <button
                                  type="button"
                                  className="extract-button"
                                  onClick={() => handleAnalyzeProfile(uploadedFile)}
                                  disabled={Boolean(
                                    extractingFileId ||
                                    analyzingFileId ||
                                    retryingFileId ||
                                    ['EXTRACTING', 'ANALYZING'].includes(fileStatuses[uploadedFile.file_id]?.status),
                                  )}
                                >
                                  {analyzingFileId === uploadedFile.file_id ? 'Analizando...' : 'Analizar con IA'}
                                </button>
                                <button
                                  type="button"
                                  className="extract-button extract-button-secondary"
                                  onClick={() => handleExtractText(uploadedFile)}
                                  disabled={Boolean(
                                    extractingFileId ||
                                    analyzingFileId ||
                                    retryingFileId ||
                                    ['EXTRACTING', 'ANALYZING'].includes(fileStatuses[uploadedFile.file_id]?.status),
                                  )}
                                >
                                  {extractingFileId === uploadedFile.file_id ? 'Extrayendo...' : 'Ver texto extraído'}
                                </button>
                              </div>
                            </>
                          ) : (
                            <span className="upload-status-error" title={uploadedFile.message}>No se pudo cargar</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              <aside className="guidance-panel" aria-label="Información de carga">
                <div className="guidance-topline"><span className="guidance-mark">i</span> INFORMACIÓN</div>
                <h2>Todo listo para empezar</h2>
                <p>Sube los currículums y deja que el sistema prepare la información para tu proceso de selección.</p>
                <div className="guidance-divider" />
                <div className="requirements-title">Requisitos de carga</div>
                <div className="requirement-row"><span className="check-mark">✓</span><span>Formato PDF</span></div>
                <div className="requirement-row"><span className="check-mark">✓</span><span>Hasta 20 documentos por carga</span></div>
                <div className="requirement-row"><span className="check-mark">✓</span><span>Máximo 10 MB por documento</span></div>
                <div className="privacy-note">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.6" d="M12 3l8 3v5c0 5-3.5 8.2-8 10-4.5-1.8-8-5-8-10V6l8-3z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.6" d="M9 12l2 2 4-4" />
                  </svg>
                  Tus documentos se procesan de forma segura.
                </div>
              </aside>
            </div>
          </>
        </section>
        )}
      </main>

      <footer className="footer">
        <span>CV-Match AI</span>
        <span>Herramientas para una selección más ágil</span>
      </footer>

      {extractionView && (
        <div className="modal-backdrop" onClick={() => setExtractionView(null)}>
          <section
            className="extraction-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="extraction-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-heading">
              <div>
                <p className="dialog-eyebrow">LECTURA DEL DOCUMENTO</p>
                <h2 id="extraction-title">Texto extraído</h2>
              </div>
              <button type="button" className="dialog-close" onClick={() => setExtractionView(null)} aria-label="Cerrar ventana">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
            <p className="dialog-filename" title={extractionView.filename}>{extractionView.filename}</p>

            {extractionView.loading && (
              <div className="extraction-loading">
                <span className="spinner extraction-spinner" aria-hidden="true" />
                <span>Extrayendo texto del currículum...</span>
              </div>
            )}

            {extractionView.error && (
              <div className="error-message extraction-error" role="alert">
                <span className="error-icon" aria-hidden="true">!</span>
                {extractionView.error}
              </div>
            )}

            {extractionView.data && (
              <>
                <div className="extraction-meta">
                  <span className={`extraction-status ${extractionView.data.status === 'warning' ? 'is-warning' : 'is-success'}`}>
                    <span />
                    {extractionView.data.status === 'warning' ? 'Revisión necesaria' : 'Extracción completada'}
                  </span>
                  {Number.isInteger(extractionView.data.total_pages) && (
                    <span>{extractionView.data.total_pages} {extractionView.data.total_pages === 1 ? 'página' : 'páginas'}</span>
                  )}
                </div>
                {extractionView.data.message && (
                  <p className="extraction-notice">{extractionView.data.message}</p>
                )}
                <pre className="extracted-text">
                  {extractionView.data.extracted_text || 'No se encontró texto seleccionable en este documento.'}
                </pre>
                {extractionView.data.pages_summary?.length > 0 && (
                  <div className="page-summary">
                    {extractionView.data.pages_summary.map((page) => (
                      <span key={page.page}>Página {page.page}: {page.text_length} caracteres</span>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}

      {profileView && (
        <div className="modal-backdrop" onClick={() => setProfileView(null)}>
          <section
            className="extraction-dialog profile-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-heading">
              <div>
                <p className="dialog-eyebrow">ANÁLISIS INTELIGENTE</p>
                <h2 id="profile-title">Perfil estructurado</h2>
              </div>
              <button type="button" className="dialog-close" onClick={() => setProfileView(null)} aria-label="Cerrar ventana">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
            <p className="dialog-filename" title={profileView.filename}>{profileView.filename}</p>

            {profileView.loading && (
              <div className="extraction-loading">
                <span className="spinner extraction-spinner" aria-hidden="true" />
                <span>Analizando el currículum con IA...</span>
              </div>
            )}

            {profileView.error && (
              <div className="error-message extraction-error" role="alert">
                <span className="error-icon" aria-hidden="true">!</span>
                {profileView.error}
              </div>
            )}

            {profileView.data && (
              <div className="profile-content">
                <div className="profile-toolbar">
                  <span className="profile-status"><span className="success-dot" /> Estructura validada</span>
                  <button
                    type="button"
                    className={`view-toggle ${showRawProfile ? 'is-active' : ''}`}
                    onClick={() => setShowRawProfile((visible) => !visible)}
                    aria-pressed={showRawProfile}
                  >
                    {showRawProfile ? 'Ver perfil visual' : 'Inspeccionar JSON'}
                  </button>
                </div>

                {showRawProfile ? (
                  <pre className="profile-json">{JSON.stringify(profileView.data, null, 2)}</pre>
                ) : (
                  <div className="profile-sections">
                    <section className="profile-section profile-identity">
                      <div className="section-heading"><span className="section-kicker">IDENTIDAD</span><span className="section-rule" /></div>
                      <div className="identity-grid">
                        <div><span>Nombre</span><strong>{profileView.data.nombre_completo || 'No informado'}</strong></div>
                        <div><span>Correo</span><strong>{profileView.data.correo || 'No informado'}</strong></div>
                        <div><span>Teléfono</span><strong>{profileView.data.telefono || 'No informado'}</strong></div>
                        <div><span>Ubicación</span><strong>{profileView.data.ubicacion || 'No informada'}</strong></div>
                      </div>
                      {profileView.data.resumen_profesional && <p className="profile-summary">{profileView.data.resumen_profesional}</p>}
                    </section>

                    <section className="profile-section">
                      <div className="section-heading"><span className="section-kicker">HABILIDADES Y LENGUAS</span><span className="section-rule" /></div>
                      <div className="tag-list">
                        {[...(profileView.data.habilidades || []), ...(profileView.data.idiomas || []).map((idioma) => `Idioma: ${idioma}`)].length > 0
                          ? [...(profileView.data.habilidades || []), ...(profileView.data.idiomas || []).map((idioma) => `Idioma: ${idioma}`)].map((item) => <span className="profile-tag" key={item}>{item}</span>)
                          : <span className="profile-empty">No se registraron habilidades.</span>}
                      </div>
                    </section>

                    <section className="profile-section">
                      <div className="section-heading"><span className="section-kicker">EXPERIENCIA LABORAL</span><span className="section-rule" /></div>
                      {(profileView.data.experiencia || []).length > 0 ? (
                        <ol className="timeline-list">
                          {profileView.data.experiencia.map((item, index) => (
                            <li key={`${item.empresa || 'experiencia'}-${index}`}>
                              <span className="timeline-index">{String(index + 1).padStart(2, '0')}</span>
                              <div><strong>{item.cargo || 'Cargo no informado'}</strong><span className="timeline-company">{item.empresa || 'Empresa no informada'} · {item.fecha_inicio || '?'} - {item.fecha_fin || 'actualidad'}</span>{item.funciones?.length > 0 && <ul>{item.funciones.map((funcion) => <li key={funcion}>{funcion}</li>)}</ul>}</div>
                            </li>
                          ))}
                        </ol>
                      ) : <p className="profile-empty">No se registró experiencia laboral.</p>}
                    </section>

                    <section className="profile-section">
                      <div className="section-heading"><span className="section-kicker">EDUCACIÓN</span><span className="section-rule" /></div>
                      {(profileView.data.educacion || []).length > 0 ? (
                        <ol className="timeline-list education-list">
                          {profileView.data.educacion.map((item, index) => <li key={`${item.institucion || 'educacion'}-${index}`}><span className="timeline-index">{String(index + 1).padStart(2, '0')}</span><div><strong>{item.titulo || 'Título no informado'}</strong><span className="timeline-company">{item.institucion || 'Institución no informada'} · {item.anio_graduacion || 'Año no informado'}</span></div></li>)}
                        </ol>
                      ) : <p className="profile-empty">No se registró educación.</p>}
                    </section>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(Boolean(getAccessToken()));
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  useEffect(() => {
    const handleExpiredSession = () => {
      setCurrentUser(null);
      setCheckingSession(false);
    };
    window.addEventListener('auth-expired', handleExpiredSession);

    if (getAccessToken()) {
      getCurrentUser()
        .then(setCurrentUser)
        .catch(() => setCurrentUser(null))
        .finally(() => setCheckingSession(false));
    }

    return () => window.removeEventListener('auth-expired', handleExpiredSession);
  }, []);

  const handleLogin = async (email, password) => {
    setLoginLoading(true);
    setLoginError('');
    try {
      await login(email, password);
      setCurrentUser(await getCurrentUser());
    } catch (error) {
      setLoginError(error.message);
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      setCurrentUser(null);
    }
  };

  if (checkingSession) {
    return <main className="session-loading" aria-live="polite">Verificando sesión segura...</main>;
  }
  if (!currentUser) {
    return <Login onLogin={handleLogin} loading={loginLoading} error={loginError} />;
  }
  return <Workspace currentUser={currentUser} onLogout={handleLogout} />;
}