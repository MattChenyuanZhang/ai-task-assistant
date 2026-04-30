import { useState, useEffect, useCallback } from 'react'
import AdvicePanel from './components/AdvicePanel'
import TaskList from './components/TaskList'
import AddTaskModal from './components/AddTaskModal'
import { fetchTasks, extractTasks } from './api/client'

export default function App() {
  const [page, setPage] = useState('home')
  const [tasks, setTasks] = useState([])
  const [showAddTask, setShowAddTask] = useState(false)
  const [taglineVisible, setTaglineVisible] = useState(false)
  const [btnVisible, setBtnVisible] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setTaglineVisible(true), 300)
    const t2 = setTimeout(() => setBtnVisible(true), 1400)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  const loadTasks = useCallback(async () => {
    const data = await fetchTasks()
    setTasks(data)
  }, [])

  const handleStart = async () => {
    await loadTasks()
    setPage('dashboard')
  }

  const handleExtract = async (text) => {
    await extractTasks(text)
    await loadTasks()
  }

  if (page === 'home') {
    return (
      <div className="home">
        <nav className="nav">
          <span className="logo">HAL</span>
          <div className="nav-actions">
            <button className="btn-nav">Log In</button>
            <button className="btn-nav-fill">Sign Up</button>
          </div>
        </nav>
        <div className="hero">
          <h1 className={`tagline ${taglineVisible ? 'visible' : ''}`}>
            Let me plan your day for you.
          </h1>
          <button
            className={`btn-start ${btnVisible ? 'visible' : ''}`}
            onClick={handleStart}
          >
            Start
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <nav className="nav">
        <span className="logo" onClick={() => setPage('home')} style={{ cursor: 'pointer' }}>HAL</span>
        <div className="nav-actions">
          <button className="btn-nav">Log In</button>
          <button className="btn-nav-fill">Sign Up</button>
        </div>
      </nav>

      <main className="dash-main">
        <div className="dash-header">
          <h2 className="dash-title">Today's Plan</h2>
          <button className="btn-add" onClick={() => setShowAddTask(true)}>
            + Add Task
          </button>
        </div>

        <AdvicePanel />

        {tasks.length === 0 ? (
          <div className="empty-state">
            <p>No tasks yet. What do you want to accomplish today?</p>
            <button className="btn-add-large" onClick={() => setShowAddTask(true)}>
              + Add your first task
            </button>
          </div>
        ) : (
          <TaskList tasks={tasks} onRefresh={loadTasks} />
        )}
      </main>

      {showAddTask && (
        <AddTaskModal
          onClose={() => setShowAddTask(false)}
          onSubmit={async (text) => {
            await handleExtract(text)
            setShowAddTask(false)
          }}
        />
      )}
    </div>
  )
}
