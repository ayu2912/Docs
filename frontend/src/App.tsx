import { useState } from 'react'
import { UploadPanel } from './components/UploadPanel'
import { ChatPanel }   from './components/ChatPanel'

export default function App() {
  const [ready, setReady] = useState(false)

  return (
    <div className="app">
      <header className="app-nav">
        <div className="app-nav-brand">
          <span className="app-nav-mark">◈</span>
          <span className="app-nav-name">Docs</span>
        </div>
        <span className="app-nav-sub">RAG Document Assistant</span>
      </header>

      <div className="app-main">
        <div className="center-col">
          <UploadPanel onReady={setReady} compact={ready} />
          {ready && <ChatPanel />}
        </div>
      </div>
    </div>
  )
}
