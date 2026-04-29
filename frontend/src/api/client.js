import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
})

export const fetchTasks = (status) =>
  api.get('/api/tasks', { params: status ? { status } : {} }).then(r => r.data)

export const createTask = (task) =>
  api.post('/api/tasks', task).then(r => r.data)

export const updateTask = (id, data) =>
  api.patch(`/api/tasks/${id}`, data).then(r => r.data)

export const deleteTask = (id) =>
  api.delete(`/api/tasks/${id}`)

export const fetchUrgentTasks = () =>
  api.get('/api/tasks/urgent').then(r => r.data)

export const extractTasks = (text) =>
  api.post('/api/extract', { text }).then(r => r.data)

export const fetchAdvice = () =>
  api.post('/api/advice').then(r => r.data)

export const fetchTodaySchedule = () =>
  api.get('/api/schedule/today').then(r => r.data)

export const createScheduleBlock = (block) =>
  api.post('/api/schedule', block).then(r => r.data)

export const deleteScheduleBlock = (id) =>
  api.delete(`/api/schedule/${id}`)
