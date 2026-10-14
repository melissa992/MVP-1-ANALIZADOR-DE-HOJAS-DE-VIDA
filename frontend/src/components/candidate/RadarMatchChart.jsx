import './RadarMatchChart.css';

const DIMENSIONS = [
  { key: 'habilidades', label: 'Hard skills', angle: -90 },
  { key: 'experiencia', label: 'Experiencia', angle: 0 },
  { key: 'educacion', label: 'Educación', angle: 90 },
  { key: 'idiomas', label: 'Idiomas', angle: 180 },
];

const CENTER = { x: 180, y: 145 };
const RADIUS = 82;

function pointAt(angle, radius) {
  const radians = (angle * Math.PI) / 180;
  return {
    x: CENTER.x + Math.cos(radians) * radius,
    y: CENTER.y + Math.sin(radians) * radius,
  };
}

function toPoints(points) {
  return points.map(({ x, y }) => `${x},${y}`).join(' ');
}

export default function RadarMatchChart({ breakdown }) {
  const metrics = DIMENSIONS.map((dimension) => {
    const category = breakdown?.[dimension.key];
    const score = category?.score;
    const maxScore = category?.max_score;

    if (
      !Number.isFinite(score) ||
      !Number.isFinite(maxScore) ||
      maxScore <= 0 ||
      score < 0 ||
      score > maxScore
    ) {
      return null;
    }

    return {
      ...dimension,
      percentage: Math.round((score / maxScore) * 100),
    };
  });

  if (metrics.some((metric) => metric === null)) {
    return (
      <p className="radar-match-unavailable" role="status">
        No hay suficientes métricas para mostrar el gráfico de competencias.
      </p>
    );
  }

  const dataPoints = metrics.map((metric) =>
    pointAt(metric.angle, (metric.percentage / 100) * RADIUS),
  );

  return (
    <div className="radar-match-chart">
      <div className="radar-match-visual">
        <svg viewBox="0 0 360 290" role="img" aria-label="Gráfico radar de competencias del candidato">
          {[25, 50, 75, 100].map((level) => (
            <polygon
              key={level}
              className="radar-match-grid"
              points={toPoints(DIMENSIONS.map(({ angle }) => pointAt(angle, (level / 100) * RADIUS)))}
            />
          ))}
          {DIMENSIONS.map(({ key, angle }) => {
            const endpoint = pointAt(angle, RADIUS);
            return (
              <line
                key={key}
                className="radar-match-axis"
                x1={CENTER.x}
                y1={CENTER.y}
                x2={endpoint.x}
                y2={endpoint.y}
              />
            );
          })}
          <polygon className="radar-match-area" points={toPoints(dataPoints)} />
          {dataPoints.map(({ x, y }, index) => (
            <circle
              className="radar-match-point"
              key={metrics[index].key}
              cx={x}
              cy={y}
              r="4"
            />
          ))}
          {metrics.map(({ key, label, angle }) => {
            const position = pointAt(angle, RADIUS + 34);
            return (
              <text
                key={key}
                className="radar-match-label"
                x={position.x}
                y={position.y}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {label}
              </text>
            );
          })}
        </svg>
      </div>
      <ul className="radar-match-legend" aria-label="Puntajes por competencia">
        {metrics.map(({ key, label, percentage }) => (
          <li key={key}>
            <span>{label}</span>
            <strong>{percentage}%</strong>
          </li>
        ))}
      </ul>
      <p className="radar-match-note">
        Cada eje muestra el puntaje obtenido como porcentaje de su máximo.
      </p>
    </div>
  );
}
