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

export default {
  createVacancy,
};
