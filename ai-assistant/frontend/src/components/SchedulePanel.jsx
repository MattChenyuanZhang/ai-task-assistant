import { useState, useEffect } from 'react'
import { fetchTodaySchedule, createScheduleBlock, deleteScheduleBlock } from '../api/client'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function isActiveNow(block) {
  const now = new Date()
  const [sh, sm] = block.start_time.split(':').map(Number)
  const [eh, em] = block.end_time.split(':').map(Number)
  const nowMins = now.getHours() * 60 + now.getMinutes()
  return nowMins >= sh * 60 + sm && nowMins < eh * 60 + em
}

function fmtTime(hhmm) {
  const [h, m] = hhmm.split(':').map(Number)
  const ampm = h >= 12 ? 'PM' : 'AM'
  return `${h % 12 || 12}:${m.toString().padStart(2, '0')} ${ampm}`
}

const EMPTY_FORM = { title: '', start_time: '', end_time: '', recurrence: 'daily', day_of_week: 0, date: '' }

export default function SchedulePanel() {
  const [blocks, setBlocks] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    const data = await fetchTodaySchedule()
    setBlocks(data)
  }

  useEffect(() => { load() }, [])

  const set = (key, value) => setForm(f => ({ ...f, [key]: value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createScheduleBlock({
        title: form.title,
        start_time: form.start_time,
        end_time: form.end_time,
        recurrence: form.recurrence,
        day_of_week: form.recurrence === 'weekly' ? Number(form.day_of_week) : null,
        date: form.recurrence === 'none' ? form.date : null,
      })
      setForm(EMPTY_FORM)
      setShowForm(false)
      await load()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    await deleteScheduleBlock(id)
    await load()
  }

  return (
    <div className="schedule-panel">
      <div className="schedule-header">
        <h2>Today's Schedule</h2>
        <button className="btn-secondary" onClick={() => setShowForm(v => !v)}>
          {showForm ? 'Cancel' : '+ Block'}
        </button>
      </div>

      {showForm && (
        <form className="schedule-form" onSubmit={handleSubmit}>
          <input
            className="schedule-input"
            placeholder="Title (e.g. CS101, Lunch, Sleep)"
            value={form.title}
            onChange={e => set('title', e.target.value)}
            required
          />
          <div className="time-row">
            <input type="time" value={form.start_time} onChange={e => set('start_time', e.target.value)} required />
            <span className="time-sep">to</span>
            <input type="time" value={form.end_time} onChange={e => set('end_time', e.target.value)} required />
          </div>
          <select value={form.recurrence} onChange={e => set('recurrence', e.target.value)}>
            <option value="daily">Every day</option>
            <option value="weekly">Weekly (same day)</option>
            <option value="none">One-time</option>
          </select>
          {form.recurrence === 'weekly' && (
            <select value={form.day_of_week} onChange={e => set('day_of_week', e.target.value)}>
              {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
            </select>
          )}
          {form.recurrence === 'none' && (
            <input type="date" value={form.date} onChange={e => set('date', e.target.value)} required />
          )}
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </form>
      )}

      {blocks.length === 0 ? (
        <p className="empty">No events today. Add classes, meals, or sleep blocks.</p>
      ) : (
        <div className="block-list">
          {blocks.map(b => {
            const active = isActiveNow(b)
            return (
              <div key={b.id} className={`schedule-block-item${active ? ' active' : ''}`}>
                <div className="block-left">
                  {active && <span className="now-badge">NOW</span>}
                  <span className="block-title">{b.title}</span>
                  <span className="block-time">{fmtTime(b.start_time)} – {fmtTime(b.end_time)}</span>
                </div>
                <button className="btn-danger" onClick={() => handleDelete(b.id)} title="Remove">✕</button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
