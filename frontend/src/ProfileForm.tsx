import { useState } from 'react';
import { api, message } from './api';
import type { Profile } from './api';

export function ProfileForm({ initial, onSaved, onCancel }: {
  initial: Profile | null; onSaved: (profile: Profile) => void; onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [email, setEmail] = useState(initial?.email ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return <section className="onboarding" aria-labelledby="profile-title">
    <div className="brand-symbol" aria-hidden="true">IA</div>
    <h1 id="profile-title">Your contribution, recorded.</h1>
    <p>Read the paper. Capture the evidence. We’ll take care of the bookkeeping.</p>
    <form onSubmit={async event => {
      event.preventDefault(); setBusy(true); setError('');
      try { onSaved(await api<Profile>('/profile', 'POST', { name, email })); }
      catch (failure) { setError(message(failure)); } finally { setBusy(false); }
    }}>
      <label>Your name<input autoFocus required maxLength={200} value={name} onChange={e => setName(e.target.value)} autoComplete="name" /></label>
      <label>Email (optional)<input type="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" /></label>
      <p className="help">Your name travels with your observations and exports. Article text and annotations are stored on this computer.</p>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="actions"><button className="primary" disabled={busy || !name.trim()}>{busy ? 'Saving…' : 'Start annotating'}</button>
        {onCancel && <button type="button" onClick={onCancel}>Cancel</button>}</div>
    </form>
  </section>;
}
