import { useState } from 'react';
import { translate } from '../api.js';
import { useLang } from '../i18n.jsx';

export default function SourceCard({ index, source, flash }) {
  const { t } = useLang();
  const [translated, setTranslated] = useState(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const handleTranslate = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await translate(source.snippet, t('translate_lang_name'));
      setTranslated(res.translated);
      setShowOriginal(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article
      id={`source-${index}`}
      className={`source-card${flash ? ' flash' : ''}`}
    >
      <div className="source-num">[{index}]</div>
      <div>
        <div className="source-meta">
          <span className="source-file">{source.file}</span>
          <span className="source-score">
            {source.chunk_id.split('::')[1]} · score {source.score.toFixed(3)}
          </span>
        </div>
        <p className="source-snippet">
          {translated && !showOriginal ? translated : source.snippet}
        </p>
        <div className="source-actions">
          {!translated && (
            <button className="btn small ghost" onClick={handleTranslate} disabled={busy}>
              {busy ? t('translating') : t('translate')}
            </button>
          )}
          {translated && (
            <button
              className="btn small ghost"
              onClick={() => setShowOriginal((v) => !v)}
            >
              {showOriginal ? t('translate') : t('show_original')}
            </button>
          )}
        </div>
        {error && <p className="status-line error">{error}</p>}
      </div>
    </article>
  );
}
