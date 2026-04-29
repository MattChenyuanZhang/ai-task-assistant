import { useState, useRef } from 'react'

export default function VoiceInput({ onSubmit, loading }) {
  const [text, setText] = useState('')
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Try Chrome.')
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setText(prev => prev ? prev + ' ' + transcript : transcript)
    }
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)

    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }

  const stopListening = () => {
    recognitionRef.current?.stop()
    setListening(false)
  }

  const handleSubmit = () => {
    if (!text.trim()) return
    onSubmit(text.trim())
    setText('')
  }

  return (
    <div className="voice-input">
      <h2>Add Tasks</h2>
      <p className="hint">Type or speak your tasks, deadlines, and priorities naturally.</p>
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder='e.g. "Finish the report by Friday, high priority. Call John tomorrow morning."'
        rows={4}
        disabled={loading}
      />
      <div className="voice-actions">
        <button
          className={`btn-mic ${listening ? 'recording' : ''}`}
          onClick={listening ? stopListening : startListening}
          disabled={loading}
          title={listening ? 'Stop recording' : 'Start voice input'}
        >
          {listening ? '⏹ Stop' : '🎤 Speak'}
        </button>
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={loading || !text.trim()}
        >
          {loading ? 'Extracting...' : 'Extract & Save Tasks'}
        </button>
      </div>
    </div>
  )
}
