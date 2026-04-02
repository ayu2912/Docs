import { useState, useRef, useEffect } from 'react'
import { useStreamQuery } from '../hooks/useStreamQuery'
import { Source } from '../api'

function SourceChips({ sources }: { sources: Source[] }) {
  return (
    <div className="source-chips">
      {sources.map((s, i) => (
        <span key={i} className="source-chip">
          {s.source} · p{s.page}
        </span>
      ))}
    </div>
  )
}

export function ChatPanel() {
  const { messages, streaming, submit } = useStreamQuery()
  const [input,  setInput]  = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || streaming) return
    setInput('')
    submit(q)
  }

  return (
    <div className="chat-panel">
      <div className="messages">
        {messages.length === 0 ? (
          <div className="empty-hint">
            <span className="empty-text">Ask anything about your documents.</span>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              <div className="bubble">
                {m.content}
                {m.streaming && <span className="cursor" />}
              </div>
              {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
                <SourceChips sources={m.sources} />
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <form className="input-row" onSubmit={handleSubmit}>
        <input
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask a question about your documents…"
          disabled={streaming}
          autoFocus
        />
        <button
          className="send-btn"
          type="submit"
          disabled={streaming || !input.trim()}
          aria-label="Send"
        >
          ↑
        </button>
      </form>
    </div>
  )
}
