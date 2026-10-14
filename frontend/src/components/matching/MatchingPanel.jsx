import { useState, useRef, useEffect } from 'react';
import { calculateMatch, listVacancies } from '../../services/api';
import './MatchingPanel.css';

/* ─────────────────────────────────────────────────
   Helpers
───────────────────────────────────────────────── */
function safeParseJson(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === 'object' && parsed !== null) return { ok: true, data: parsed };
    return { ok: false, error: 'El JSON debe ser un objeto ({}).' };
  } catch (e) {
    return { ok: false, error: `JSON inválido: ${e.message}` };
  }
}

function scoreColor(score) {
  if (score >= 75) return { ring: '#16a34a', bar: '#22c55e', text: '#15803d', bg: '#f0fdf4' };
  if (score >= 50) return { ring: '#ca8a04', bar: '#facc15', text: '#92400e', bg: '#fefce8' };
  return { ring: '#dc2626', bar: '#f87171', text: '#991b1b', bg: '#fef2f2' };
}

function scoreLabel(score) {
  if (score >= 75) return 'Alta idoneidad';
  if (score >= 50) return 'Idoneidad media';
  if (score >= 25) return 'Idoneidad baja';
  return 'No idóneo';
}

/* Gauge SVG circular */
function ScoreGauge({ score }) {
  const c = scoreColor(score);
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div className="gauge-wrapper" style={{ '--ring-color': c.ring }}>
      <svg viewBox="0 0 130 130" className="gauge-svg" aria-hidden="true">
        {/* Track */}
        <circle cx="65" cy="65" r={r} fill="none" stroke="#e2e8f0" strokeWidth="13" />
        {/* Progress */}
        <circle
          cx="65" cy="65" r={r}
          fill="none"
          stroke={c.bar}
          strokeWidth="13"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 65 65)"
          style={{ transition: 'stroke-dasharray 1s cubic-bezier(.4,0,.2,1)' }}
        />
      </svg>
      <div className="gauge-label" style={{ color: c.text }}>
        <span className="gauge-score">{score}</span>
        <span className="gauge-pct">%</span>
        <span className="gauge-tag" style={{ color: c.text }}>{scoreLabel(score)}</span>
      </div>
    </div>
  );
}

/* Barra de desglose por eje */
function BreakdownBar({ label, value, max, color }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="breakdown-row">
      <div className="breakdown-meta">
        <span className="breakdown-label">{label}</span>
        <span className="breakdown-pts">
          <strong>{value}</strong>/{max} pts
        </span>
      </div>
      <div className="breakdown-track">
        <div
          className="breakdown-fill"
          style={{
            width: `${pct}%`,
            background: color,
            transition: 'width 1.1s cubic-bezier(.4,0,.2,1)',
          }}
        />
      </div>
    </div>
  );
}

const REQUIREMENT_CATEGORIES = {
  habilidades: 'Habilidad',
  experiencia: 'Experiencia',
  educacion: 'Educación',
  idiomas: 'Idioma',
};

function RequirementList({ title, items, status }) {
  return (
    <section className={`requirement-group requirement-group-${status}`}>
      <h4 className="requirement-group-title">
        {title} <span>{items.length}</span>
      </h4>
      {items.length ? (
        <ul className="requirement-list">
          {items.map((item) => (
            <li key={`${item.category}-${item.requirement}`}>
              <strong>
                <span className="requirement-category">
                  {REQUIREMENT_CATEGORIES[item.category] || item.category}
                </span>
                {item.requirement}
              </strong>
              <span className="requirement-evidence">{item.evidence}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="requirement-empty">No hay requisitos en esta categoría.</p>
      )}
    </section>
  );
}

/* TextArea con JSON con hint de error inline */
function JsonTextarea({ id, label, hint, value, onChange, error, rows = 10 }) {
  return (
    <div className="json-field">
      <label htmlFor={id} className="json-label">{label}</label>
      <p className="json-hint">{hint}</p>
      <textarea
        id={id}
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        className={`json-textarea${error ? ' is-error' : ''}`}
        aria-describedby={error ? `${id}-err` : undefined}
      />
      {error && (
        <p id={`${id}-err`} className="json-error" role="alert">
          <span aria-hidden="true">⚠ </span>{error}
        </p>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────
   Componente principal
───────────────────────────────────────────────── */
export default function MatchingPanel() {
  const [candidateRaw, setCandidateRaw] = useState('');
  const [vacancyRaw, setVacancyRaw] = useState('');
  const [candidateErr, setCandidateErr] = useState('');
  const [vacancyErr, setVacancyErr] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [apiError, setApiError] = useState('');
  const [vacancies, setVacancies] = useState([]);
  const [selectedVacancyId, setSelectedVacancyId] = useState('');
  const [vacanciesError, setVacanciesError] = useState('');
  const resultRef = useRef(null);

  useEffect(() => {
    let active = true;
    listVacancies()
      .then((data) => {
        if (active) setVacancies(data.filter((vacancy) => vacancy.structured_requirements));
      })
      .catch((error) => {
        if (active) setVacanciesError(error.message);
      });
    return () => {
      active = false;
    };
  }, []);

  const validate = () => {
    let valid = true;
    const cp = safeParseJson(candidateRaw);
    const vp = safeParseJson(vacancyRaw);

    if (!candidateRaw.trim()) {
      setCandidateErr('Este campo es obligatorio.');
      valid = false;
    } else if (!cp.ok) {
      setCandidateErr(cp.error);
      valid = false;
    } else {
      setCandidateErr('');
    }

    if (!vacancyRaw.trim()) {
      setVacancyErr('Este campo es obligatorio.');
      valid = false;
    } else if (!vp.ok) {
      setVacancyErr(vp.error);
      valid = false;
    } else {
      setVacancyErr('');
    }

    if (!valid) return null;
    return { candidate: cp.data, vacancy: vp.data };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const parsed = validate();
    if (!parsed) return;

    setLoading(true);
    setResult(null);
    setApiError('');

    try {
      const data = await calculateMatch(
        parsed.candidate,
        parsed.vacancy,
        selectedVacancyId || undefined,
      );
      setResult(data);
      // Scroll suave al resultado
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
    } catch (err) {
      setApiError(err.message || 'Error inesperado al conectar con el Matching Engine.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCandidateRaw('');
    setVacancyRaw('');
    setCandidateErr('');
    setVacancyErr('');
    setResult(null);
    setApiError('');
    setSelectedVacancyId('');
  };

  const colors = result ? scoreColor(result.score) : null;

  return (
    <div className="matching-root">

      {/* ── Formulario de entrada ── */}
      <form onSubmit={handleSubmit} noValidate>
        <div className="matching-inputs">
          <JsonTextarea
            id="candidate-json"
            label="Perfil del Candidato (JSON)"
            hint="Pega el perfil estructurado del candidato generado al analizar su hoja de vida."
            value={candidateRaw}
            onChange={setCandidateRaw}
            error={candidateErr}
          />
          <JsonTextarea
            id="vacancy-json"
            label="Requisitos de la Vacante (JSON)"
            hint="Pega los requisitos estructurados generados al registrar la vacante."
            value={vacancyRaw}
            onChange={(value) => {
              setVacancyRaw(value);
              setSelectedVacancyId('');
            }}
            error={vacancyErr}
          />
        </div>
        <div className="json-field matching-vacancy-link">
          <label htmlFor="matching-vacancy" className="json-label">
            Asociar resultado al ranking (opcional)
          </label>
          <p className="json-hint">
            Selecciona una vacante procesada para guardar el resultado en su ranking.
          </p>
          <select
            id="matching-vacancy"
            className="json-textarea"
            value={selectedVacancyId}
            onChange={(event) => {
              const vacancy = vacancies.find((item) => String(item.id) === event.target.value);
              setSelectedVacancyId(event.target.value);
              if (vacancy?.structured_requirements) {
                setVacancyRaw(JSON.stringify(vacancy.structured_requirements, null, 2));
                setVacancyErr('');
              }
            }}
          >
            <option value="">Sin asociar (solo calcular)</option>
            {vacancies.map((vacancy) => (
              <option key={vacancy.id} value={vacancy.id}>{vacancy.title}</option>
            ))}
          </select>
          {vacanciesError && <p className="json-error" role="alert">{vacanciesError}</p>}
        </div>

        {/* Error de API */}
        {apiError && (
          <div className="match-api-error" role="alert">
            <svg className="match-api-error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="match-api-error-title">Error en el Matching Engine</p>
              <p className="match-api-error-msg">{apiError}</p>
            </div>
            <button type="button" onClick={() => setApiError('')} className="match-api-error-close" aria-label="Cerrar">×</button>
          </div>
        )}

        {/* Acciones */}
        <div className="match-actions">
          {(candidateRaw || vacancyRaw) && !loading && (
            <button type="button" onClick={handleReset} className="match-btn-ghost">
              Limpiar todo
            </button>
          )}
          <button
            type="submit"
            disabled={loading || (!candidateRaw.trim() && !vacancyRaw.trim())}
            className="match-btn-primary"
            id="calculate-match-btn"
          >
            {loading ? (
              <>
                <svg className="match-spinner" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" strokeDasharray="40 60" strokeLinecap="round" />
                </svg>
                Calculando score...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Calcular Score de Idoneidad
              </>
            )}
          </button>
        </div>
      </form>

      {/* ── Panel de resultados ── */}
      {result && (
        <section ref={resultRef} className="match-result" aria-live="polite" aria-label="Resultado del matching"
          style={{ '--result-bg': colors.bg, '--result-border': colors.ring + '40' }}>

          <div className="match-result-header">
            <div>
              <p className="match-result-eyebrow">MATCHING ENGINE · Evaluación</p>
              <h3 className="match-result-title">Resultado de Idoneidad</h3>
            </div>
            <span className="match-result-badge" style={{ background: colors.bg, color: colors.text, borderColor: colors.ring + '60' }}>
              IA · Gemini
            </span>
          </div>

          {/* Score + desglose */}
          <div className="match-result-body">

            {/* Gauge */}
            <div className="match-gauge-col">
              <ScoreGauge score={result.score} />
              <p className="match-score-note" style={{ color: colors.text }}>
                Score de idoneidad global
              </p>
            </div>

            {/* Desglose por categoría */}
            <div className="match-breakdown-col">
              <p className="match-breakdown-title">Desglose por categoría</p>
              <BreakdownBar
                label="Habilidades"
                value={result.breakdown?.habilidades?.score ?? 0}
                max={40}
                color="#8b5cf6"
              />
              <BreakdownBar
                label="Experiencia"
                value={result.breakdown?.experiencia?.score ?? 0}
                max={40}
                color="#3b82f6"
              />
              <BreakdownBar
                label="Educación"
                value={result.breakdown?.educacion?.score ?? 0}
                max={10}
                color="#0ea5e9"
              />
              <BreakdownBar
                label="Idiomas"
                value={result.breakdown?.idiomas?.score ?? 0}
                max={10}
                color="#0ea5e9"
              />
            </div>
          </div>

          <div className="match-requirements">
            <p className="match-breakdown-title">Requisitos y evidencia del CV</p>
            <div className="requirements-grid">
              <RequirementList
                title="Cumplidos"
                items={result.requirements_met || []}
                status="met"
              />
              <RequirementList
                title="Parcialmente cumplidos"
                items={result.requirements_partial || []}
                status="partial"
              />
              <RequirementList
                title="Faltantes"
                items={result.requirements_missing || []}
                status="missing"
              />
            </div>
          </div>

          {/* Justificación narrativa */}
          <div className="match-justification">
            <p className="match-justification-title">
              <svg className="match-justification-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Justificación del evaluador
            </p>
            <p className="match-justification-text">{result.justification}</p>
          </div>

          {/* CTA nuevo cálculo */}
          <div className="match-result-footer">
            <button type="button" onClick={handleReset} className="match-btn-ghost match-btn-sm">
              Realizar nuevo cálculo
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
