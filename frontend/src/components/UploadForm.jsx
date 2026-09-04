import { useRef, useState } from 'react';
import { useLang } from '../i18n.jsx';

export default function UploadForm({ onUpload, busy }) {
  const { t } = useLang();
  const fileRef = useRef(null);
  const [fileName, setFileName] = useState(null);
  const [tags, setTags] = useState('');

  const submit = () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    onUpload(file, tags);
    fileRef.current.value = '';
    setFileName(null);
    setTags('');
  };

  return (
    <div className="upload-row">
      <label className="file-label">
        {fileName || t('upload_choose')}
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md"
          style={{ display: 'none' }}
          onChange={(e) => setFileName(e.target.files?.[0]?.name || null)}
        />
      </label>
      <input
        type="text"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        placeholder={t('upload_tags')}
        aria-label="Tags"
      />
      <button className="btn small" onClick={submit} disabled={busy || !fileName}>
        {t('upload_submit')}
      </button>
    </div>
  );
}
