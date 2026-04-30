import { useState } from 'react'

export default function AddTaskModal({ onClose, onSubmit }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!text.trim()) return
    setLoading(true)
    await onSubmit(text)
    setLoading(false)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Add Task</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <p className="modal-hint">Describe your task in plain English. HAL will extract the details.</p>
        <textarea
          className="modal-textarea"
          placeholder="e.g. Finish the report by Friday at 5pm, high priority, about 3 hours of work"
          value={text}
          onChange={e => setText(e.target.value)}
          rows={4}
          autoFocus
        />
        <div className="modal-actions">
          <button className="btn-ghost-modal" onClick={onClose}>Cancel</button>
          <button className="btn-submit" onClick={handleSubmit} disabled={loading || !text.trim()}>
            {loading ? 'Adding...' : 'Add'}
          </button>
        </div>
      </div>
    </div>
  )
}
