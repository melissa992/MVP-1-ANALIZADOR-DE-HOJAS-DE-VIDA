import { useEffect, useState } from 'react';
import { getVacancyRanking, listVacancies } from '../../services/api';
import './RankingDashboard.css';

const SORT_COLUMNS = [
  { key: 'candidate_name', label: 'Nombre' },
  { key: 'score', label: 'Score (%)' },
  { key: 'experience_years', label: 'Años de experiencia' },
];

function MatchBadge({ level, score }) {
  const label = level === 'high' ? 'Alto' : level === 'medium' ? 'Medio' : 'Bajo';
  return (
    <span className={`ranking-match-badge ranking-match-${level}`}>
      {label} · {score}%
    </span>
  );
}

export default function RankingDashboard() {
  const [vacancies, setVacancies] = useState([]);
  const [vacancyId, setVacancyId] = useState('');
  const [ranking, setRanking] = useState(null);
  const [vacanciesLoading, setVacanciesLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [minScore, setMinScore] = useState('0');
  const [maxScore, setMaxScore] = useState('100');
  const [skill, setSkill] = useState('');
  const [sortBy, setSortBy] = useState('score');
  const [order, setOrder] = useState('desc');
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const min = Number(minScore);
  const max = Number(maxScore);
  const filterError = (
    minScore === '' || maxScore === '' ||
    !Number.isInteger(min) || !Number.isInteger(max) ||
    min < 0 || max > 100 || min > max
  ) ? 'El rango debe ser válido y estar entre 0 y 100.' : '';
  const currentRanking = ranking?.vacancy_id === vacancyId ? ranking : null;

  useEffect(() => {
    let active = true;
    listVacancies()
      .then((data) => {
        if (!active) return;
        setVacancies(data);
        const initialVacancy = data.find((vacancy) => vacancy.status === 'processed') || data[0];
        if (initialVacancy) setVacancyId(String(initialVacancy.id));
      })
      .catch((loadError) => {
        if (active) setError(loadError.message);
      })
      .finally(() => {
        if (active) setVacanciesLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!vacancyId) {
      return undefined;
    }
    if (filterError) return undefined;

    let active = true;
    const timeoutId = window.setTimeout(() => {
      setLoading(true);
      setError('');
      getVacancyRanking(vacancyId, {
        min_score: min,
        max_score: max,
        skill,
        sort_by: sortBy,
        order,
      })
        .then((data) => {
          if (active) setRanking(data);
        })
        .catch((loadError) => {
          if (active) {
            setRanking(null);
            setError(loadError.message);
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timeoutId);
    };
  }, [vacancyId, minScore, maxScore, skill, sortBy, order, filterError, min, max]);

  const clearFilters = () => {
    setMinScore('0');
    setMaxScore('100');
    setSkill('');
  };

  const sortByColumn = (column) => {
    if (sortBy === column) {
      setOrder((currentOrder) => (currentOrder === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setOrder('asc');
    }
  };

  return (
    <section className="ranking-dashboard" aria-label="Dashboard de ranking de candidatos">
      <div className="ranking-dashboard-heading">
        <div>
          <p className="ranking-eyebrow">RANKING DE CANDIDATOS · HU-09</p>
          <h2>Comparativo de talento</h2>
          <p>Filtra, ordena y revisa candidatos evaluados para cada vacante.</p>
        </div>
        <label className="ranking-vacancy-field" htmlFor="ranking-vacancy">
          Vacante activa
          <select
            id="ranking-vacancy"
            value={vacancyId}
            onChange={(event) => setVacancyId(event.target.value)}
            disabled={vacanciesLoading || vacancies.length === 0}
          >
            {vacancies.length === 0 && <option value="">No hay vacantes</option>}
            {vacancies.map((vacancy) => (
              <option key={vacancy.id} value={vacancy.id}>
                {vacancy.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="ranking-filters" aria-label="Filtros del ranking">
        <label>
          Score mínimo
          <input
            type="number"
            min="0"
            max="100"
            value={minScore}
            onChange={(event) => setMinScore(event.target.value)}
          />
        </label>
        <label>
          Score máximo
          <input
            type="number"
            min="0"
            max="100"
            value={maxScore}
            onChange={(event) => setMaxScore(event.target.value)}
          />
        </label>
        <label className="ranking-skill-filter">
          Habilidad clave
          <input
            type="search"
            value={skill}
            onChange={(event) => setSkill(event.target.value)}
            placeholder="Ej. Python"
          />
        </label>
        <button type="button" className="ranking-clear-button" onClick={clearFilters}>
          Limpiar
        </button>
      </div>

      {(filterError || error) && <p className="ranking-error" role="alert">{filterError || error}</p>}
      {loading && !filterError && <p className="ranking-status" role="status">Cargando ranking...</p>}

      {!filterError && !error && !loading && !vacanciesLoading && vacancies.length === 0 && (
        <p className="ranking-empty">Registra una vacante para comenzar a consultar rankings.</p>
      )}

      {!filterError && !error && !loading && currentRanking && currentRanking.candidates.length === 0 && (
        <p className="ranking-empty">
          No hay candidatos evaluados que coincidan con estos filtros. Calcula un matching
          asociado a esta vacante para comenzar el ranking.
        </p>
      )}

      {!filterError && !error && currentRanking && currentRanking.candidates.length > 0 && (
        <>
          <p className="ranking-result-count">
            {currentRanking.total_candidates} {currentRanking.total_candidates === 1 ? 'candidato' : 'candidatos'}
          </p>
          <div className="ranking-table-scroll">
            <table className="ranking-table">
              <thead>
                <tr>
                  {SORT_COLUMNS.map((column) => (
                    <th key={column.key} scope="col">
                      <button type="button" onClick={() => sortByColumn(column.key)}>
                        {column.label}
                        {sortBy === column.key && (
                          <span aria-label={order === 'asc' ? 'ascendente' : 'descendente'}>
                            {order === 'asc' ? ' ↑' : ' ↓'}
                          </span>
                        )}
                      </button>
                    </th>
                  ))}
                  <th scope="col">Nivel de match</th>
                  <th scope="col">Habilidades</th>
                  <th scope="col"><span className="visually-hidden">Acciones</span></th>
                </tr>
              </thead>
              <tbody>
                {currentRanking.candidates.map((candidate) => (
                  <tr key={candidate.candidate_id}>
                    <th scope="row">{candidate.candidate_name}</th>
                    <td>{candidate.score}%</td>
                    <td>{candidate.experience_years}</td>
                    <td><MatchBadge level={candidate.match_level} score={candidate.score} /></td>
                    <td>
                      <div className="ranking-skill-pills">
                        {candidate.matching_skills.length
                          ? candidate.matching_skills.map((candidateSkill) => (
                            <span className="ranking-skill-pill" key={candidateSkill}>{candidateSkill}</span>
                          ))
                          : <span className="ranking-no-skills">Sin habilidades coincidentes</span>}
                      </div>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ranking-detail-button"
                        onClick={() => setSelectedCandidate(candidate)}
                      >
                        Ver Detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {selectedCandidate && (
        <div className="ranking-modal-backdrop" onClick={() => setSelectedCandidate(null)}>
          <section
            className="ranking-detail-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ranking-detail-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="ranking-detail-close"
              onClick={() => setSelectedCandidate(null)}
              aria-label="Cerrar detalle"
            >
              ×
            </button>
            <p className="ranking-eyebrow">DETALLE DEL CANDIDATO</p>
            <h2 id="ranking-detail-title">{selectedCandidate.candidate_name}</h2>
            <MatchBadge level={selectedCandidate.match_level} score={selectedCandidate.score} />
            <p>{selectedCandidate.experience_years} años de experiencia</p>
            <h3>Habilidades coincidentes</h3>
            <div className="ranking-skill-pills">
              {selectedCandidate.matching_skills.length
                ? selectedCandidate.matching_skills.map((candidateSkill) => (
                  <span className="ranking-skill-pill" key={candidateSkill}>{candidateSkill}</span>
                ))
                : <span className="ranking-no-skills">Sin habilidades coincidentes</span>}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
