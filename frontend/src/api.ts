//types

export interface Source {
  source: string
  page:   number
}

export type SSEEvent =
  | { type: 'sources'; sources: Source[] }
  | { type: 'delta';   text: string }
  | { type: 'done' }
  | { type: 'error';   text: string }

export interface AppStatus {
  chunks: number
  ready:  boolean
  docs:   string[]
}

export interface IngestJob {
  status: 'pending' | 'running' | 'done' | 'error'
  detail: string
}

# Status 

export async function fetchStatus(): Promise<AppStatus> {
  const res = await fetch('/api/status')
  if (!res.ok) throw new Error('Failed to fetch status')
  return res.json()
}

//ingest

export async function uploadFiles(files: File[]): Promise<string> {
  const form = new FormData()
  for (const f of files) form.append('files', f)

  const res = await fetch('/api/ingest', { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())

  const data = await res.json() as { job_id: string }
  return data.job_id
}

export async function pollJob(jobId: string): Promise<IngestJob> {
  const res = await fetch(`/api/ingest/status/${jobId}`)
  if (!res.ok) throw new Error('Failed to poll job status')
  return res.json()
}

// Query (SSE over fetch) 

export async function* streamQuery(question: string): AsyncGenerator<SSEEvent> {
  const res = await fetch('/api/query', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body:    JSON.stringify({ question }),
  })

  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

  const reader  = res.body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE events separated
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''

    for (const event of events) {
      const line = event.replace(/^data: /, '').trim()
      if (line) yield JSON.parse(line) as SSEEvent
    }
  }
}
