export default function NotificationBanner({ urgentTasks, onDismiss }) {
  if (!urgentTasks || urgentTasks.length === 0) return null

  return (
    <div className="notification-banner">
      <div className="notif-content">
        <span className="notif-icon">⚠️</span>
        <div className="notif-tasks">
          <strong>Upcoming deadlines:</strong>
          {urgentTasks.map(t => (
            <span key={t.id} className="notif-task">
              {t.title} — <em>{t.hours_left}h left</em>
            </span>
          ))}
        </div>
      </div>
      <button className="notif-dismiss" onClick={onDismiss}>✕</button>
    </div>
  )
}
