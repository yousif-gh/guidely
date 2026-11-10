import { useState } from 'react'
import SourceList from '../components/SourceList'

const SERVICE_DOWN = 'The AI service is unavailable right now. Please try again shortly.'
const ERROR_MESSAGES = {
  404: "I couldn't find an answer in the documents. Try different words.",
  409: 'Documents have not been indexed yet.',
  422: 'Please enter a question.',
  429: 'Too many requests. Please wait a moment and try again.',
  502: SERVICE_DOWN,
  503: SERVICE_DOWN,
  504: 'The AI service took too long. Please try again.',
}
const UNKNOWN_ERROR = 'Something went wrong. Please try again.'

export default function SearchPage() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (response.ok) {
        setResult(await response.json())
      } else {
        setError(ERROR_MESSAGES[response.status] ?? UNKNOWN_ERROR)
      }
    } catch {
      setError('Could not reach the server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <form className="search" onSubmit={handleSubmit}>
        <label htmlFor="question">Your question</label>
        <div className="search-row">
          <input
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="How long does a refund take?"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Searching…' : 'Ask'}
          </button>
        </div>
      </form>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {result && (
        <article>
          <h2>Answer</h2>
          <p className="answer">{result.answer}</p>
          <SourceList sources={result.sources} />
        </article>
      )}
    </>
  )
}
