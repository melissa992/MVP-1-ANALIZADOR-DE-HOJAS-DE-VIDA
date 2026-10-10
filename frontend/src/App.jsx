import { useState } from 'react';
import './App.css';

function App() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [responseResult, setResponseResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [extractionView, setExtractionView] = useState(null);
  const [extractingFileId, setExtractingFileId] = useState(null);

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
    setResponseResult(null);
    setExtractionView(null);
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
    setResponseResult(null);
    setExtractionView(null);
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
      const res = await fetch('http://127.0.0.1:8000/upload-cv/', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error en el servidor');
      
      setResponseResult(data);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExtractText = async (uploadedFile) => {
    setExtractionView({ filename: uploadedFile.filename, loading: true });
    setExtractingFileId(uploadedFile.file_id);

    try {
      const res = await fetch(`http://127.0.0.1:8000/extract-text/${encodeURIComponent(uploadedFile.file_id)}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'No fue posible extraer el texto.');

      setExtractionView({ filename: uploadedFile.filename, data });
    } catch (err) {
      setExtractionView({ filename: uploadedFile.filename, error: err.message });
    } finally {
      setExtractingFileId(null);
    }
  };

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
          <span>Plataforma de selección</span>
        </div>
      </header>

      <main className="workspace" id="top">
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
                        <button
                          type="button"
                          className="extract-button"
                          onClick={() => handleExtractText(uploadedFile)}
                          disabled={Boolean(extractingFileId)}
                        >
                          {extractingFileId === uploadedFile.file_id ? 'Extrayendo...' : 'Ver texto extraído'}
                        </button>
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
    </div>
  );
}

export default App;