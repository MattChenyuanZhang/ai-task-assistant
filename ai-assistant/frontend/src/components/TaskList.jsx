import { useState } from 'react'
import { updateTask, deleteTask } from '../api/client'

const PRIORITY_COLOR = { high: '#e53e3e', medium: '#d69e2e', low: '#38a169' }

function formatDeadline(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function TaskItem({ task, onRefresh }) {
  const [loading, setLoading] = useState(false)

  const toggleDone = async () => {
    setLoading(true)
    await updateTask(task.id, { status: task.status === 'done' ? 'pending' : 'done' })
    onRefresh()
    setLoading(false)
  }

  const handleDelete = async () => {
    setLoading(true)
    await deleteTask(task.id)
    onRefresh()
  }

  return (
    <div className={`task-item ${task.status === 'done' ? 'done' : ''}`}>
      <div className="task-header">
        <span
          className="priority-badge"
          style={{ background: PRIORITY_COLOR[task.priority] || '#718096' }}
        >
          {task.priority}
        </span>
        <span className="task-title">{task.title}</span>
        <div className="task-actions">
          <button onClick={toggleDone} disabled={loading} title={task.status === 'done' ? 'Mark pending' : 'Mark done'}>
            {task.status === 'done' ? '↩' : '✓'}
          </button>
          <button onClick={handleDelete} disabled={loading} title="Delete" className="btn-danger">
            ✕
          </button>
        </div>
      </div>
      {task.description && <p className="task-desc">{task.description}</p>}
      <div className="task-meta">
        {task.deadline && (
          <span className="deadline">📅 {formatDeadline(task.deadline)}</span>
        )}
        {task.estimated_hours && (
          <span className="hours">⏱ ~{task.estimated_hours}h</span>
        )}
      </div>
    </div>
  )
}

export default function TaskList({ tasks, onRefresh }) {
  const pending = tasks.filter(t => t.status === 'pending')
  const done = tasks.filter(t => t.status === 'done')

  if (tasks.length === 0) {
    return (
      <div className="task-list">
        <h2>Your Tasks</h2>
        <p className="empty">No tasks yet. Add some using voice or text above.</p>
      </div>
    )
  }

  return (
    <div className="task-list">
      <h2>Your Tasks</h2>
      {pending.length > 0 && (
        <div className="task-section">
          <h3>Pending ({pending.length})</h3>
          {pending.map(t => (
            <TaskItem key={t.id} task={t} onRefresh={onRefresh} />
          ))}
        </div>
      )}
      {done.length > 0 && (
        <div className="task-section">
          <h3>Completed ({done.length})</h3>
          {done.map(t => (
            <TaskItem key={t.id} task={t} onRefresh={onRefresh} />
          ))}
        </div>
      )}
    </div>
  )
}
