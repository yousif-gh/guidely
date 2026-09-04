import { useLang } from '../i18n.jsx';

export default function DocumentTable({ docs, onEdit, onDelete, busy }) {
  const { t } = useLang();
  if (!docs.length) {
    return (
      <div className="state empty" style={{ marginTop: 0 }}>
        {t('empty_docs')}
      </div>
    );
  }
  return (
    <table className="doc-table">
      <thead>
        <tr>
          <th>{t('col_file')}</th>
          <th>{t('col_chunks')}</th>
          <th className="hide-sm">{t('col_tags')}</th>
          <th className="hide-sm">{t('col_indexed')}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {docs.map((d) => (
          <tr key={d.id}>
            <td className="mono">{d.filename}</td>
            <td>{d.num_chunks}</td>
            <td className="hide-sm">
              {d.tags.length
                ? d.tags.map((tag) => <span key={tag} className="tag">{tag}</span>)
                : '—'}
            </td>
            <td className="hide-sm mono">
              {d.indexed_at ? d.indexed_at.slice(0, 16).replace('T', ' ') : '—'}
            </td>
            <td>
              <button className="btn small ghost" onClick={() => onEdit(d.id)} disabled={busy}>
                {t('edit')}
              </button>{' '}
              <button className="btn small danger" onClick={() => onDelete(d.id)} disabled={busy}>
                {t('delete')}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
