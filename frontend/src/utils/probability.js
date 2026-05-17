const SLEEP_HOURS_PER_DAY = 8
const FREE_FRACTION = (24 - SLEEP_HOURS_PER_DAY) / 24  // 16/24

export function freeHours(deadlineIso) {
  const hoursRaw = (new Date(deadlineIso) - Date.now()) / 3_600_000
  return Math.max(0, hoursRaw * FREE_FRACTION)
}

export function calculateProbabilities(tasks) {
  // Only pending tasks with both deadline and estimated_hours
  const eligible = tasks.filter(
    t => t.status === 'pending' && t.deadline && t.estimated_hours > 0
  )

  if (eligible.length === 0) return {}

  const F = {}
  eligible.forEach(t => { F[t.id] = freeHours(t.deadline) })

  // Initial estimate: naive single-task probability
  const P = {}
  eligible.forEach(t => {
    P[t.id] = F[t.id] > 0 ? Math.min(1, Math.max(0, 1 - t.estimated_hours / F[t.id])) : 0
  })

  // Iterate to convergence
  for (let iter = 0; iter < 30; iter++) {
    let maxDiff = 0

    eligible.forEach(ti => {
      const Fi = F[ti.id]
      const Ei = ti.estimated_hours
      if (Fi <= 0) { P[ti.id] = 0; return }

      let stolen = 0
      eligible.forEach(tj => {
        if (tj.id === ti.id) return
        const Pj = P[tj.id]
        const Ej = tj.estimated_hours
        // Closed-form: E[time tj steals from ti's window]
        const contribution = Pj * Ej * (Fi - Ej / 2) / Fi
        stolen += Math.max(0, contribution)
      })

      const Tleft = Math.max(0, Fi - stolen)
      const newP = Ei > 0 && Tleft > 0
        ? Math.min(1, Math.max(0, 1 - Ei / Tleft))
        : (Tleft <= 0 ? 0 : 1)

      maxDiff = Math.max(maxDiff, Math.abs(newP - P[ti.id]))
      P[ti.id] = newP
    })

    if (maxDiff < 0.001) break
  }

  return P  // { [task_id]: probability }
}

export function getBucket(p) {
  if (p === null || p === undefined) return null
  if (p > 0.80) return 'safe'
  if (p > 0.60) return 'watch'
  if (p > 0.40) return 'at-risk'
  if (p > 0.20) return 'danger'
  return 'critical'
}

export const BUCKET_COLOR = {
  safe:     '#38a169',
  watch:    '#68d391',
  'at-risk':'#d69e2e',
  danger:   '#ed8936',
  critical: '#e53e3e',
}

const BUCKET_ORDER = ['safe', 'watch', 'at-risk', 'danger', 'critical']

export function bucketDropped(prev, next) {
  if (!prev || !next) return false
  return BUCKET_ORDER.indexOf(next) > BUCKET_ORDER.indexOf(prev)
}
