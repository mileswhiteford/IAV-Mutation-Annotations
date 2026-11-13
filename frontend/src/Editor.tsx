import { useEffect, useState } from 'react';
import type { MutableRefObject } from 'react';
import { api, label, message } from './api';
import type { Configuration, Evidence, Fields, Observation } from './api';
import { useAutosave } from './useAutosave';

export type EditorHandle = { flush: () => Promise<boolean>; attach: (evidence: Evidence) => void };

export function Editor({ initial, config, handle, onSaved, onDuplicate, onEvidence }: {
  initial: Observation; config: Configuration; handle: MutableRefObject<EditorHandle | null>;
  onSaved: (observation: Observation) => void; onDuplicate: () => void; onEvidence: (e: Evidence) => void;
}) {
  const { draft, change, save, state, error, conflicted } = useAutosave(initial, `/observations/${initial.id}`, onSaved);
  const [history, setHistory] = useState<unknown[] | null>(null);
  const [historyError, setHistoryError] = useState('');
  const [actionError, setActionError] = useState('');
  useEffect(() => {
    handle.current = { flush: save, attach: evidence => change(value => ({ ...value, status: 'draft',
      evidence: [...(value.evidence ?? []), evidence] })) };
    return () => { handle.current = null; };
  }, [handle, save, change]);

  function field(name: keyof Fields) {
    const definition = config.fields.find(item => item.name === name);
    const value = draft.fields[name];
    const update = (text: string) => change(record => ({ ...record, status: 'draft', fields: { ...record.fields, [name]: text } }));
    return <div className={`field field-${name}`} key={name}>
      <label htmlFor={`field-${name}`}>{label(name)}{['mutation', 'phenotype', 'date'].includes(name) && <span className="required" title="Required for completion"> *</span>}</label>
      {name === 'notes' || name === 'phenotype'
        ? <textarea id={`field-${name}`} rows={name === 'notes' ? 3 : 2} value={value} onChange={e => update(e.target.value)} />
        : <input id={`field-${name}`} value={value} readOnly={name === 'pmid'} onChange={e => update(e.target.value)}
          list={config.vocabulary[name] ? `vocab-${name}` : undefined} placeholder={name === 'date' ? 'MM/DD/YYYY' : undefined} />}
      {config.vocabulary[name] && <datalist id={`vocab-${name}`}>{config.vocabulary[name].map(item => <option key={item} value={item} />)}</datalist>}
      {name === 'phenotype' && (config.vocabulary.phenotype?.length ?? 0) > 0 && <select aria-label="Phenotype vocabulary suggestions" value="" onChange={e => { if (e.target.value) update(e.target.value); }}>
        <option value="">Choose a vocabulary suggestion…</option>{config.vocabulary.phenotype.map(item => <option key={item}>{item}</option>)}
      </select>}
      {definition?.description && <details className="field-help"><summary>Field guidance</summary><p>{definition.description}</p></details>}
    </div>;
  }

  return <section className="editor panel" aria-labelledby="editor-title">
    <div className="panel-heading"><h2 id="editor-title">Observation</h2><span className={`badge ${draft.status}`}>{draft.status}</span></div>
    <div className="save-strip"><span role="status" className={state === 'Saved' ? 'saved' : ''}>{state}</span><button onClick={() => { void save(); }}>Save now</button></div>
    {error && <div role="alert" className="error">{error}{conflicted && <p>Copy any unsaved text before reloading this page. Automatic saving has stopped to protect both versions.</p>}</div>}
    <p className="help contributor">Recorded by {draft.annotator_name}. {draft.status === 'legacy' ? 'Imported work needs evidence review.' : 'Edits return completed work to draft.'}</p>
    <fieldset><legend>Mutation and observed effect</legend>{field('mutation')}{field('phenotype')}
      <div className="form-grid">{field('protein')}{field('numbering')}</div>
    </fieldset>
    <fieldset><legend>Experimental context</legend><p className="help">One observation per combination of mutation(s), phenotype, and experimental system. Leave unreported details blank.</p>
      {field('backbone')}{field('recombinant')}
      <div className="form-grid">{field('subtype')}{field('temperature')}{field('cell_type')}{field('animal_model')}</div>
      {field('binding_assay')}
    </fieldset>
    <section className="evidence-list" aria-labelledby="evidence-title"><h3 id="evidence-title">Supporting evidence <span className="count">{draft.evidence?.length ?? 0}</span></h3>
      {!draft.evidence?.length && <p className="empty compact">Attach a Results passage from the article. Methods passages can clarify context.</p>}
      {draft.evidence?.map((e, index) => <div className="evidence" key={`${e.passage_id}-${index}`}>
        <div className="evidence-heading"><strong>{e.role === 'results' ? 'Results evidence' : 'Methods context'}</strong>{e.section_confirmed && <span>Section confirmed</span>}</div>
        <blockquote>{e.quote}</blockquote><div className="actions"><button onClick={() => onEvidence(e)}>Show in article</button>
          <button aria-label={`Remove evidence ${index + 1}`} onClick={() => change(value => ({ ...value, status: 'draft', evidence: value.evidence?.filter((_, i) => i !== index) }))}>Remove</button></div>
      </div>)}
    </section>
    <fieldset><legend>Notes and provenance</legend>{field('notes')}
      <label className="checkbox"><input type="checkbox" checked={draft.review_flag} onChange={e => change(value => ({ ...value, review_flag: e.target.checked }))} />Flag for review</label>
      <div className="form-grid">{field('date')}{field('author')}{field('paper_id')}{field('pmid')}{field('pmcid')}</div>
    </fieldset>
    <details className="protocol"><summary>Protocol reminders</summary>
      <ul><li>Use Results for relationships and Methods for experimental context.</li><li>Keep mutations tested together as a combination.</li><li>Separate distinct phenotypes and experimental systems.</li><li>Compare against wildtype; retain relevant tested mutations with no effect.</li><li>Exclude background, unvalidated predictions, virulence-only outcomes, and resistance claims as specified in the protocol.</li></ul>
      <pre>{config.protocol}</pre>
    </details>
    {actionError && <p role="alert" className="error">{actionError}</p>}
    <div className="editor-footer actions"><button className="primary" disabled={conflicted} onClick={async () => {
      change(value => ({ ...value, status: 'complete' })); await save();
    }}>Mark complete</button><button disabled={conflicted} onClick={async () => {
      change(value => ({ ...value, status: 'draft' })); await save();
    }}>Save as draft</button><button onClick={async () => { if (await save()) onDuplicate(); }}>Duplicate observation</button></div>
    <details className="history" onToggle={async event => {
      if (!event.currentTarget.open) return;
      try { setHistory(await api<unknown[]>(`/observations/${initial.id}/revisions`)); }
      catch (failure) { setHistoryError(message(failure)); setActionError('Could not load edit history. Your observation remains available.'); }
    }}><summary>Attribution and edit history</summary><p className="help">Record {draft.id}</p>
      {historyError && <p role="alert">{historyError}</p>}<pre>{history ? JSON.stringify(history, null, 2) : 'Open to load history.'}</pre>
    </details>
  </section>;
}
