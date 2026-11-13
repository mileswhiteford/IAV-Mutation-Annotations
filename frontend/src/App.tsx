import { useEffect, useRef, useState } from 'react';
import { api, download, message } from './api';
import type { Configuration, Evidence, Observation, Paper, Profile } from './api';
import { Editor } from './Editor';
import type { EditorHandle } from './Editor';
import { PaperNotes } from './PaperNotes';
import { ProfileForm } from './ProfileForm';
import { Reader } from './Reader';
import type { EvidenceFocus } from './Reader';
import { Tools } from './Tools';

export default function App() {
  const [config, setConfig] = useState<Configuration | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [booting, setBooting] = useState(true);
  const [editingProfile, setEditingProfile] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [selected, setSelected] = useState('');
  const [pmid, setPmid] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [tools, setTools] = useState(false);
  const [focus, setFocus] = useState<EvidenceFocus>(null);
  const editor = useRef<EditorHandle | null>(null);
  const notes = useRef<(() => Promise<boolean>) | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([api<Configuration>('/config'), api<Profile | null>('/profile')]).then(([c, p]) => {
      if (!cancelled) { setConfig(c); setProfile(p); }
    }).catch(failure => setError(message(failure))).finally(() => { if (!cancelled) setBooting(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (profile) void api<Paper[]>('/papers').then(setPapers).catch(failure => setError(message(failure)));
  }, [profile]);

  async function flush() {
    const observationSaved = await (editor.current?.flush() ?? Promise.resolve(true));
    const notesSaved = await (notes.current?.() ?? Promise.resolve(true));
    return observationSaved && notesSaved;
  }

  async function act(action: () => Promise<void>, guard = true) {
    setBusy(true); setError('');
    try { if (!guard || await flush()) await action(); }
    catch (failure) { setError(message(failure)); }
    finally { setBusy(false); }
  }

  async function openPaper(id: string, retrieve = false) {
    const next = await api<Paper>(retrieve ? '/papers' : `/papers/${id}`, retrieve ? 'POST' : 'GET', retrieve ? { pmid: id } : undefined);
    const rows = await api<Observation[]>(`/papers/${id}/observations`);
    setPaper(next); setObservations(rows); setSelected(rows[0]?.id ?? ''); setFocus(null);
    setPapers(await api<Paper[]>('/papers'));
  }

  async function addObservation(context = false, duplicate = false) {
    if (!paper) return;
    const next = duplicate
      ? await api<Observation>(`/observations/${selected}/duplicate`, 'POST')
      : await api<Observation>(`/papers/${paper.pmid}/observations`, 'POST', { context_from: context ? selected : null });
    setObservations(value => [...value, next]); setSelected(next.id);
    setPapers(await api<Paper[]>('/papers'));
  }

  const observation = observations.find(item => item.id === selected);
  if (booting) return <main className="loading" aria-busy="true">Opening your annotation workspace…</main>;
  if (!config) return <main className="onboarding"><h1>Could not open the workspace</h1><p role="alert">{error}</p><button onClick={() => window.location.reload()}>Retry</button></main>;
  if (!profile || editingProfile) return <main><ProfileForm initial={profile} onSaved={value => { setProfile(value); setEditingProfile(false); }} onCancel={profile ? () => setEditingProfile(false) : undefined} /></main>;

  return <>
    <a className="skip-link" href="#main">Skip to workspace</a>
    <header className="app-header"><div className="brand"><span className="brand-symbol" aria-hidden="true">IA</span><div><strong>IAV Literature Annotator</strong><span>Evidence, in context</span></div></div>
      <div className="header-actions"><button disabled={busy} onClick={() => { void act(async () => { setEditingProfile(true); }); }}>{profile.name}</button>
        <button disabled={busy} onClick={() => { void act(async () => { setTools(true); }); }}>Import &amp; backup</button>
        <button className="primary" disabled={busy} onClick={() => { void act(() => download('/export', 'iav-annotations.zip')); }}>Export work</button></div>
    </header>
    <div className="app-layout">
      <aside className="library" aria-label="Paper library"><h2>Your papers <span className="count">{papers.length}</span></h2>
        <form onSubmit={event => { event.preventDefault(); void act(() => openPaper(pmid.trim(), !papers.some(p => p.pmid === pmid.trim()))); }}>
          <label htmlFor="pmid">Add or open a PMID</label><div className="pmid-entry"><input id="pmid" inputMode="numeric" pattern="[1-9][0-9]{0,11}" required placeholder="Enter PMID" value={pmid} onChange={e => setPmid(e.target.value)} /><button disabled={busy} type="submit">Open</button></div>
        </form>
        <p className="help">Any PMID works. No assignment needed.</p>
        <nav aria-label="Cached papers">{papers.map(item => <button className={`paper-link ${paper?.pmid === item.pmid ? 'active' : ''}`} key={item.pmid} disabled={busy}
          aria-current={paper?.pmid === item.pmid ? 'page' : undefined} onClick={() => { void act(() => openPaper(item.pmid)); }}>
          <span className="paper-id">PMID {item.pmid}</span><span className="paper-link-title">{item.title || 'Article metadata not yet retrieved'}</span>
          <span className="paper-progress">{item.observation_count} observations · {item.review?.progress.replaceAll('_', ' ') ?? 'in progress'}</span>
        </button>)}</nav>
        {!papers.length && <p className="empty compact">Papers you open or import will appear here.</p>}
      </aside>
      <main id="main" className="main-workspace" aria-busy={busy}>
        {busy && <div className="busy-bar" role="status">Working… You can keep reading while the request finishes.</div>}
        {error && <div className="error global-error" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}
        {!paper ? <section className="welcome"><span className="welcome-rule" aria-hidden="true" /><h1>Start with a paper.</h1>
          <p>Enter a PMID to bring the article and annotation protocol into one workspace. Your notes and observations stay on this computer.</p>
          <ol><li>Retrieve the available article text.</li><li>Select Results evidence and record an observation.</li><li>Export your contribution, including partial work.</li></ol>
          <button onClick={() => setTools(true)}>Import existing annotations</button>
        </section> : <>
          <section className="paper-heading"><div className="paper-identifiers">PMID {paper.pmid}{paper.paper_id && ` / ${paper.paper_id}`}{paper.pmcid && ` / ${paper.pmcid}`}</div>
            <h1>{paper.title || `Paper ${paper.pmid}`}</h1><div className="actions source-links"><a href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`} target="_blank" rel="noreferrer">Open PubMed</a>
              {paper.pmcid && /^PMC\d+$/.test(paper.pmcid) && <a href={`https://pmc.ncbi.nlm.nih.gov/articles/${paper.pmcid}/`} target="_blank" rel="noreferrer">Open PMC</a>}
              <button disabled={busy} onClick={() => { void act(async () => {
                setPaper(await api<Paper>(`/papers/${paper.pmid}/retry`, 'POST'));
              }); }}>Retrieve / refresh text</button></div>
            <div className="retrieval-states">{Object.entries(paper.retrieval ?? {}).map(([kind, result]) => <p key={kind} className={result.state === 'error' ? 'retrieval-error' : ''}>
              <strong>{kind === 'pmc' ? 'PMC' : 'PubMed'}: {String(result.state)}</strong> {String(result.message)}
            </p>)}</div>
            <PaperNotes key={paper.pmid} paper={paper} handle={notes} />
          </section>
          <div className="observation-toolbar"><label>Observation<select value={selected} disabled={busy || !observations.length} onChange={e => {
            const id = e.target.value; void act(async () => { setSelected(id); });
          }}><option value="">Choose an observation</option>{observations.map((item, i) => <option key={item.id} value={item.id}>{i + 1}. {item.fields.mutation || 'Draft'} — {item.fields.phenotype || 'No phenotype yet'} ({item.annotator_name}, {item.status})</option>)}</select></label>
            <button className="primary" disabled={busy || !paper.sources?.some(s => s.kind === 'pmc')} onClick={() => { void act(() => addObservation()); }}>New observation</button>
            {observation && <button disabled={busy} onClick={() => { void act(() => addObservation(true)); }}>Reuse context</button>}
          </div>
          <div className="workspace"><Reader key={paper.pmid} paper={paper} canAttach={!!observation && !busy} onAttach={(evidence: Evidence) => editor.current?.attach(evidence)} focus={focus} />
            {observation ? <Editor key={observation.id} initial={observation} config={config} handle={editor}
              onSaved={saved => setObservations(value => value.map(item => item.id === saved.id ? saved : item))}
              onDuplicate={() => { void act(() => addObservation(false, true)); }}
              onEvidence={evidence => setFocus({ evidence, nonce: Date.now() })} />
              : <section className="panel editor-empty"><h2>Capture an observation</h2><p>{paper.sources?.some(s => s.kind === 'pmc') ? 'Create an observation, then attach supporting Results text from the article.' : 'Use the paper’s screening notes while full text is unavailable. You can defer it and return later.'}</p>
                <details className="protocol"><summary>Read the annotation protocol</summary><pre>{config.protocol}</pre></details></section>}
          </div>
        </>}
      </main>
    </div>
    {tools && <Tools onClose={() => setTools(false)} onChanged={() => { void act(async () => {
      setPapers(await api<Paper[]>('/papers'));
      if (paper) setObservations(await api<Observation[]>(`/papers/${paper.pmid}/observations`));
    }, false); }} />}
  </>;
}
