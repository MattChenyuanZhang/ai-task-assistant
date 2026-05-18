import { useState, useEffect } from 'react'
import { updateTask, deleteTask, clearAllTasks, fetchTaskLogs } from '../api/client'
import { calculateProbabilities, getBucket, BUCKET_COLOR } from '../utils/probability'

const PRIORITY_COLOR = { high: '#e53e3e', medium: '#d69e2e', low: '#38a169' }

function formatDeadline(iso) {
  if (!iso) return null
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function ProbabilityCircle({ probability }) {
  if (probability === null || probability === undefined) return null
  const r = 16, size = 40, cx = size / 2
  const circumference = 2 * Math.PI * r
  const offset = circumference * (1 - Math.max(0, Math.min(1, probability)))
  const color = BUCKET_COLOR[getBucket(probability)]
  const pct = Math.round(probability * 100)

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e8e8e8" strokeWidth="3" />
      <circle cx={cx} cy={cx} r={r} fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round" transform={`rotate(-90 ${cx} ${cx})`}
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      <text x={cx} y={cx + 4} textAnchor="middle" fontSize="9" fontWeight="600" fill={color}>
        {pct}%
      </text>
    </svg>
  )
}

function TaskDetailModal({ task, probability, onClose }) {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTaskLogs(task.id)
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [task.id])

  const bucket = getBucket(probability)
  const bucketColor = bucket ? BUCKET_COLOR[bucket] : '#aaa'

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal task-detail-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{task.title}</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="task-detail-meta">
          <span className="priority-badge" style={{ background: PRIORITY_COLOR[task.priority] || '#718096' }}>
            {task.priority}
          </span>
          <span className="task-detail-status">{task.status}</span>
          {probability !== null && probability !== undefined && (
            <span className="task-detail-prob" style={{ color: bucketColor }}>
              {Math.round(probability * 100)}% finish probability
            </span>
          )}
        </div>

        <div className="task-detail-fields">
          {task.description && (
            <div className="task-detail-row">
              <span className="task-detail-label">Description</span>
              <span>{task.description}</span>
            </div>
          )}
          <div className="task-detail-row">
            <span className="task-detail-label">Deadline</span>
            <span>{task.deadline ? formatDeadline(task.deadline) : '—'}</span>
          </div>
          <div className="task-detail-row">
            <span className="task-detail-label">Estimated</span>
            <span>{task.estimated_hours ? `~${task.estimated_hours}h` : '—'}</span>
          </div>
          <div className="task-detail-row">
            <span className="task-detail-label">Created</span>
            <span>{formatTime(task.created_at)}</span>
          </div>
        </div>

        <div className="task-detail-log-section">
          <h4 className="task-detail-log-title">Update history</h4>
          {loading ? (
            <p className="task-detail-log-empty">Loading…</p>
          ) : logs.length === 0 ? (
            <p className="task-detail-log-empty">No updates yet.</p>
          ) : (
            logs.map(log => (
              <div key={log.id} className="task-log-entry">
                <div className="task-log-prompt">"{log.prompt}"</div>
                <div className="task-log-changes">
                  {Object.entries(log.changes).map(([k, v]) => (
                    <span key={k} className="task-log-change">{k}: {String(v)}</span>
                  ))}
                </div>
                <div className="task-log-time">{formatTime(log.created_at)}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function ProgressBar({ finished, estimated }) {
  if (!estimated || estimated <= 0) return null
  const total = finished + estimated
  const pct = Math.round((finished / total) * 100)
  return (
    <div className="prob-bar-wrap">
      <span className="prob-bar-side">{finished > 0 ? `${finished}h done` : '0h done'}</span>
      <div className="prob-bar-track">
        <div className="prob-bar-fill" style={{ width: `${pct}%`, background: '#555' }} />
      </div>
      <span className="prob-bar-side">~{estimated}h left</span>
    </div>
  )
}

function TaskItem({ task, probability, onRefresh }) {
  const [loading, setLoading] = useState(false)
  const [showDetail, setShowDetail] = useState(false)

  const toggleDone = async (e) => {
    e.stopPropagation()
    setLoading(true)
    await updateTask(task.id, { status: task.status === 'done' ? 'pending' : 'done' })
    onRefresh()
    setLoading(false)
  }

  const handleDelete = async (e) => {
    e.stopPropagation()
    setLoading(true)
    await deleteTask(task.id)
    onRefresh()
  }

  return (
    <>
      <div
        className={`task-item ${task.status === 'done' ? 'done' : ''} ${task.working ? 'working' : ''}`}
        onClick={() => setShowDetail(true)}
        style={{ cursor: 'pointer' }}
      >
        <div className="task-header">
          <span className="priority-badge" style={{ background: PRIORITY_COLOR[task.priority] || '#718096' }}>
            {task.priority}
          </span>
          <span className="task-title">{task.title}</span>
          {task.working && <span className="working-badge">● working</span>}
          <div className="task-actions">
            <button onClick={toggleDone} disabled={loading} title={task.status === 'done' ? 'Mark pending' : 'Mark done'}>
              {task.status === 'done' ? '↩' : '✓'}
            </button>
            <button onClick={handleDelete} disabled={loading} title="Delete" className="btn-danger">✕</button>
          </div>
        </div>
        {task.description && <p className="task-desc">{task.description}</p>}
        <div className="task-meta">
          {task.deadline && <span className="deadline">📅 {formatDeadline(task.deadline)}</span>}
          {task.status === 'pending' && probability !== undefined && probability !== null && (
            <span className="prob-wrap"><ProbabilityCircle probability={probability} /></span>
          )}
        </div>
        {task.status === 'pending' && (
          <ProgressBar finished={task.finished_hours || 0} estimated={task.estimated_hours} />
        )}
      </div>

      {showDetail && (
        <TaskDetailModal
          task={task}
          probability={probability}
          onClose={() => setShowDetail(false)}
        />
      )}
    </>
  )
}

function TaskBlock({ title, tasks, probs, status, onRefresh }) {
  const [clearing, setClearing] = useState(false)

  const handleClearAll = async () => {
    if (!window.confirm(`Clear all ${title.toLowerCase()}?`)) return
    setClearing(true)
    await clearAllTasks(status)
    onRefresh()
    setClearing(false)
  }

  return (
    <div className="task-block">
      <div className="task-block-header">
        <h3 className="task-block-title">
          {title} <span className="task-block-count">({tasks.length})</span>
        </h3>
        {tasks.length > 0 && (
          <button className="btn-clear-all" onClick={handleClearAll} disabled={clearing}>
            {clearing ? 'Clearing…' : 'Clear all'}
          </button>
        )}
      </div>
      {tasks.length === 0 ? (
        <p className="task-block-empty">No {title.toLowerCase()} yet.</p>
      ) : (
        tasks.map(t => (
          <TaskItem key={t.id} task={t} probability={probs?.[t.id]} onRefresh={onRefresh} />
        ))
      )}
    </div>
  )
}

function useLiveTasks(tasks) {
  const [liveTasks, setLiveTasks] = useState(tasks)

  useEffect(() => {
    setLiveTasks(tasks)
    const id = setInterval(() => {
      setLiveTasks(tasks.map(t => {
        if (!t.working || !t.working_start) return t
        const elapsed = (Date.now() - new Date(t.working_start).getTime()) / 3_600_000
        return {
          ...t,
          estimated_hours: Math.max(0, (t.estimated_hours || 0) - elapsed),
          finished_hours: (t.finished_hours || 0) + elapsed,
        }
      }))
    }, 1_000)
    return () => clearInterval(id)
  }, [tasks])

  return liveTasks
}

export default function TaskList({ tasks, onRefresh }) {
  const liveTasks = useLiveTasks(tasks)
  const [probs, setProbs] = useState({})

  useEffect(() => {
    setProbs(calculateProbabilities(liveTasks))
  }, [liveTasks])

  useEffect(() => {
    const id = setInterval(() => setProbs(calculateProbabilities(liveTasks)), 10_000)
    return () => clearInterval(id)
  }, [tasks])

  const pending = [...liveTasks.filter(t => t.status === 'pending')]
    .sort((a, b) => (probs[a.id] ?? 1) - (probs[b.id] ?? 1))
  const done = liveTasks.filter(t => t.status === 'done')

  return (
    <div className="task-list">
      <TaskBlock title="Tasks" tasks={pending} probs={probs} status="pending" onRefresh={onRefresh} />
      <TaskBlock title="Completed" tasks={done} probs={null} status="done" onRefresh={onRefresh} />
    </div>
  )
}
