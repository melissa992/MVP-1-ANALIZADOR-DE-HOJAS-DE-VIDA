import { useEffect, useRef, useState } from 'react';
import {
  respondToVoiceInterview,
  startVoiceInterview,
  synthesizeInterviewVoice,
} from '../../services/api';
import './VoiceInterviewModal.css';

const stateLabels = {
  setup: 'Preparada para comenzar',
  loading: 'Preparando preguntas personalizadas...',
  speaking: 'El entrevistador virtual está hablando...',
  ready: 'Tu turno. Presiona el micrófono para responder.',
  listening: 'Escuchando tu respuesta...',
  thinking: 'Analizando competencias...',
  report: 'Simulación finalizada',
};

function VoiceInterviewModal({ candidateId, vacancyId, onClose }) {
  const [session, setSession] = useState(null);
  const [phase, setPhase] = useState('setup');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [turns, setTurns] = useState([]);
  const [muted, setMuted] = useState(false);
  const [manualAnswer, setManualAnswer] = useState('');
  const [error, setError] = useState('');
  const [audioNotice, setAudioNotice] = useState('');
  const audioRef = useRef(null);
  const audioUrlRef = useRef('');
  const lastSpokenTextRef = useRef('');
  const recognitionRef = useRef(null);
  const transcriptRef = useRef('');
  const submitOnEndRef = useRef(false);
  const disposedRef = useRef(false);
  const finishedRef = useRef(false);

  const currentQuestion = session?.questions[questionIndex];
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const supportsSpeechRecognition = Boolean(SpeechRecognition);
  const completed = turns.length;
  const averageScore = completed
    ? Math.round(turns.reduce((sum, turn) => sum + turn.score, 0) / completed)
    : 0;

  useEffect(() => {
    disposedRef.current = false;
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      disposedRef.current = true;
      window.removeEventListener('keydown', closeOnEscape);
      const recognition = recognitionRef.current;
      recognitionRef.current = null;
      recognition?.abort();
      audioRef.current?.pause();
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, [onClose]);

  const stopAudio = () => {
    audioRef.current?.pause();
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    audioUrlRef.current = '';
    audioRef.current = null;
  };

  const speak = async (text, afterSpeaking = 'ready') => {
    lastSpokenTextRef.current = text;
    setError('');
    setAudioNotice('');
    setPhase('speaking');
    stopAudio();
    try {
      const audioBlob = await synthesizeInterviewVoice(text);
      if (disposedRef.current) return;
      const audioUrl = URL.createObjectURL(audioBlob);
      audioUrlRef.current = audioUrl;
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      audio.onended = () => {
        setPhase(afterSpeaking);
        URL.revokeObjectURL(audioUrl);
        audioUrlRef.current = '';
        audioRef.current = null;
      };
      audio.onerror = () => {
        setPhase(afterSpeaking);
        URL.revokeObjectURL(audioUrl);
        audioUrlRef.current = '';
        audioRef.current = null;
        setAudioNotice('No se pudo reproducir el audio. Puedes continuar leyendo en pantalla.');
      };
      try {
        await audio.play();
      } catch {
        setPhase(afterSpeaking);
        setAudioNotice('El navegador bloqueó la reproducción automática. Usa «Reproducir voz» para escuchar.');
      }
    } catch (audioError) {
      setPhase(afterSpeaking);
      setAudioNotice(audioError.message);
    }
  };

  const beginInterview = async () => {
    setPhase('loading');
    setError('');
    try {
      const interview = await startVoiceInterview(candidateId, vacancyId);
      if (disposedRef.current) return;
      setSession(interview);
      await speak(interview.opening_text);
    } catch (startError) {
      setError(startError.message);
      setPhase('setup');
    }
  };

  const submitAnswer = async (answerText) => {
    const answer = answerText.trim();
    if (!currentQuestion || phase === 'thinking') return;
    if (!answer) {
      setError('No se detectó una respuesta. Intenta hablar de nuevo o escríbela.');
      setPhase('ready');
      return;
    }
    setPhase('thinking');
    setError('');
    setAudioNotice('');
    try {
      const evaluation = await respondToVoiceInterview({
        candidateId,
        vacancyId,
        question: currentQuestion.question,
        objective: currentQuestion.objective,
        answer,
      });
      const updatedTurns = [
        ...turns,
        { question: currentQuestion.question, answer, ...evaluation },
      ];
      setTurns(updatedTurns);
      setTranscript('');
      transcriptRef.current = '';
      setManualAnswer('');

      if (finishedRef.current) {
        setPhase('report');
        return;
      }
      const nextIndex = questionIndex + 1;
      if (nextIndex >= session.questions.length) {
        await speak(evaluation.feedback, 'report');
        return;
      }
      setQuestionIndex(nextIndex);
      const nextQuestion = session.questions[nextIndex];
      await speak(
        `${evaluation.feedback} Siguiente pregunta: ${nextQuestion.question}`,
      );
    } catch (answerError) {
      setError(answerError.message);
      setPhase('ready');
    }
  };

  const startListening = () => {
    if (muted || !supportsSpeechRecognition || phase === 'thinking') return;
    setError('');
    setAudioNotice('');
    transcriptRef.current = '';
    setTranscript('');
    submitOnEndRef.current = false;
    const recognition = new SpeechRecognition();
    recognition.lang = 'es-CO';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let fullTranscript = '';
      for (let index = 0; index < event.results.length; index += 1) {
        fullTranscript += event.results[index][0].transcript;
      }
      transcriptRef.current = fullTranscript.trim();
      setTranscript(transcriptRef.current);
    };
    recognition.onerror = (event) => {
      if (recognitionRef.current !== recognition) return;
      if (event.error !== 'aborted' && event.error !== 'no-speech') {
        setError(
          event.error === 'not-allowed'
            ? 'Permite el acceso al micrófono en tu navegador para responder por voz.'
            : 'No fue posible reconocer la voz. Puedes escribir tu respuesta.',
        );
      }
      setPhase('ready');
    };
    recognition.onend = () => {
      if (recognitionRef.current !== recognition) return;
      recognitionRef.current = null;
      if (submitOnEndRef.current) {
        submitOnEndRef.current = false;
        void submitAnswer(transcriptRef.current);
      } else {
        setPhase((current) => (current === 'listening' ? 'ready' : current));
      }
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setPhase('listening');
    } catch {
      setError('No se pudo activar el micrófono. Puedes escribir tu respuesta.');
      setPhase('ready');
    }
  };

  const stopListening = () => {
    if (!recognitionRef.current) return;
    submitOnEndRef.current = true;
    recognitionRef.current.stop();
  };

  const toggleMute = () => {
    if (!muted && recognitionRef.current) {
      submitOnEndRef.current = false;
      const recognition = recognitionRef.current;
      recognitionRef.current = null;
      recognition.abort();
      setPhase('ready');
    }
    setMuted((current) => !current);
  };

  const finishInterview = () => {
    finishedRef.current = true;
    if (recognitionRef.current) {
      submitOnEndRef.current = false;
      const recognition = recognitionRef.current;
      recognitionRef.current = null;
      recognition.abort();
    }
    stopAudio();
    setPhase('report');
  };

  const statusLabel = stateLabels[phase] || stateLabels.ready;

  return (
    <div className="voice-interview-backdrop" onClick={onClose}>
      <section
        className="voice-interview-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-interview-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="voice-interview-header">
          <div>
            <p className="voice-interview-eyebrow">ELEVENLABS · GEMINI</p>
            <h2 id="voice-interview-title">Simulador de Entrevista IA</h2>
          </div>
          <button type="button" className="voice-close-button" onClick={onClose} aria-label="Cerrar simulador">
            ×
          </button>
        </header>

        {phase === 'report' ? (
          <div className="voice-report">
            <div className="voice-report-score">
              <span>{averageScore}</span>
              <small>de 100</small>
            </div>
            <h3>Reporte de entrevista</h3>
            <p className="voice-report-summary">
              {completed
                ? `Evaluación promedio de ${completed} respuesta${completed === 1 ? '' : 's'} para ${session?.vacancy_title}.`
                : 'La entrevista finalizó antes de registrar respuestas.'}
            </p>
            {turns.length > 0 && (
              <>
                <div className="voice-score-bars" aria-label="Puntaje por respuesta">
                  {turns.map((turn, index) => (
                    <div className="voice-score-row" key={`${index}-${turn.question}`}>
                      <span>Respuesta {index + 1}</span>
                      <div><i style={{ width: `${turn.score}%` }} /></div>
                      <strong>{turn.score}</strong>
                    </div>
                  ))}
                </div>
                <h4>Radar de evaluación</h4>
                <div className="voice-radar-wrap">
                  <svg
                    className="voice-radar-chart"
                    viewBox="0 0 220 220"
                    role="img"
                    aria-label={`Radar de evaluación con promedio de ${averageScore} puntos`}
                  >
                    {[25, 50, 75, 100].map((scale) => (
                      <circle key={scale} cx="110" cy="110" r={scale * 0.78} />
                    ))}
                    {turns.map((turn, index) => {
                      const angle = ((index / Math.max(turns.length, 3)) * Math.PI * 2) - Math.PI / 2;
                      const x = 110 + (Math.cos(angle) * 78);
                      const y = 110 + (Math.sin(angle) * 78);
                      return (
                        <g key={`${index}-${turn.question}`}>
                          <line x1="110" y1="110" x2={x} y2={y} />
                          <text x={110 + (Math.cos(angle) * 98)} y={110 + (Math.sin(angle) * 98)}>
                            {index + 1}
                          </text>
                        </g>
                      );
                    })}
                    {turns.length > 1 && (
                      <polygon
                        points={turns.map((turn, index) => {
                          const angle = ((index / Math.max(turns.length, 3)) * Math.PI * 2) - Math.PI / 2;
                          const radius = (turn.score / 100) * 78;
                          return `${110 + (Math.cos(angle) * radius)},${110 + (Math.sin(angle) * radius)}`;
                        }).join(' ')}
                      />
                    )}
                  </svg>
                  <div className="voice-radar-legend">
                    {turns.map((turn, index) => (
                      <span key={`${index}-${turn.question}`}>
                        <i>{index + 1}</i> {turn.score} pts
                      </span>
                    ))}
                  </div>
                </div>
                <h4>Transcripción</h4>
                <div className="voice-transcript-list">
                  {turns.map((turn, index) => (
                    <article key={`${index}-${turn.question}`}>
                      <strong>{index + 1}. {turn.question}</strong>
                      <p>{turn.answer}</p>
                      <span>{turn.feedback}</span>
                    </article>
                  ))}
                </div>
              </>
            )}
            <button type="button" className="voice-primary-button" onClick={onClose}>Volver a la ficha</button>
          </div>
        ) : (
          <>
            <div className="voice-interview-body">
              <main className="voice-stage">
                <div className={`voice-orb voice-orb-${phase}`} aria-hidden="true">
                  <span /><span /><span />
                </div>
                <p className="voice-live-status" role="status">{statusLabel}</p>
                {phase === 'setup' && (
                  <>
                    <p className="voice-stage-copy">
                      Una conversación guiada y personalizada según el perfil y las brechas de la vacante.
                    </p>
                    <button type="button" className="voice-primary-button" onClick={beginInterview}>
                      <span aria-hidden="true">✦</span> Iniciar simulación
                    </button>
                  </>
                )}
                {phase === 'loading' && <span className="voice-loading-spinner" aria-hidden="true" />}
                {phase === 'speaking' && (
                  <button
                    type="button"
                    className="voice-replay-button"
                    onClick={() => speak(
                      questionIndex === 0 && turns.length === 0
                        ? session.opening_text
                        : currentQuestion?.question || '',
                    )}
                  >
                    Reproducir voz
                  </button>
                )}
                {phase === 'listening' && transcript && (
                  <p className="voice-live-transcript">{transcript}</p>
                )}
                {phase === 'ready' && session && (
                  <div className="voice-response-controls">
                    {supportsSpeechRecognition ? (
                      <button
                        type="button"
                        className={`voice-mic-button ${phase === 'listening' ? 'is-listening' : ''}`}
                        onClick={startListening}
                        disabled={muted}
                        aria-label="Iniciar respuesta por voz"
                      >
                        <span aria-hidden="true">🎙</span>
                      </button>
                    ) : (
                      <p className="voice-stage-copy">
                        El reconocimiento de voz no está disponible en este navegador. Escribe tu respuesta.
                      </p>
                    )}
                    {supportsSpeechRecognition && (
                      <span className="voice-control-hint">
                        {muted ? 'Micrófono silenciado' : 'Presiona para comenzar a hablar'}
                      </span>
                    )}
                    <textarea
                      className="voice-manual-answer"
                      value={manualAnswer}
                      onChange={(event) => setManualAnswer(event.target.value)}
                      placeholder={supportsSpeechRecognition ? 'O escribe tu respuesta...' : 'Escribe tu respuesta...'}
                      rows={3}
                    />
                  </div>
                )}
                {phase === 'listening' && (
                  <button type="button" className="voice-stop-button" onClick={stopListening}>
                    Terminar respuesta
                  </button>
                )}
                {phase === 'thinking' && <span className="voice-loading-spinner" aria-hidden="true" />}
                {phase === 'ready' && session && (
                  <button
                    type="button"
                    className="voice-primary-button"
                    onClick={() => void submitAnswer(manualAnswer)}
                    disabled={!manualAnswer.trim()}
                  >
                    Enviar respuesta
                  </button>
                )}
                {audioNotice && (
                  <div className="voice-audio-notice" role="status">
                    <p>{audioNotice}</p>
                    {session && (
                      <button
                        type="button"
                        onClick={() => speak(lastSpokenTextRef.current)}
                      >
                        Intentar audio de nuevo
                      </button>
                    )}
                  </div>
                )}
                {error && <p className="voice-error" role="alert">{error}</p>}
              </main>

              <aside className="voice-question-panel">
                <div className="voice-question-count">
                  <span>ENTREVISTA EN CURSO</span>
                  {session && <strong>{Math.min(questionIndex + 1, session.questions.length)} / {session.questions.length}</strong>}
                </div>
                <h3>{currentQuestion ? `Pregunta ${questionIndex + 1}` : 'Tu entrevista personalizada'}</h3>
                <p className="voice-question-text">
                  {currentQuestion?.question || 'Las preguntas se adaptarán a los requisitos del cargo y la experiencia del candidato.'}
                </p>
                {currentQuestion && (
                  <div className="voice-objective-card">
                    <span>OBJETIVO DE EVALUACIÓN · {currentQuestion.category.toUpperCase()}</span>
                    <p>{currentQuestion.objective}</p>
                  </div>
                )}
                {session && (
                  <div className="voice-panel-footer">
                    <span>Perfil analizado</span>
                    <strong>{session.candidate_name}</strong>
                    <span>{session.vacancy_title}</span>
                  </div>
                )}
              </aside>
            </div>
            <footer className="voice-interview-footer">
              <button type="button" className="voice-secondary-button" onClick={toggleMute}>
                {muted ? 'Activar micrófono' : 'Silenciar micrófono'}
              </button>
              <span className="voice-privacy-note">El backend recibe la transcripción, no el audio</span>
              <button type="button" className="voice-end-button" onClick={finishInterview}>
                Finalizar entrevista
              </button>
            </footer>
          </>
        )}
      </section>
    </div>
  );
}

export default VoiceInterviewModal;
