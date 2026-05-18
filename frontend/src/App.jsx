import { useState, useEffect, useCallback, useRef } from 'react'
import AdvicePanel from './components/AdvicePanel'
import TaskList from './components/TaskList'
import AddTaskModal from './components/AddTaskModal'
import { fetchTasks, extractTasks, fetchAdvice, fetchReminder, sendChat, clearAllTasks } from './api/client'
import { calculateProbabilities, getBucket, bucketDropped } from './utils/probability'

function parseSuggestions(text) {
  const match = text.match(/\*\*Suggestions:\*\*\s*([\s\S]*)$/)
  return match ? match[1].trim() : text
}

function NavBar({ onHome, onDashboard }) {
  return (
    <nav className="nav-light">
      <span className="nav-logo" style={{ cursor: 'pointer' }} onClick={onHome}>HAL</span>
      <div className="nav-links-light">
        <button className="nav-link-light nav-link-btn" onClick={onHome}>Suggestions</button>
        <button className="nav-link-light nav-link-btn" onClick={onDashboard}>My tasks</button>
        <a className="nav-link-light" href="#">About</a>
      </div>
    </nav>
  )
}

export default function App() {
  const [page, setPage] = useState('home')
  const [tasks, setTasks] = useState([])
  const [showAddTask, setShowAddTask] = useState(false)
  const [advice, setAdvice] = useState(null)
  const [messages, setMessages] = useState([])
  const [thinking, setThinking] = useState(false)
  const [input, setInput] = useState('')
  const [submitError, setSubmitError] = useState('')
  const messagesEndRef = useRef(null)
  const lastActivityRef = useRef(Date.now())
  const prevBucketsRef = useRef({})

  const loadTasks = useCallback(async () => {
    const data = await fetchTasks()
    setTasks(data)
    return data
  }, [])

  useEffect(() => {
    loadTasks().then(data => {
      if (data.length > 0) {
        setThinking(true)
        fetchAdvice()
          .then(r => {
            setAdvice(r.advice)
            const suggestions = parseSuggestions(r.advice)
            const lines = suggestions.split('\n').filter(Boolean).slice(0, 3).join('\n')
            setMessages([{ role: 'assistant', content: lines || r.advice, time: new Date() }])
          })
          .catch(() => {
            setMessages([{ role: 'assistant', content: "Hey! You have tasks waiting. What would you like to work on?", time: new Date() }])
          })
          .finally(() => setThinking(false))
      }
    })
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  // Proactive suggestion trigger
  useEffect(() => {
    const INACTIVITY_MS = 5 * 60 * 1000  // 5 minutes

    const id = setInterval(async () => {
      if (tasks.length === 0) return
      const inactiveLong = Date.now() - lastActivityRef.current > INACTIVITY_MS

      const probs = calculateProbabilities(tasks)
      const prevBuckets = prevBucketsRef.current
      const newBuckets = {}
      let bucketFell = false

      tasks.forEach(t => {
        const p = probs[t.id]
        const bucket = getBucket(p)
        newBuckets[t.id] = bucket
        if (bucket && prevBuckets[t.id] && bucketDropped(prevBuckets[t.id], bucket)) {
          bucketFell = true
        }
      })
      prevBucketsRef.current = newBuckets

      if (bucketFell || inactiveLong) {
        try {
          const r = await fetchReminder()
          if (r.reminder) {
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: `⏰ ${r.reminder}`,
              time: new Date(),
            }])
            lastActivityRef.current = Date.now()
          }
        } catch (_) {}
      }
    }, 10_000)

    return () => clearInterval(id)
  }, [tasks])

  const handleSubmit = async () => {
    if (!input.trim() || thinking) return
    const userText = input.trim()
    setInput('')
    setSubmitError('')
    lastActivityRef.current = Date.now()
    setMessages(prev => [...prev, { role: 'user', content: userText, time: new Date() }])
    setThinking(true)
    try {
      const result = await sendChat(userText)

      if (result.intent === 'task') {
        const titles = result.tasks.map(t => t.title).join(', ')
        let assistantMsg = `Got it! Added ${result.tasks.length} task(s): **${titles}**`
        const data = await loadTasks()
        if (data.length > 0) {
          const adviceData = await fetchAdvice()
          setAdvice(adviceData.advice)
          const suggestions = parseSuggestions(adviceData.advice)
          const lines = suggestions.split('\n').filter(Boolean).slice(0, 3).join('\n')
          if (lines) assistantMsg += `\n\n${lines}`
        }
        setMessages(prev => [...prev, { role: 'assistant', content: assistantMsg, time: new Date() }])
      } else if (result.intent === 'update') {
        const titles = result.updated.map(u => `**${u.title}**`).join(', ')
        const assistantMsg = `Got it! Updated ${titles}.`
        await loadTasks()
        setMessages(prev => [...prev, { role: 'assistant', content: assistantMsg, time: new Date() }])
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: result.reply, time: new Date() }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I had trouble with that. Could you rephrase?", time: new Date() }])
    } finally {
      setThinking(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  function renderContent(text) {
    return text.split(/\*\*(.*?)\*\*/g).map((part, i) =>
      i % 2 === 1 ? <strong key={i}>{part}</strong> : part
    )
  }

  // HOME PAGE
  if (page === 'home') {
    const hasPending = tasks.some(t => t.status === 'pending')
    const hasMessages = messages.length > 0 || hasPending

    return (
      <div className="home-light">
        <NavBar onHome={() => setPage('home')} onDashboard={() => setPage('dashboard')} />

        {!hasMessages ? (
          <main className="home-main">
            <h1 className="home-heading">What's your TO-DOS?</h1>
            <div className="chat-box">
              <textarea
                className="chat-input"
                placeholder="e.g. Finish the report by Friday at 5pm, high priority, about 3 hours of work"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={3}
                autoFocus
              />
              <button
                className={`chat-submit ${input.trim() && !thinking ? 'active' : ''}`}
                onClick={handleSubmit}
                disabled={!input.trim() || thinking}
                aria-label="Submit"
              >↑</button>
            </div>
            {submitError && <p className="submit-error">{submitError}</p>}
            <button className="see-tasks-link" onClick={() => setPage('dashboard')}>
              see my full task list
            </button>
          </main>
        ) : (
          <>
            <main className="chat-history">
              {messages.map((msg, i) => (
                <div key={i} className={`chat-msg chat-msg--${msg.role}`}>
                  {msg.role === 'assistant' && (
                    <div className="chat-avatar">H</div>
                  )}
                  <div className="chat-msg-body">
                    <div className="chat-bubble">
                      {msg.content.split('\n').map((line, j) => (
                        <p key={j}>{renderContent(line)}</p>
                      ))}
                    </div>
                    {msg.time && (
                      <span className="chat-time">
                        {msg.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {thinking && (
                <div className="chat-msg chat-msg--assistant">
                  <div className="chat-avatar">H</div>
                  <div className="chat-bubble chat-bubble--thinking">
                    <span className="dot" /><span className="dot" /><span className="dot" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </main>
            <div className="chat-bottom">
              <div className="chat-box">
                <textarea
                  className="chat-input"
                  placeholder="Add more tasks…"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={2}
                  autoFocus
                />
                <button
                  className={`chat-submit ${input.trim() && !thinking ? 'active' : ''}`}
                  onClick={handleSubmit}
                  disabled={!input.trim() || thinking}
                  aria-label="Submit"
                >↑</button>
              </div>
              <button className="see-tasks-link" onClick={() => setPage('dashboard')}>
                see my full task list
              </button>
            </div>
          </>
        )}
      </div>
    )
  }

  // DETAIL PAGE
  if (page === 'detail') {
    return (
      <div className="home-light">
        <NavBar onHome={() => setPage('home')} onDashboard={() => setPage('dashboard')} />
        <main className="detail-main">
          <h2 className="detail-title">AI Suggestions</h2>
          <AdvicePanel initialAdvice={advice} />
        </main>
      </div>
    )
  }

  // DASHBOARD
  return (
    <div className="home-light">
      <NavBar onHome={() => setPage('home')} onDashboard={() => setPage('dashboard')} />
      <main className="tasks-main">
        <div className="tasks-header">
          <h2 className="tasks-title">My Tasks</h2>
          <button className="btn-nav-dark" onClick={() => setPage('home')}>+ Add task</button>
        </div>
        {tasks.length === 0 ? (
          <div className="tasks-empty">
            <p>No tasks yet.</p>
          </div>
        ) : (
          <TaskList tasks={tasks} onRefresh={loadTasks} />
        )}
      </main>
    </div>
  )
}
