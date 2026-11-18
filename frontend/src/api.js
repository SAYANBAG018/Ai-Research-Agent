
const API_URL = (
  import.meta.env.VITE_API_URL || 'http://localhost:8000'
).replace(/\/$/, '')

async function handleResponse(response) {
  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      typeof payload.detail === 'string'
        ? payload.detail
        : payload.message || `Request failed (${response.status})`

    throw new Error(message)
  }

  return payload
}

export async function startResearch(topic) {
  if (!topic || topic.trim().length < 3) {
    throw new Error('Please enter a research topic with at least 3 characters.')
  }

  let response

  try {
    response = await fetch(`${API_URL}/api/research`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic: topic.trim(),
      }),
    })
  } catch {
    throw new Error(
      'Could not connect to the backend. Make sure your FastAPI server is running on port 8000.',
    )
  }

  return handleResponse(response)
}

export function downloadUrl(filePath, format) {
  if (!filePath) {
    throw new Error('The requested report file is not available.')
  }

  const allowedFormats = ['markdown', 'pdf']

  if (!allowedFormats.includes(format)) {
    throw new Error('Unsupported download format.')
  }

  const params = new URLSearchParams({
    path: filePath,
  })

  return `${API_URL}/api/download/${format}?${params.toString()}`
}

export { API_URL }
