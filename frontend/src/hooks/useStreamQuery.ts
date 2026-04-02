import { useState, useCallback } from 'react'
import { streamQuery, Source } from '../api'

export interface Message {
  role:      'user' | 'assistant'
  content:   string
  sources?:  Source[]
  streaming?: boolean
}

export function useStreamQuery() {
  const [messages,  setMessages]  = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)

  const submit = useCallback(async (question: string) => {
    if (streaming) return

    setMessages(prev => [
      ...prev,
      { role: 'user',      content: question },
      { role: 'assistant', content: '', streaming: true },
    ])
    setStreaming(true)

    try {
      for await (const event of streamQuery(question)) {
        if (event.type === 'sources') {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], sources: event.sources }
            return next
          })
        } else if (event.type === 'delta') {
          setMessages(prev => {
            const next    = [...prev]
            const last    = next[next.length - 1]
            next[next.length - 1] = { ...last, content: last.content + event.text }
            return next
          })
        } else if (event.type === 'error') {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], content: event.text }
            return next
          })
          break
        } else if (event.type === 'done') {
          break
        }
      }
    } catch {
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: 'Something went wrong. Please try again.',
        }
        return next
      })
    } finally {
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = { ...next[next.length - 1], streaming: false }
        return next
      })
      setStreaming(false)
    }
  }, [streaming])

  return { messages, streaming, submit }
}
