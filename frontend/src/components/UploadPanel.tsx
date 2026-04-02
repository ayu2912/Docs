import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchStatus, uploadFiles, pollJob } from '../api'

function OwlIllustration() {
  return (
    <svg
      width="108"
      height="162"
      viewBox="0 0 100 155"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="owl-svg"
      aria-hidden="true"
    >
      {/* Branch */}
      <path d="M4 142 Q50 148 96 142" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.35"/>

      {/* Body */}
      <ellipse cx="50" cy="103" rx="29" ry="38" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.04"/>

      {/* Head */}
      <circle cx="50" cy="47" r="24" stroke="currentColor" strokeWidth="1.5" fill="currentColor" fillOpacity="0.04"/>

      {/* Left ear tuft */}
      <path d="M36 27 L29 11 L43 24" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" fill="currentColor" fillOpacity="0.08"/>
      {/* Right ear tuft */}
      <path d="M64 27 L71 11 L57 24" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" fill="currentColor" fillOpacity="0.08"/>

      {/* Left eye outer */}
      <circle cx="39" cy="47" r="9.5" stroke="currentColor" strokeWidth="1.4" fill="currentColor" fillOpacity="0.06"/>
      {/* Left eye iris */}
      <circle cx="39" cy="47" r="5" stroke="currentColor" strokeWidth="1" fill="currentColor" fillOpacity="0.13"/>
      {/* Left pupil */}
      <circle cx="40.5" cy="45.5" r="2" fill="currentColor" fillOpacity="0.75"/>
      {/* Left eye glint */}
      <circle cx="41.8" cy="44.2" r="0.8" fill="white" opacity="0.8"/>

      {/* Right eye outer */}
      <circle cx="61" cy="47" r="9.5" stroke="currentColor" strokeWidth="1.4" fill="currentColor" fillOpacity="0.06"/>
      {/* Right eye iris */}
      <circle cx="61" cy="47" r="5" stroke="currentColor" strokeWidth="1" fill="currentColor" fillOpacity="0.13"/>
      {/* Right pupil */}
      <circle cx="62.5" cy="45.5" r="2" fill="currentColor" fillOpacity="0.75"/>
      {/* Right eye glint */}
      <circle cx="63.8" cy="44.2" r="0.8" fill="white" opacity="0.8"/>

      {/* Beak */}
      <path d="M46 58 L50 66 L54 58" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" fill="currentColor" fillOpacity="0.22"/>

      {/* Facial disc */}
      <path d="M29 57 Q50 71 71 57" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.35"/>

      {/* Body feather arcs */}
      <path d="M25 88  Q50 81 75 88"  stroke="currentColor" strokeWidth="0.9" fill="none" opacity="0.45"/>
      <path d="M23 101 Q50 94 77 101" stroke="currentColor" strokeWidth="0.9" fill="none" opacity="0.45"/>
      <path d="M25 114 Q50 107 75 114" stroke="currentColor" strokeWidth="0.9" fill="none" opacity="0.45"/>
      <path d="M29 126 Q50 120 71 126" stroke="currentColor" strokeWidth="0.9" fill="none" opacity="0.38"/>

      {/* Left wing */}
      <path d="M21 97 Q12 88 17 76 Q23 88 21 97Z" stroke="currentColor" strokeWidth="1" fill="currentColor" fillOpacity="0.06"/>
      {/* Right wing */}
      <path d="M79 97 Q88 88 83 76 Q77 88 79 97Z" stroke="currentColor" strokeWidth="1" fill="currentColor" fillOpacity="0.06"/>

      {/* Left talons */}
      <path d="M37 141 L30 151" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <path d="M37 141 L37 151" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <path d="M37 141 L43 151" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <path d="M37 141 L28 147" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>

      {/* Right talons */}
      <path d="M63 141 L57 151" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <path d="M63 141 L63 151" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <path d="M63 141 L69 151" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <path d="M63 141 L72 147" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  )
}

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'done' | 'error'

interface Props {
  onReady:  (ready: boolean) => void
  compact:  boolean
}

export function UploadPanel({ onReady, compact }: Props) {
  const [docs,     setDocs]     = useState<string[]>([])
  const [chunks,   setChunks]   = useState(0)
  const [status,   setStatus]   = useState<UploadStatus>('idle')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchStatus()
      .then(s => { setDocs(s.docs); setChunks(s.chunks); onReady(s.ready) })
      .catch(() => {})
  }, [onReady])

  const handleFiles = useCallback(async (files: FileList | null) => {
    const pdfs = Array.from(files ?? []).filter(f => f.name.toLowerCase().endsWith('.pdf'))
    if (!pdfs.length) return

    setStatus('uploading')
    try {
      const jobId = await uploadFiles(pdfs)
      setStatus('processing')

      const poll = setInterval(async () => {
        try {
          const job = await pollJob(jobId)
          if (job.status === 'done') {
            clearInterval(poll)
            const s = await fetchStatus()
            setDocs(s.docs)
            setChunks(s.chunks)
            onReady(s.ready)
            setStatus('done')
            setTimeout(() => setStatus('idle'), 2000)
          } else if (job.status === 'error') {
            clearInterval(poll)
            setStatus('error')
            setTimeout(() => setStatus('idle'), 3000)
          }
        } catch {
          clearInterval(poll)
          setStatus('error')
          setTimeout(() => setStatus('idle'), 3000)
        }
      }, 1500)
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 3000)
    }
  }, [onReady])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const onClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const busy = status === 'uploading' || status === 'processing'

  // ── Compact strip (after docs are loaded) ─────────────────────────────────
  if (compact) {
    return (
      <div
        className={['upload-strip', dragOver ? 'drag-over' : ''].filter(Boolean).join(' ')}
        onDrop={onDrop}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          style={{ display: 'none' }}
          onChange={e => handleFiles(e.target.files)}
        />

        <button
          className={['add-btn', busy ? 'spinning' : ''].filter(Boolean).join(' ')}
          onClick={busy ? undefined : onClick}
          disabled={busy}
          aria-label="Add more PDFs"
          title="Add more PDFs"
        >
          {busy ? '⟳' : '+'}
        </button>

        <div className="doc-pills">
          {docs.map(d => (
            <span key={d} className="doc-pill" title={d}>
              <span className="doc-dot" />
              {d.replace(/\.pdf$/i, '')}
            </span>
          ))}
        </div>

        {chunks > 0 && (
          <span className="chunk-badge">{chunks.toLocaleString()} chunks</span>
        )}
      </div>
    )
  }

  // ── Hero upload (initial state) ────────────────────────────────────────────
  const dropLabel: Record<UploadStatus, string> = {
    idle:       'Drop PDFs here or click to browse',
    uploading:  'Uploading…',
    processing: 'Ingesting documents…',
    done:       'Ready',
    error:      'Something went wrong — try again',
  }

  const dropIcon: Record<UploadStatus, string> = {
    idle:       '↑',
    uploading:  '⟳',
    processing: '⟳',
    done:       '✓',
    error:      '✕',
  }

  const iconClass = [
    'hero-drop-icon',
    busy               ? 'spinning' : '',
    status === 'done'  ? 'done'     : '',
    status === 'error' ? 'err'      : '',
  ].filter(Boolean).join(' ')

  return (
    <div className="upload-hero">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        multiple
        style={{ display: 'none' }}
        onChange={e => handleFiles(e.target.files)}
      />

      <div className="upload-hero-head">
        <span className="upload-hero-glyph">◈</span>
        <h1 className="upload-hero-title">Got questions? Let's dig in.</h1>
        <p className="upload-hero-sub">
          Drop your PDFs and we'll help you find answers.
        </p>
      </div>

      <div className="upload-hero-row">
        <OwlIllustration />

        <div
          className={[
            'drop-zone-hero',
            dragOver          ? 'drag-over' : '',
            busy              ? 'busy'      : '',
            status === 'error' ? 'error'    : '',
          ].filter(Boolean).join(' ')}
          onDrop={onDrop}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onClick={busy ? undefined : onClick}
          role="button"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && !busy && onClick()}
        >
          <span className={iconClass}>{dropIcon[status]}</span>
          <span className="hero-drop-label">{dropLabel[status]}</span>
          <span className="hero-drop-sub">PDF files only</span>
        </div>
      </div>
    </div>
  )
}
