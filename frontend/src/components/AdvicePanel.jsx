import { useState } from 'react'
import { fetchAdvice } from '../api/client'

function parseAdvice(text) {
  const reasoningMatch = text.match(/\*\*Reasoning:\*\*\s*([\s\S]*?)(?=\*\*Suggestions:\*\*|$)/)
  const suggestionsMatch = text.match(/\*\*Suggestions:\*\*\s*([\s\S]*)$/)
  return {
    reasoning: reasoningMatch ? reasoningMatch[1].trim() : null,
    suggestions: suggestionsMatch ? suggestionsMatch[1].trim() : text,
  }
}

export default function AdvicePanel({ initialAdvice }) {
  const [advice, setAdvice] = useState(initialAdvice)
  const [loading, setLoading] = useState(false)
  const [showReasoning, setShowReasoning] = useState(false)

  const refresh = async () => {
    setLoading(true)
    try {
      const data = await fetchAdvice()
      setAdvice(data.advice)
    } finally {
      setLoading(false)
    }
  }

  if (!advice && !loading) {
    return (
      <div className="advice-panel empty">
        <h2>Today's Advice</h2>
        <p>No advice loaded yet.</p>
        <button className="btn-primary" onClick={refresh}>Get Advice</button>
      </div>
    )
  }

  const parsed = advice ? parseAdvice(advice) : null

  return (
    <div className="advice-panel">
      <div className="advice-header">
        <h2>Today's Advice</h2>
        <button className="btn-secondary" onClick={refresh} disabled={loading}>
          {loading ? 'Loading...' : '↻ Refresh'}
        </button>
      </div>

      {loading && <div className="loading-spinner">Thinking...</div>}

      {parsed && !loading && (
        <>
          <div className="suggestions">
            {parsed.suggestions.split('\n').filter(Boolean).map((line, i) => (
              <p key={i} className="suggestion-line">{line}</p>
            ))}
          </div>

          {parsed.reasoning && (
            <div className="reasoning-section">
              <button
                className="btn-ghost"
                onClick={() => setShowReasoning(r => !r)}
              >
                {showReasoning ? '▼ Hide reasoning' : '▶ Show reasoning'}
              </button>
              {showReasoning && (
                <div className="reasoning-box">
                  <p>{parsed.reasoning}</p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
