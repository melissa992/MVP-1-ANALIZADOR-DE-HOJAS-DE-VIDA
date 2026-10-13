import { useEffect, useState } from 'react';
import { getCandidateDetail } from '../../services/api';
import './CandidateDetailModal.css';

function DetailSection({ title, children }) {
  return (
    <section className="candidate-detail-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function CandidateDetailModal({ candidateId, vacancyId, onClose }) {
  const [result, setResult] = useState(null);
  const [requestError, setRequestError] = useState(null);
  const candidate = result?.candidateId === candidateId ? result.data : null;
  const error = requestError?.candidateId === candidateId ? requestError.message : '';
  const loading = !candidate && !error;

  useEffect(() => {
    let active = true;
    getCandidateDetail(candidateId, vacancyId)
      .then((data) => {
        if (active) setResult({ candidateId, data });
      })
      .catch((requestError) => {
        if (active) setRequestError({ candidateId, message: requestError.message });
      })
    return () => {
      active = false;
    };
  }, [candidateId, vacancyId]);

  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  return (
    <div className="candidate-modal-backdrop" onClick={onClose}>
      <section
        className="candidate-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="candidate-detail-header">
          <div>
            <p className="candidate-detail-eyebrow">FICHA DEL ASPIRANTE</p>
            <h2 id="candidate-detail-title">
              {candidate?.candidate_name || 'Detalle del candidato'}
            </h2>
            {candidate && <p className="candidate-detail-role">{candidate.cargo}</p>}
          </div>
          <button
            type="button"
            className="candidate-detail-close"
            onClick={onClose}
            aria-label="Cerrar detalle"
          >
            ×
          </button>
        </header>

        {candidate && (
          <div className="candidate-detail-meta">
            <span className={`ranking-match-badge ranking-match-${candidate.score >= 80 ? 'high' : candidate.score >= 50 ? 'medium' : 'low'}`}>
              Score · {candidate.score}%
            </span>
            <span>{candidate.vacancy_title}</span>
          </div>
        )}

        {loading && <p className="candidate-detail-state" role="status">Cargando ficha completa...</p>}
        {error && <p className="candidate-detail-error" role="alert">{error}</p>}

        {candidate && !loading && (
          <div className="candidate-detail-content">
            <DetailSection title="Análisis de IA">
              <div className="candidate-explanation-grid">
                <div className="candidate-insight candidate-strengths">
                  <h4><span aria-hidden="true">✓</span> Puntos fuertes</h4>
                  {candidate.explanation.puntos_fuertes.length ? (
                    <ul>
                      {candidate.explanation.puntos_fuertes.map((item, index) => (
                        <li key={`${index}-${item}`}>{item}</li>
                      ))}
                    </ul>
                  ) : <p>No se identificaron requisitos cumplidos.</p>}
                </div>
                <div className="candidate-insight candidate-gaps">
                  <h4><span aria-hidden="true">⚠</span> Brechas detectadas</h4>
                  {candidate.explanation.brechas_detectadas.length ? (
                    <ul>
                      {candidate.explanation.brechas_detectadas.map((item, index) => (
                        <li key={`${index}-${item}`}>{item}</li>
                      ))}
                    </ul>
                  ) : <p>No se detectaron brechas para esta evaluación.</p>}
                </div>
              </div>
              <div className="candidate-executive-summary">
                <h4>Resumen ejecutivo</h4>
                <p>{candidate.explanation.justificacion_resumida}</p>
              </div>
              {candidate.breakdown && (
                <div className="candidate-breakdown" aria-label="Desglose del score">
                  {Object.entries(candidate.breakdown).map(([category, points]) => (
                    <div key={category}>
                      <span>{category}</span>
                      <strong>{points.score}/{points.max_score}</strong>
                    </div>
                  ))}
                </div>
              )}
            </DetailSection>

            <DetailSection title="Perfil profesional">
              <div className="candidate-profile-grid">
                <div><span>Experiencia total</span><strong>{candidate.experience_years} años</strong></div>
                <div><span>Nivel de estudios</span><strong>{candidate.education_level}</strong></div>
                <div><span>Correo</span><strong>{candidate.email || 'No registrado'}</strong></div>
                <div><span>Teléfono</span><strong>{candidate.phone || 'No registrado'}</strong></div>
              </div>
              <h4 className="candidate-subheading">Habilidades técnicas</h4>
              <div className="candidate-detail-pills">
                {candidate.skills.length
                  ? candidate.skills.map((item) => <span key={item}>{item}</span>)
                  : <p>No se registraron habilidades.</p>}
              </div>
              <h4 className="candidate-subheading">Idiomas</h4>
              <div className="candidate-detail-pills">
                {candidate.languages.length
                  ? candidate.languages.map((item) => <span key={item}>{item}</span>)
                  : <p>No se registraron idiomas.</p>}
              </div>
            </DetailSection>

            <DetailSection title="Experiencia laboral">
              {candidate.experience.length ? (
                <div className="candidate-history-list">
                  {candidate.experience.map((item, index) => (
                    <article key={`${item.empresa || 'experiencia'}-${index}`}>
                      <strong>{item.cargo || 'Cargo no especificado'}</strong>
                      <span>{item.empresa || 'Empresa no especificada'}</span>
                      <span>
                        {[item.fecha_inicio, item.fecha_fin].filter(Boolean).join(' — ') || 'Periodo no especificado'}
                      </span>
                      {item.funciones?.length > 0 && <p>{item.funciones.join(' · ')}</p>}
                    </article>
                  ))}
                </div>
              ) : <p>No se registró experiencia laboral detallada.</p>}
            </DetailSection>

            <DetailSection title="Formación académica">
              {candidate.education.length ? (
                <div className="candidate-history-list">
                  {candidate.education.map((item, index) => (
                    <article key={`${item.titulo || 'estudio'}-${index}`}>
                      <strong>{item.titulo || 'Título no especificado'}</strong>
                      <span>{item.institucion || 'Institución no especificada'}</span>
                      {item.anio_graduacion && <span>{item.anio_graduacion}</span>}
                    </article>
                  ))}
                </div>
              ) : <p>No se registró formación académica detallada.</p>}
            </DetailSection>
          </div>
        )}
      </section>
    </div>
  );
}

export default CandidateDetailModal;
