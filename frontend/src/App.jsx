import { useState } from 'react'
import AdminPage from './pages/AdminPage'
import SearchPage from './pages/SearchPage'

export default function App() {
  const [page, setPage] = useState('search')

  return (
    <main className="page">
      <h1>Guidely</h1>
      <nav>
        <button
          className="nav-link"
          aria-current={page === 'search' ? 'page' : undefined}
          onClick={() => setPage('search')}
        >
          Search
        </button>
        <button
          className="nav-link"
          aria-current={page === 'admin' ? 'page' : undefined}
          onClick={() => setPage('admin')}
        >
          Admin
        </button>
      </nav>
      {page === 'search' ? <SearchPage /> : <AdminPage />}
    </main>
  )
}
