import { useRef, useState, useEffect } from 'react';
import { api, download, message } from './api';
import type { ImportPreview, ImportRequest } from './api';

export function Tools({ onClose, onChanged }: { onClose: () => void; onChanged: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [name, setName] = useState('');
  const [requests, setRequests] = useState<ImportRequest[]>([]);
  const [previews, setPreviews] = useState<ImportPreview[]>([]);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { dialog.current?.showModal(); }, []);
  const invalid = previews.length === 0 || previews.some(p => p.errors?.length || p.rows.some(r => r.errors.length));

  async function preview(items: ImportRequest[]) {
    setBusy(true); setError(''); setStatus(''); setPreviews([]); setRequests(items);
    try { setPreviews(await Promise.all(items.map(item => api<ImportPreview>('/import/preview', 'POST', item)))); }
    catch (failure) { setError(message(failure)); } finally { setBusy(false); }
  }

  return <dialog ref={dialog} onCancel={onClose} className="tools-dialog" aria-labelledby="tools-title">
    <div className="panel-heading"><h2 id="tools-title">Import, export, and recovery</h2><button onClick={onClose}>Close</button></div>
    <p>Exports include contributor names, record IDs, partial work, and evidence provenance.</p>
    <section><h3>Export your work</h3><div className="actions"><button onClick={() => { void download('/export', 'iav-annotations.zip').catch(e => setError(message(e))); }}>Export all work</button>
      <button onClick={() => { void download('/export?completed_only=true', 'iav-completed.zip').catch(e => setError(message(e))); }}>Export completed only</button></div></section>
    <section><h3>Import CSV annotations</h3><p className="help">Preview before importing. Existing records are preserved. A CSV carries values and attribution; evidence anchors travel in the export’s provenance file.</p>
      <label>Annotator for CSVs without attribution<input value={name} onChange={e => { setName(e.target.value); setPreviews([]); }} /></label>
      <label>Choose CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={async e => {
        const file = e.target.files?.[0];
        if (file) await preview([{ csv: await file.text(), filename: file.name, annotator: name }]);
        e.target.value = '';
      }} /></label>
      <button disabled={busy} onClick={async () => {
        try { await preview(await api<ImportRequest[]>('/import/repository')); } catch (failure) { setError(message(failure)); }
      }}>Preview existing repository annotations</button>
      {previews.map((p, i) => <div className="import-preview" key={i}><h4>{requests[i]?.filename}: {p.rows.length} rows</h4>
        {p.errors?.map((text, j) => <p className="error" key={j}>{text}</p>)}
        <div className="table-scroll"><table><caption>Import preview; original values are retained</caption><thead><tr><th>Row</th><th>PMID</th><th>Annotator</th><th>Checks</th></tr></thead><tbody>
          {p.rows.map(row => <tr key={row.line}><td>{row.line}</td><td>{row.fields.pmid}</td><td>{row.annotator_name || 'Missing'}</td><td>{row.errors.join(' ') || <details><summary>{row.warnings.length} review notes</summary>{row.warnings.map((w, j) => <p key={j}>{w}</p>)}</details>}</td></tr>)}
        </tbody></table></div></div>)}
      <button className="primary" disabled={busy || invalid} onClick={async () => {
        setBusy(true); setError('');
        try { const results: ImportPreview[] = [];
          for (const item of requests) results.push(await api<ImportPreview>('/import/apply', 'POST', item));
          setStatus(`${results.reduce((n, r) => n + r.imported, 0)} imported; ${results.reduce((n, r) => n + r.skipped, 0)} already present.`); onChanged();
        } catch (failure) { setError(message(failure)); } finally { setBusy(false); }
      }}>{busy ? 'Working…' : 'Import previewed rows'}</button>
    </section>
    <section><h3>Back up and restore</h3><p className="help">A backup includes the complete local database and cached articles. Restoring replaces local work and saves a recovery copy beside the database.</p>
      <button onClick={() => { void download('/backup', 'iav-backup.sqlite3').catch(e => setError(message(e))); }}>Download backup</button>
      <label>Restore an application backup<input type="file" accept=".sqlite3" disabled={busy} onChange={async e => {
        const file = e.target.files?.[0]; e.target.value = '';
        if (!file || !window.confirm('Replace local work with this backup? A recovery copy of the current database will be saved.')) return;
        setBusy(true); setError('');
        try { const response = await fetch('/api/restore', { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file });
          if (!response.ok) throw new Error((await response.json()).detail); window.location.reload();
        } catch (failure) { setError(message(failure)); } finally { setBusy(false); }
      }} /></label>
    </section>
    {status && <p role="status" className="notice">{status}</p>}{error && <p role="alert" className="error">{error}</p>}
  </dialog>;
}
