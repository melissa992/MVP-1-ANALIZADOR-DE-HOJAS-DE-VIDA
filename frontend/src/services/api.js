export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const ACCESS_TOKEN_KEY = 'cv-match-access-token';

export function getAccessToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function storeAccessToken(token) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (response.status === 401) {
    clearAccessToken();
    window.dispatchEvent(new Event('auth-expired'));
  }
  return response;
}

export async function login(email, password) {
  const response = await apiFetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible iniciar sesión.`,
    );
  }

  storeAccessToken(data.access_token);
  return data;
}

export async function getCurrentUser() {
  const response = await apiFetch('/me', { headers: { Accept: 'application/json' } });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: La sesión ya no es válida.`,
    );
  }
  return data;
}

export async function logout() {
  try {
    await apiFetch('/logout', { method: 'POST' });
  } finally {
    clearAccessToken();
  }
}

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

  const response = await apiFetch('/vacancies/', {
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

  const response = await apiFetch('/match/', {
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
  const response = await apiFetch('/vacancies/', {
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
  const response = await apiFetch(
    `/ranking/${encodeURIComponent(vacancyId)}${suffix}`,
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
  const response = await apiFetch(
    `/candidates/${encodeURIComponent(candidateId)}/detail?${query}`,
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

export async function generateInterviewGuide(candidateId, vacancyId) {
  if (!candidateId || !vacancyId) {
    throw new Error('Se requiere el candidato y la vacante para generar la guía.');
  }

  const response = await apiFetch('/candidates/generate-interview-questions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      candidate_id: candidateId,
      vacancy_id: vacancyId,
    }),
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible generar la guía de entrevista.`,
    );
  }

  return data;
}

export async function startVoiceInterview(candidateId, vacancyId) {
  const response = await apiFetch('/interview/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ candidate_id: candidateId, vacancy_id: vacancyId }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible iniciar la entrevista.`,
    );
  }
  return data;
}

export async function respondToVoiceInterview({
  candidateId,
  vacancyId,
  question,
  objective,
  answer,
}) {
  const response = await apiFetch('/interview/respond', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      candidate_id: candidateId,
      vacancy_id: vacancyId,
      question,
      objective,
      answer,
    }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible evaluar la respuesta.`,
    );
  }
  return data;
}

export async function synthesizeInterviewVoice(text) {
  const response = await apiFetch('/interview/tts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'audio/mpeg',
    },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible generar el audio.`,
    );
  }
  return response.blob();
}

export async function getFileStatus(fileId) {
  const response = await apiFetch(`/status/${encodeURIComponent(fileId)}`, {
    headers: { Accept: 'application/json' },
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible consultar el estado del archivo.`,
    );
  }

  return data;
}

export async function retryFileProcessing(fileId) {
  const response = await apiFetch(`/retry/${encodeURIComponent(fileId)}`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      (typeof data?.detail === 'string' && data.detail) ||
      `Error ${response.status}: No fue posible reintentar el procesamiento.`,
    );
  }

  return data;
}

export default {
  apiFetch,
  login,
  getCurrentUser,
  logout,
  createVacancy,
  calculateMatch,
  listVacancies,
  getVacancyRanking,
  getCandidateDetail,
  generateInterviewGuide,
  getFileStatus,
  retryFileProcessing,
};
