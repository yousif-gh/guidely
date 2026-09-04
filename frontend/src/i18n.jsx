import { createContext, useContext, useEffect, useState } from 'react';

const STRINGS = {
  en: {
    tagline: 'ask the docs / get cited answers',
    nav_search: 'search',
    nav_admin: 'admin',
    toggle_theme: 'Toggle dark mode',
    toggle_lang: 'Switch to Arabic',
    ask_placeholder: 'Ask about a policy, process, or product…',
    ask_button: 'Ask',
    ask_button_busy: 'Searching…',
    try_examples: 'try:',
    spinner: 'retrieving passages',
    empty_state: 'Answers appear here with numbered sources, so you can check exactly where each claim came from.',
    answer_eyebrow: 'Answer',
    sources_eyebrow: 'Sources',
    cache_hit: 'cache hit',
    cache_miss: 'cache miss',
    upload_title: 'Upload a document',
    upload_choose: 'choose .txt / .md file',
    upload_tags: 'tags, comma separated (optional)',
    upload_submit: 'Upload and index',
    indexed_title: 'Indexed documents',
    reindex: 'Re-index all',
    export_csv: 'Export query log (CSV)',
    empty_docs: 'Nothing is indexed yet. Upload a file above or drop files into backend/data/sample-docs and run a re-index.',
    col_file: 'File',
    col_chunks: 'Chunks',
    col_tags: 'Tags',
    col_indexed: 'Indexed',
    edit: 'Edit',
    delete: 'Delete',
    editing: 'Editing',
    save: 'Save and re-index',
    cancel: 'Cancel',
    metrics_title: 'Metrics',
    m_documents: 'documents',
    m_chunks: 'chunks',
    m_queries: 'queries served',
    m_median: 'median latency',
    m_p95: 'p95 latency',
    m_cache_rate: 'cache hit rate',
    translate: 'Translate',
    translating: 'Translating…',
    show_original: 'Show original',
    translate_lang_name: 'English',
  },
  ar: {
    tagline: 'اسأل المستندات / احصل على إجابات موثّقة',
    nav_search: 'بحث',
    nav_admin: 'إدارة',
    toggle_theme: 'تبديل الوضع الداكن',
    toggle_lang: 'التبديل إلى الإنجليزية',
    ask_placeholder: 'اسأل عن سياسة أو إجراء أو منتج…',
    ask_button: 'اسأل',
    ask_button_busy: 'جارٍ البحث…',
    try_examples: 'جرّب:',
    spinner: 'جارٍ استرجاع المقاطع',
    empty_state: 'تظهر الإجابات هنا مع مصادر مرقّمة، حتى تتحقق بدقة من مصدر كل ادعاء.',
    answer_eyebrow: 'الإجابة',
    sources_eyebrow: 'المصادر',
    cache_hit: 'إصابة ذاكرة تخزين مؤقت',
    cache_miss: 'دون تخزين مؤقت',
    upload_title: 'رفع مستند',
    upload_choose: 'اختر ملف ‎.txt / .md',
    upload_tags: 'وسوم، مفصولة بفواصل (اختياري)',
    upload_submit: 'رفع وفهرسة',
    indexed_title: 'المستندات المفهرسة',
    reindex: 'إعادة فهرسة الكل',
    export_csv: 'تصدير سجل الاستعلامات (CSV)',
    empty_docs: 'لا يوجد شيء مفهرس بعد. ارفع ملفًا أعلاه أو ضع ملفات في backend/data/sample-docs ثم أعد الفهرسة.',
    col_file: 'الملف',
    col_chunks: 'المقاطع',
    col_tags: 'الوسوم',
    col_indexed: 'تاريخ الفهرسة',
    edit: 'تعديل',
    delete: 'حذف',
    editing: 'تعديل',
    save: 'حفظ وإعادة فهرسة',
    cancel: 'إلغاء',
    metrics_title: 'المقاييس',
    m_documents: 'المستندات',
    m_chunks: 'المقاطع',
    m_queries: 'الاستعلامات المنفذة',
    m_median: 'زمن الاستجابة الوسيط',
    m_p95: 'زمن الاستجابة (p95)',
    m_cache_rate: 'نسبة إصابة التخزين المؤقت',
    translate: 'ترجمة',
    translating: 'جارٍ الترجمة…',
    show_original: 'عرض النص الأصلي',
    translate_lang_name: 'Arabic',
  },
};

const LangContext = createContext(null);

function getInitialLang() {
  const saved = localStorage.getItem('guidely-lang');
  return saved === 'ar' || saved === 'en' ? saved : 'en';
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState(getInitialLang);
  const dir = lang === 'ar' ? 'rtl' : 'ltr';

  useEffect(() => {
    document.documentElement.setAttribute('lang', lang);
    document.documentElement.setAttribute('dir', dir);
    localStorage.setItem('guidely-lang', lang);
  }, [lang, dir]);

  const t = (key) => STRINGS[lang][key] ?? STRINGS.en[key] ?? key;

  return (
    <LangContext.Provider value={{ lang, setLang, dir, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error('useLang must be used inside LangProvider');
  return ctx;
}
