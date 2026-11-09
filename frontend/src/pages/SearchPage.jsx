import { useState } from 'react';
import { ask } from '../api.js';
import AnswerCard from '../components/AnswerCard.jsx';
import SourceCard from '../components/SourceCard.jsx';
import { useLang } from '../i18n.jsx';

const EXAMPLES = {
  en: [
    'How do I reset my password?',
    'How many days per week can I work remotely?',
    'When are refunds issued after a return?',
  ],
  ar: [
    'كيف أعيد تعيين كلمة المرور؟',
    'كم عدد أيام العمل عن بُعد في الأسبوع؟',
    'متى يتم استرداد المبلغ بعد الإرجاع؟',
  ],
};

export default function SearchPage() {
  const { lang, t } = useLang();
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [flashIndex, setFlashIndex] = useState(null);
  const [history, setHistory] = useState([]); // bonus: follow-up context

  const submit = async (q) => {
    const text = (q ?? question).trim();
    if (!text || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await ask(text, { history: history.slice(-6) });
      setResult(res);
      setHistory((h) => [
        ...h,
        { role: 'user', content: text },
        { role: 'assistant', content: res.answer },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const jumpToSource = (n) => {
    setFlashIndex(n);
    document
      .getElementById(`source-${n}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => setFlashIndex(null), 1400);
  };

  return (
    <main>
      <div className="ask-form">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder={t('ask_placeholder')}
          aria-label="Your question"
        />
        <button className="btn" onClick={() => submit()} disabled={loading}>
          {loading ? t('ask_button_busy') : t('ask_button')}
        </button>
      </div>
      <div className="hint">
        {t('try_examples')}{' '}
        {EXAMPLES[lang].map((ex, i) => (
          <span key={ex}>
            <button onClick={() => { setQuestion(ex); submit(ex); }}>{ex}</button>
            {i < EXAMPLES[lang].length - 1 ? ' · ' : ''}
          </span>
        ))}
      </div>

      {loading && (
        <div className="spinner">
          <img src="/letter-g-logo.gif" alt={t('spinner')} />
        </div>
      )}

      {error && (
        <div className="state error" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && !result && (
        <div className="state empty">{t('empty_state')}</div>
      )}

      {result && (
        <>
          <section className="answer-block">
            <p className="eyebrow">{t('answer_eyebrow')}</p>
            <AnswerCard answer={result.answer} onCiteClick={jumpToSource} />
            <div className="telemetry">
              <span>{result.latency_ms} ms</span>
              <span className={result.cache.hits > 0 ? 'cache-hit' : 'cache-miss'}>
                {result.cache.hits > 0 ? t('cache_hit') : t('cache_miss')}
              </span>
              <span>emb {result.provider.embeddings}</span>
              <span>llm {result.provider.llm}</span>
            </div>
          </section>

          <section className="sources">
            <p className="eyebrow">{t('sources_eyebrow')} ({result.sources.length})</p>
            {result.sources.map((s, i) => (
              <SourceCard
                key={s.chunk_id}
                index={i + 1}
                source={s}
                flash={flashIndex === i + 1}
              />
            ))}
          </section>
        </>
      )}
    </main>
  );
}
