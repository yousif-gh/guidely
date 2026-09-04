import { useState, useEffect } from 'react';
import SearchPage from './pages/SearchPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import { LangProvider, useLang } from './i18n.jsx';

function getInitialTheme() {
  const saved = localStorage.getItem('guidely-theme');
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function Shell() {
  const [page, setPage] = useState('search');
  const [theme, setTheme] = useState(getInitialTheme);
  const { lang, setLang, t } = useLang();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('guidely-theme', theme);
  }, [theme]);

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <div className="wordmark">
            Guidely<span className="dot">.</span>
          </div>
          <div className="tagline">{t('tagline')}</div>
        </div>
        <nav className="nav" aria-label="Pages">
          <button
            className={page === 'search' ? 'active' : ''}
            onClick={() => setPage('search')}
          >
            {t('nav_search')}
          </button>
          <button
            className={page === 'admin' ? 'active' : ''}
            onClick={() => setPage('admin')}
          >
            {t('nav_admin')}
          </button>
          <button
            className="lang-toggle"
            onClick={() => setLang((l) => (l === 'ar' ? 'en' : 'ar'))}
            aria-label={t('toggle_lang')}
            title={t('toggle_lang')}
          >
            {lang === 'ar' ? 'EN' : 'AR'}
          </button>
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
            aria-label={t('toggle_theme')}
            title={t('toggle_theme')}
          >
            {theme === 'dark' ? '☀️' : '🌙️'}
          </button>
        </nav>
      </header>
      {page === 'search' ? <SearchPage /> : <AdminPage />}
    </div>
  );
}

export default function App() {
  return (
    <LangProvider>
      <Shell />
    </LangProvider>
  );
}