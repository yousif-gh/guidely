export default function SourceList({ sources }) {
  return (
    <section>
      <h2>Sources</h2>
      {sources.map((source, index) => (
        <details className="source" key={`${source.source}-${index}`}>
          <summary>
            [{index + 1}] {source.source}
            <span className="score">match {source.score.toFixed(2)}</span>
          </summary>
          <p>{source.text}</p>
        </details>
      ))}
    </section>
  )
}
