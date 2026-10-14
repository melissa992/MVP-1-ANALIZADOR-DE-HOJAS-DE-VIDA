import { useState } from 'react';
import { createVacancy } from '../services/api';

/**
 * Componente para el registro de vacantes laborales (HU-05).
 * Permite a los reclutadores registrar el título y pegar la descripción en texto libre.
 *
 * @param {Object} props
 * @param {Function} [props.onSuccess] - Callback opcional ejecutado al crear exitosamente la vacante.
 */
export default function VacancyForm({ onSuccess }) {
  const [title, setTitle] = useState('');
  const [rawDescription, setRawDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [createdVacancy, setCreatedVacancy] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const cleanTitle = title.trim();
    const cleanDescription = rawDescription.trim();

    if (!cleanTitle) {
      setErrorMsg('Por favor ingresa un título para la vacante.');
      return;
    }

    if (!cleanDescription) {
      setErrorMsg('Por favor pega o ingresa la descripción de la vacante.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    setCreatedVacancy(null);

    try {
      const result = await createVacancy(cleanTitle, cleanDescription);
      setCreatedVacancy(result);

      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess(result);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Ocurrió un error inesperado al registrar la vacante.');
    } finally {
      setLoading(false);
    }
  };

  const handleDismissAlerts = () => {
    setErrorMsg('');
    setCreatedVacancy(null);
  };

  const handleClearForm = () => {
    setTitle('');
    setRawDescription('');
    setErrorMsg('');
    setCreatedVacancy(null);
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Contenedor principal de la tarjeta */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden transition-all duration-200">
        {/* Cabecera del formulario */}
        <div className="px-6 py-6 sm:px-8 border-b border-slate-100 bg-gradient-to-r from-emerald-50/50 via-slate-50/30 to-white">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-100/70 text-[#274b40] text-xs font-semibold tracking-wide uppercase mb-2">
                <span className="w-2 h-2 rounded-full bg-[#315e50] animate-pulse"></span>
                Módulo de Reclutamiento
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-slate-850 tracking-tight text-[#1c2c26]">
                Registro de Nueva Vacante
              </h2>
              <p className="text-sm text-slate-600 mt-1 max-w-xl">
                Ingresa el título del puesto y pega la oferta laboral completa. El sistema la registrará para su posterior análisis inteligente con IA.
              </p>
            </div>
            <div className="hidden sm:flex flex-col items-end text-xs text-slate-500">
              <span className="font-semibold text-slate-700">Estado inicial</span>
              <span className="inline-flex items-center gap-1.5 mt-0.5 px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200/60 font-medium">
                pending_processing
              </span>
            </div>
          </div>
        </div>

        {/* Mensaje de éxito tras registro */}
        {createdVacancy && (
          <div
            className="mx-6 sm:mx-8 mt-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200/80 text-emerald-950 flex flex-col gap-3 shadow-xs"
            role="status"
            aria-live="polite"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-emerald-900 text-sm">
                    ¡Vacante registrada y estructurada con IA exitosamente!
                  </p>
                  <p className="text-xs text-emerald-800/90 mt-0.5">
                    <strong className="font-medium text-emerald-950">"{createdVacancy.title}"</strong> · Estado: <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-200/80 text-emerald-900">{createdVacancy.status}</span> · ID: <code className="px-1.5 py-0.5 bg-emerald-100/70 rounded text-[11px] font-mono text-emerald-900">{createdVacancy.id}</code>
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleDismissAlerts}
                className="text-xs text-emerald-700 hover:text-emerald-950 underline font-medium self-end sm:self-center cursor-pointer transition-colors"
              >
                Cerrar aviso
              </button>
            </div>

            {/* HU-06: Vista previa de requisitos estructurados por LLM */}
            {createdVacancy.structured_requirements && (
              <div className="mt-2 pt-3 border-t border-emerald-200/70 text-xs text-slate-800 bg-white/70 rounded-lg p-3">
                <div className="font-bold text-emerald-950 mb-2 flex items-center gap-1.5">
                  <span>✨ Requisitos estructurados con IA:</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[12px]">
                  <div><span className="font-semibold text-slate-600">Cargo normalizado:</span> {createdVacancy.structured_requirements.cargo || 'No especificado'}</div>
                  <div><span className="font-semibold text-slate-600">Experiencia mínima:</span> {createdVacancy.structured_requirements.anios_experiencia_requeridos} año(s)</div>
                  <div><span className="font-semibold text-slate-600">Nivel de estudios:</span> {createdVacancy.structured_requirements.nivel_estudios || 'No especificado'}</div>
                  <div><span className="font-semibold text-slate-600">Idiomas:</span> {createdVacancy.structured_requirements.idiomas?.length ? createdVacancy.structured_requirements.idiomas.join(', ') : 'No especificado'}</div>
                </div>
                {createdVacancy.structured_requirements.habilidades_clave?.length > 0 && (
                  <div className="mt-2.5">
                    <span className="font-semibold text-slate-600 block mb-1">Habilidades clave extraídas:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {createdVacancy.structured_requirements.habilidades_clave.map((hab, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded bg-emerald-100 text-[#274b40] font-medium text-[11px]">
                          {hab}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Mensaje de error */}
        {errorMsg && (
          <div
            className="mx-6 sm:mx-8 mt-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start justify-between gap-3 shadow-xs"
            role="alert"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-rose-500 text-white flex items-center justify-center shrink-0 mt-0.5">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-rose-900 text-sm">Error en el registro</p>
                <p className="text-xs text-rose-800 mt-0.5">{errorMsg}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setErrorMsg('')}
              className="text-xs text-rose-700 hover:text-rose-950 underline font-medium cursor-pointer"
            >
              Cerrar
            </button>
          </div>
        )}

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
          {/* Campo: Título de la Vacante */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="vacancy-title" className="block text-sm font-semibold text-slate-800">
                Título de la Vacante <span className="text-emerald-700">*</span>
              </label>
              <span className="text-xs text-slate-500">
                {title.length > 0 && `${title.length} caracteres`}
              </span>
            </div>
            <div className="relative">
              <input
                id="vacancy-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ej. Desarrollador Full Stack Senior (Python / React)"
                disabled={loading}
                required
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white text-slate-900 placeholder-slate-400 text-sm transition-all duration-150 focus:border-[#315e50] focus:ring-3 focus:ring-[#315e50]/20 focus:outline-none disabled:bg-slate-50 disabled:cursor-not-allowed"
              />
            </div>
            <p className="text-xs text-slate-500 mt-1.5">
              Identifica el rol o posición claramente para vincular los perfiles de los postulantes.
            </p>
          </div>

          {/* Campo: Descripción de la Vacante */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="vacancy-description" className="block text-sm font-semibold text-slate-800">
                Descripción de la Vacante <span className="text-emerald-700">*</span>
              </label>
              <span className="text-xs text-slate-500">
                {rawDescription.trim() ? `${rawDescription.trim().split(/\s+/).length} palabras` : 'Texto libre'}
              </span>
            </div>
            <div className="relative">
              <textarea
                id="vacancy-description"
                rows={9}
                value={rawDescription}
                onChange={(e) => setRawDescription(e.target.value)}
                placeholder="Pega aquí el texto completo de la oferta de empleo:&#10;• Requisitos técnicos y habilidades blandas&#10;• Experiencia requerida (años, sectores, tecnologías)&#10;• Responsabilidades y objetivos del cargo&#10;• Idiomas y condiciones laborales..."
                disabled={loading}
                required
                className="w-full px-4 py-3.5 rounded-xl border border-slate-300 bg-white text-slate-900 placeholder-slate-400 text-sm font-sans leading-relaxed transition-all duration-150 focus:border-[#315e50] focus:ring-3 focus:ring-[#315e50]/20 focus:outline-none disabled:bg-slate-50 disabled:cursor-not-allowed resize-y min-h-[180px]"
              />
            </div>
            <div className="flex items-center justify-between text-xs text-slate-500 mt-1.5">
              <span>Acepta texto libre sin necesidad de formateo previo.</span>
              <span>Requerido para análisis semántico</span>
            </div>
          </div>

          {/* Barra de acciones y botón de envío */}
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-t border-slate-100">
            <div className="text-xs text-slate-500">
              Todos los campos marcados con <span className="text-emerald-700 font-bold">*</span> son requeridos.
            </div>

            <div className="flex items-center gap-3">
              {(title || rawDescription) && !loading && (
                <button
                  type="button"
                  onClick={handleClearForm}
                  disabled={loading}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Limpiar campos
                </button>
              )}

              <button
                type="submit"
                disabled={loading || !title.trim() || !rawDescription.trim()}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-[#315e50] hover:bg-[#274b40] active:bg-[#1e3c33] text-white text-sm font-semibold tracking-wide shadow-sm hover:shadow transition-all duration-150 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
              >
                {loading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    <span>Registrando vacante...</span>
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                    <span>Registrar Vacante</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
