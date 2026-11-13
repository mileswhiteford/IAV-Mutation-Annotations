import { useEffect, useState } from 'react';
import type { Evidence, Paper, Passage, Source } from './api';
import { api, message } from './api';

export type EvidenceFocus = { evidence: Evidence; nonce: number } | null;

function selectionFor(passage: Passage): { start: number; end: number; quote: string } {
  const container = document.getElementById(`text-${passage.id}`);
  const selection = window.getSelection();
  if (container && selection?.rangeCount && !selection.isCollapsed) {
    const range = selection.getRangeAt(0);
    if (container.contains(range.startContainer) && container.contains(range.endContainer)) {
      const prefix = range.cloneRange();
      prefix.selectNodeContents(container); prefix.setEnd(range.startContainer, range.startOffset);
      const quote = range.toString();
      const start = Array.from(prefix.toString()).length;
      return { start, end: start + Array.from(quote).length, quote };
    }
    throw new Error('Select text within a single passage, or clear your selection to use the whole passage.');
  }
  return { start: 0, end: Array.from(passage.text).length, quote: passage.text };
}

function Text({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>;
  const index = text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  return index < 0 ? <>{text}</> : <>{text.slice(0, index)}<mark>{text.slice(index, index + query.length)}</mark>{text.slice(index + query.length)}</>;
}

export function Reader({ paper, canAttach, onAttach, focus }: {
  paper: Paper; canAttach: boolean; onAttach: (evidence: Evidence) => void; focus: EvidenceFocus;
}) {
  const [query, setQuery] = useState('');
  const [section, setSection] = useState('all');
  const [passages, setPassages] = useState(paper.passages ?? []);
  const [sourceId, setSourceId] = useState(paper.passages?.[0]?.source_id ?? '');
  const [error, setError] = useState('');
  const [highlight, setHighlight] = useState('');

  useEffect(() => {
    setPassages(paper.passages ?? []);
    setSourceId(paper.passages?.[0]?.source_id ?? '');
  }, [paper]);

  useEffect(() => {
    if (!focus) return;
    let cancelled = false;
    const evidence = focus.evidence;
    void api<Source>(`/sources/${encodeURIComponent(evidence.source_id)}`).then(source => {
      if (cancelled) return;
      const passage = source.passages.find(p => p.id === evidence.passage_id);
      if (!passage || Array.from(passage.text).slice(evidence.start, evidence.end).join('') !== evidence.quote) {
        setError('This evidence does not match its saved passage. Review the quotation.'); return;
      }
      setPassages(source.passages); setSourceId(source.id); setSection('all'); setQuery('');
      setHighlight(evidence.passage_id); setError('');
      setTimeout(() => document.getElementById(`passage-${evidence.passage_id}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' }), 50);
    }).catch(failure => setError(message(failure)));
    return () => { cancelled = true; };
  }, [focus]);

  const source = paper.sources?.find(item => item.id === sourceId);
  const isFullText = source?.kind === 'pmc';
  const visible = passages.filter(p => (section === 'all' || p.section === section)
    && (!query || p.text.toLocaleLowerCase().includes(query.toLocaleLowerCase())));

  function attach(passage: Passage, role: 'results' | 'methods') {
    try {
      const selected = selectionFor(passage);
      if (!selected.quote.trim()) return;
      const uncertain = passage.section === 'uncertain';
      if (uncertain && !window.confirm(`This passage has an uncertain section. Confirm that the selected text is ${role === 'results' ? 'Results reporting this study’s experiment' : 'Methods describing experimental context'}.`)) return;
      onAttach({ source_id: passage.source_id, passage_id: passage.id, ...selected,
        role, section_confirmed: uncertain });
      setError(''); window.getSelection()?.removeAllRanges();
    } catch (failure) { setError(message(failure)); }
  }

  return <section className="reader panel" aria-labelledby="reader-title">
    <div className="panel-heading"><h2 id="reader-title">Article</h2><span className="badge">{isFullText ? 'Full text' : 'Title / abstract'}</span></div>
    <div className="reader-tools">
      <label>Find in article<input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search article text" /></label>
      <label>Section<select value={section} onChange={e => setSection(e.target.value)}>
        <option value="all">All sections</option>{['results', 'methods', 'abstract', 'uncertain', 'other'].map(s => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
      </select></label>
    </div>
    {(paper.sources?.length ?? 0) > 1 && <label className="version-picker">Source version<select value={sourceId} onChange={async e => {
      try { const next = await api<Source>(`/sources/${encodeURIComponent(e.target.value)}`); setSourceId(next.id); setPassages(next.passages); setHighlight(''); }
      catch (failure) { setError(message(failure)); }
    }}>{paper.sources?.map(s => <option key={s.id} value={s.id}>{s.kind === 'pmc' ? 'PMC' : 'PubMed'} · {new Date(s.retrieved_at).toLocaleString()}</option>)}</select></label>}
    {!isFullText && <p className="notice">Abstracts support screening. Results evidence from full text is required to complete an observation.</p>}
    <p className="reader-tip">Select text, then attach it below the passage. With no selection, the whole passage is attached.</p>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="article-body">
      {visible.length === 0 && <p className="empty">{passages.length ? 'No passages match this view.' : 'No article text is cached yet. Try retrieving the article, or leave screening notes and defer it.'}</p>}
      {visible.map(p => <article id={`passage-${p.id}`} key={p.id} className={`passage ${highlight === p.id ? 'highlighted' : ''}`}>
        <div className="passage-meta"><span>{p.heading || p.section}</span>{p.infons?.type === 'table_caption' && <span>Table caption</span>}</div>
        <p id={`text-${p.id}`} className={p.section === 'title' ? 'article-title' : ''}><Text text={p.text} query={query} /></p>
        {isFullText && ['results', 'methods', 'uncertain'].includes(p.section) && <div className="passage-actions">
          {(p.section === 'results' || p.section === 'uncertain') && <button disabled={!canAttach} onMouseDown={e => e.preventDefault()} onClick={() => attach(p, 'results')}>Attach Results evidence</button>}
          {(p.section === 'methods' || p.section === 'uncertain') && <button disabled={!canAttach} onMouseDown={e => e.preventDefault()} onClick={() => attach(p, 'methods')}>Attach Methods context</button>}
        </div>}
      </article>)}
    </div>
  </section>;
}
