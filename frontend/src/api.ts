import type { components } from './generated/api';

export type Profile = components['schemas']['Profile'];
export type Paper = components['schemas']['Paper'];
export type Observation = components['schemas']['Observation'];
export type Evidence = components['schemas']['Evidence'];
export type Passage = components['schemas']['Passage'];
export type Source = components['schemas']['Source'];
export type Review = components['schemas']['Review'];
export type Configuration = components['schemas']['Configuration'];
export type ImportRequest = components['schemas']['ImportRequest'];
export type ImportPreview = components['schemas']['ImportPreview'];
export type Fields = components['schemas']['SchemaFields'];

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

function errorText(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => typeof item === 'string' ? item : item.msg || JSON.stringify(item)).join(' ');
  return JSON.stringify(detail);
}

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method, headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch { throw new ApiError('The local app is not responding. Keep this tab open and restart the launcher, then retry saving.', 0); }
  const result = await response.json();
  if (!response.ok) throw new ApiError(errorText(result.detail ?? result), response.status);
  return result as T;
}

export async function download(path: string, filename: string) {
  const response = await fetch(`/api${path}`);
  if (!response.ok) throw new Error('The download failed. Please retry.');
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const message = (error: unknown) => error instanceof Error ? error.message : String(error);
export const label = (key: string) => ({ pmid: 'PMID', pmcid: 'PMCID', author: 'Paper researcher',
  paper_id: 'Paper ID (optional)', date: 'Annotation date', temperature: 'Temperature (°C)',
  numbering: 'HA / NA numbering', binding_assay: 'Receptor / binding substrate' }[key]
  ?? key.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase()));
