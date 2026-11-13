import { useEffect } from 'react';
import type { MutableRefObject } from 'react';
import type { Paper, Review } from './api';
import { useAutosave } from './useAutosave';

export function PaperNotes({ paper, handle }: { paper: Paper; handle: MutableRefObject<(() => Promise<boolean>) | null> }) {
  const initial = paper.review as Review;
  const { draft, change, save, state, error } = useAutosave(initial, `/papers/${paper.pmid}/review`, undefined,
    value => ({ progress: value.progress, notes: value.notes, revision: value.revision }));
  useEffect(() => { handle.current = save; return () => { handle.current = null; }; }, [save, handle]);
  return <details className="paper-notes"><summary>Paper progress and screening notes <span className="subtle">{state}</span></summary>
    <div className="field"><label htmlFor="paper-progress">Paper progress</label><select id="paper-progress" value={draft.progress} onChange={e => change(value => ({ ...value, progress: e.target.value as Review['progress'] }))}>
      <option value="in_progress">In progress</option><option value="deferred">Deferred</option><option value="no_eligible">No eligible observations</option><option value="finished">Finished reading</option>
    </select></div>
    <div className="field"><label htmlFor="paper-notes-text">Screening notes</label><textarea id="paper-notes-text" rows={3} value={draft.notes} onChange={e => change(value => ({ ...value, notes: e.target.value }))} /></div>
    {error && <p role="alert" className="error">{error}</p>}<button onClick={() => { void save(); }}>Save paper notes</button>
  </details>;
}
