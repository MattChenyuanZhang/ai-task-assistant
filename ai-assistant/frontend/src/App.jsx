import { useState, useEffect, useCallback } from 'react'
import VoiceInput from './components/VoiceInput'
import TaskList from './components/TaskList'
import AdvicePanel from './components/AdvicePanel'
import SchedulePanel from './components/SchedulePanel'
import NotificationBanner from './components/NotificationBanner'
import { fetchTasks, extractTasks, fetchUrgentTasks } from './api/client'

export default function App() {
  const [tasks, setTasks] = useState([])
  const [urgentTasks, setUrgentTasks] = useState([])
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [extractLoading, setExtractLoading] = useState(false)
  const [extractResult, setExtractResult] = useState(null)

  const loadTasks = useCallback(async () => {
    const data = await fetchTasks()
    setTasks(data)
  }, [])

  const checkUrgent = useCallback(async () => {
    const data = await fetchUrgentTasks()
    if (data.length > 0) {
      setUrgentTasks(data)
      setBannerDismissed(false)
    }
  }, [])

  // On open: load tasks and check urgent once
  useEffect(() => {
    loadTasks()
    checkUrgent()
  }, [loadTasks, checkUrgent])

  const handleExtract = async (text) => {
    setExtractLoading(true)
    setExtractResult(null)
    try {
      const result = await extractTasks(text)
      setExtractResult(`Saved ${result.extracted} task${result.extracted !== 1 ? 's' : ''}`)
      await loadTasks()
    } catch {
      setExtractResult('Failed to extract tasks. Check the backend.')
    } finally {
      setExtractLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Daily Assistant</h1>
        <span className="time">{new Date().toLocaleString(undefined, {
          weekday: 'long', month: 'long', day: 'numeric',
          hour: '2-digit', minute: '2-digit',
        })}</span>
      </header>

      {!bannerDismissed && (
        <NotificationBanner
          urgentTasks={urgentTasks}
          onDismiss={() => setBannerDismissed(true)}
        />
      )}

      <main className="app-main">
        <div className="left-panel">
          <VoiceInput onSubmit={handleExtract} loading={extractLoading} />
          {extractResult && <p className="extract-result">{extractResult}</p>}
          <TaskList tasks={tasks} onRefresh={loadTasks} />
        </div>
        <div className="right-panel">
          <AdvicePanel />
          <SchedulePanel />
        </div>
      </main>
    </div>
  )
}
