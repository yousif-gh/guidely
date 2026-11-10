import { useEffect, useState } from 'react'

const ERROR_MESSAGES = {
  400: 'That file is empty or is not valid UTF-8 text.',
  413: 'That file is larger than 1 MB.',
  415: 'Only .txt files with a plain name are supported.',
  422: 'Please choose a file.',
}
const UNKNOWN_ERROR = 'Something went wrong. Please try again.'
const LOAD_ERROR = 'Could not load documents. Is the backend running?'

async function fetchDocuments() {
  const response = await fetch('/api/documents')
  if (!response.ok) {
    throw new Error('failed to load documents')
  }
  return response.json()
}

function describeIndex(index) {
  const skipped = index.skipped.length ? ` Skipped: ${index.skipped.join(' ')}` : ''
  return `Indexed ${index.chunks} chunks, ${index.cache_hits} already cached.${skipped}`
}

export default function AdminPage() {
  const [documents, setDocuments] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchDocuments().then(setDocuments).catch(() => setError(LOAD_ERROR))
  }, [])

  async function send(url, options, getIndex) {
    setBusy(true)
    setMessage('')
    setError('')
    try {
      const response = await fetch(url, { method: 'POST', ...options })
      if (!response.ok) {
        setError(ERROR_MESSAGES[response.status] ?? UNKNOWN_ERROR)
        return false
      }
      setMessage(describeIndex(getIndex(await response.json())))
      setDocuments(await fetchDocuments())
      return true
    } catch {
      setError(UNKNOWN_ERROR)
      return false
    } finally {
      setBusy(false)
    }
  }

  async function handleUpload(event) {
    event.preventDefault()
    const form = event.currentTarget
    const uploaded = await send(
      '/api/documents',
      { body: new FormData(form) },
      (data) => data.index,
    )
    if (uploaded) {
      form.reset()
    }
  }

  return (
    <>
      <form className="upload" onSubmit={handleUpload}>
        <label htmlFor="file">Upload a .txt document</label>
        <p className="hint">Uploading a file with an existing name replaces that document.</p>
        <div className="search-row">
          <input id="file" name="file" type="file" accept=".txt" required />
          <button type="submit" disabled={busy}>
            Upload
          </button>
        </div>
      </form>

      <button
        className="secondary"
        disabled={busy}
        onClick={() => send('/api/documents/reindex', {}, (data) => data)}
      >
        {busy ? 'Working…' : 'Reindex all documents'}
      </button>

      {message && (
        <p className="success" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <h2>Documents</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Size</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.name}>
              <td>{document.name}</td>
              <td>{(document.bytes / 1024).toFixed(1)} KB</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
