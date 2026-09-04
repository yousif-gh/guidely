import { useEffect, useState } from 'react';
import {
  deleteDocument,
  editDocument,
  getDocumentContent,
  getMetrics,
  listDocuments,
  reindex,
  uploadDocument,
} from '../api.js';
import DocumentTable from '../components/DocumentTable.jsx';
import UploadForm from '../components/UploadForm.jsx';
import { useLang } from '../i18n.jsx';

export default function AdminPage() {
  const { t } = useLang();
  const [docs, setDocs] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState(null); // { ok: bool, text: string }
  const [editing, setEditing] = useState(null); // { id, filename, content }
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      const [d, m] = await Promise.all([listDocuments(), getMetrics()]);
      setDocs(d.documents);
      setMetrics(m);
    } catch (err) {
      setStatus({ ok: false, text: err.message });
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const run = async (fn, okText) => {
    setBusy(true);
    setStatus(null);
    try {
      const out = await fn();
      setStatus({ ok: true, text: okText(out) });
      await refresh();
    } catch (err) {
      setStatus({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  };

  const handleUpload = (file, tags) =>
    run(
      () => uploadDocument(file, tags),
      (r) =>
        `Indexed ${r.document.filename}: ${r.chunks_created} chunks, ` +
        `${r.embeddings_new} new / ${r.embeddings_cached} cached embeddings (${r.elapsed_ms} ms)`
    );

  const handleReindex = () =>
    run(
      () => reindex(),
      (r) =>
        `Re-index done in ${r.elapsed_ms} ms — indexed ${r.indexed.length}, ` +
        `skipped ${r.skipped_unchanged.length} unchanged`
    );

  const handleDelete = (id) =>
    run(() => deleteDocument(id), () => `Deleted ${id}`);

  const openEditor = async (id) => {
    setStatus(null);
    try {
      const doc = await getDocumentContent(id);
      setEditing(doc);
    } catch (err) {
      setStatus({ ok: false, text: err.message });
    }
  };

  const saveEdit = () =>
    run(
      () => editDocument(editing.id, editing.content),
      (r) =>
        `Saved ${r.document.filename} and re-indexed ` +
        `(${r.embeddings_new} new / ${r.embeddings_cached} cached embeddings)`
    ).then(() => setEditing(null));

  return (
    <main>
      <div className="panel">
        <h2>{t('upload_title')}</h2>
        <UploadForm onUpload={handleUpload} busy={busy} />
      </div>

      <div className="panel">
        <h2>{t('indexed_title')}</h2>
        <DocumentTable
          docs={docs}
          onEdit={openEditor}
          onDelete={handleDelete}
          busy={busy}
        />
        <div className="editor-actions">
          <button className="btn small" onClick={handleReindex} disabled={busy}>
            {t('reindex')}
          </button>
          <a
            className="btn small ghost"
            href="/api/metrics/export.csv"
            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
          >
            {t('export_csv')}
          </a>
        </div>
        {status && (
          <p className={`status-line${status.ok ? '' : ' error'}`} role="status">
            {status.text}
          </p>
        )}
      </div>

      {editing && (
        <div className="panel editor">
          <h2>{t('editing')} {editing.filename}</h2>
          <textarea
            value={editing.content}
            onChange={(e) => setEditing({ ...editing, content: e.target.value })}
            aria-label="Document content"
          />
          <div className="editor-actions">
            <button className="btn small" onClick={saveEdit} disabled={busy}>
              {t('save')}
            </button>
            <button className="btn small ghost" onClick={() => setEditing(null)}>
              {t('cancel')}
            </button>
          </div>
        </div>
      )}

      {metrics && (
        <div className="panel">
          <h2>{t('metrics_title')}</h2>
          <div className="metrics-grid">
            <div className="metric">
              <div className="k">{t('m_documents')}</div>
              <div className="v">{metrics.index.documents}</div>
            </div>
            <div className="metric">
              <div className="k">{t('m_chunks')}</div>
              <div className="v">{metrics.index.chunks}</div>
            </div>
            <div className="metric">
              <div className="k">{t('m_queries')}</div>
              <div className="v">{metrics.queries_served}</div>
            </div>
            <div className="metric">
              <div className="k">{t('m_median')}</div>
              <div className="v">
                {metrics.latency ? `${metrics.latency.median_ms} ms` : '—'}
              </div>
            </div>
            <div className="metric">
              <div className="k">{t('m_p95')}</div>
              <div className="v">
                {metrics.latency ? `${metrics.latency.p95_ms} ms` : '—'}
              </div>
            </div>
            <div className="metric">
              <div className="k">{t('m_cache_rate')}</div>
              <div className="v">
                {metrics.embedding_cache.hit_rate != null
                  ? `${Math.round(metrics.embedding_cache.hit_rate * 100)}%`
                  : '—'}
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
