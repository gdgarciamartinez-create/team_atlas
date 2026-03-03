import { useEffect, useState } from 'react'
import { checkHealth } from './api'

export default function Health() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    checkHealth()
      .then(data => setStatus(data.status || (data.ok ? "ok" : "error")))
      .catch(() => setStatus('offline'))
  }, [])

  return (
    <p>
      Backend status: <strong>{status}</strong>
    </p>
  )
}