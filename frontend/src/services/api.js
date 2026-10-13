const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Registra una nueva vacante en el sistema (HU-05).
 * Realiza una petición POST al backend con el título y la descripción libre.
 *
 * @param {string} title - Título del cargo o vacante.
 * @param {string} rawDescription - Descripción textual completa de la oferta.
 * @returns {Promise<Object>} Datos de la vacante creada devueltos por el backend.
 */
export async function createVacancy(title, rawDescription) {
  if (!title || !title.trim()) {
    throw new Error('El título de la vacante es obligatorio.');
  }

  if (!rawDescription || !rawDescription.trim()) {
    throw new Error('La descripción de la vacante es obligatoria.');
  }

  const response = await fetch(`${API_BASE_URL}/vacancies/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      title: title.trim(),
      raw_description: rawDescription.trim(),
    }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorDetail =
      (typeof data?.detail === 'string' && data.detail) ||
      (Array.isArray(data?.detail) && data.detail.map((d) => d.msg || d).join(', ')) ||
      `Error ${response.status}: No fue posible registrar la vacante.`;

    throw new Error(errorDetail);
  }

  return data;
}

/**
 * Calcula el score y devuelve desglose y evidencia de requisitos (HU-07 / HU-08).
 * Llama al Matching Engine del backend que usa Gemini con temperature=0.
 *
 * @param {Object} candidateData - Perfil estructurado del candidato (salida de HU-04).
 * @param {Object} vacancyData   - Requisitos estructurados de la vacante (salida de HU-06).
 * @returns {Promise<{score: number, justification: string, breakdown: Object, requirements_met: Array, requirements_partial: Array, requirements_missing: Array}>}
 */
export async function calculateMatch(candidateData, vacancyData, vacancyId) {
  if (!candidateData || typeof candidateData !== 'object') {
    throw new Error('El perfil del candidato es obligatorio y debe ser un objeto JSON.');
  }
  if (!vacancyData || typeof vacancyData !== 'object') {
    throw new Error('Los datos de la vacante son obligatorios y deben ser un objeto JSON.');
  }

  const response = await fetch(`${API_BASE_URL}/match/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      candidate_data: candidateData,
      vacancy_data: vacancyData,
      ...(vacancyId ? { vacancy_id: vacancyId } : {}),
    }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorDetail =
      (typeof data?.detail === 'string' && data.detail) ||
      (Array.isArray(data?.detail) && data.detail.map((d) => d.msg || d).join(', ')) ||
      `Error ${response.status}: No fue posible calcular el score de idoneidad.`;

    throw new Error(errorDetail);
  }

  return data;
}

export async function listVacancies() {
  const response = await fetch(`${API_BASE_URL}/vacancies/`, {
    headers: { Accept: 'application/json' },
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible cargar las vacantes.`,
    );
  }

  return data;
}

export async function getVacancyRanking(vacancyId, filters = {}) {
  if (!vacancyId) {
    throw new Error('Debes seleccionar una vacante para consultar el ranking.');
  }

  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  });
  const suffix = query.size ? `?${query.toString()}` : '';
  const response = await fetch(
    `${API_BASE_URL}/ranking/${encodeURIComponent(vacancyId)}${suffix}`,
    { headers: { Accept: 'application/json' } },
  );
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible cargar el ranking.`,
    );
  }

  return data;
}

export async function getCandidateDetail(candidateId, vacancyId) {
  if (!candidateId || !vacancyId) {
    throw new Error('Se requiere el candidato y la vacante para consultar el detalle.');
  }

  const query = new URLSearchParams({ vacancy_id: vacancyId });
  const response = await fetch(
    `${API_BASE_URL}/candidates/${encodeURIComponent(candidateId)}/detail?${query}`,
    { headers: { Accept: 'application/json' } },
  );
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible cargar el detalle del candidato.`,
    );
  }

  return data;
}

export default {
  createVacancy,
  calculateMatch,
  listVacancies,
  getVacancyRanking,
  getCandidateDetail,
};
