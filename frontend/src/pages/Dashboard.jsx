import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'

import api from '../api/axios'
import { useAuth } from '../context/auth'

function Dashboard() {
  const [keys, setKeys] = useState([])
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState(null)
  const [isCreating, setIsCreating] = useState(false)
  const { logout } = useAuth()

  const fetchKeys = async () => {
    setError('')

    try {
      const response = await api.get('/keys/')
      setKeys(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load API keys')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isActive = true

    async function loadInitialKeys() {
      try {
        const response = await api.get('/keys/')

        if (isActive) {
          setKeys(response.data)
        }
      } catch (err) {
        if (isActive) {
          setError(err.response?.data?.detail || 'Unable to load API keys')
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    loadInitialKeys()

    return () => {
      isActive = false
    }
  }, [])

  const handleCreateKey = async (event) => {
    event.preventDefault()
    setError('')
    setIsCreating(true)

    try {
      const response = await api.post('/keys/', { name: newKeyName })
      setCreatedKey(response.data)
      setNewKeyName('')
      setIsCreateOpen(false)
      await fetchKeys()
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to generate API key')
    } finally {
      setIsCreating(false)
    }
  }

  const handleRevokeKey = async (keyId) => {
    setError('')

    try {
      await api.delete(`/keys/${keyId}`)
      setKeys((currentKeys) => currentKeys.filter((key) => key.id !== keyId))
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to revoke API key')
    }
  }

  return (
    <main className="dashboard-page">
      <header className="topbar">
        <div>
          <p className="eyebrow">API Key Manager</p>
          <h1>Dashboard</h1>
        </div>
        <button className="secondary-button" onClick={logout} type="button">
          Sign out
        </button>
      </header>

      <section className="toolbar" aria-label="API key actions">
        <div>
          <h2>API keys</h2>
          <p>{keys.length} active {keys.length === 1 ? 'key' : 'keys'}</p>
        </div>
        <button className="primary-button icon-button" onClick={() => setIsCreateOpen(true)} type="button">
          <Plus aria-hidden="true" size={18} />
          Generate New Key
        </button>
      </section>

      {error ? <p className="error-message">{error}</p> : null}

      <section className="key-list" aria-label="Active API keys">
        {isLoading ? (
          <p className="empty-state">Loading keys...</p>
        ) : keys.length > 0 ? (
          keys.map((key) => (
            <article className="key-row" key={key.id}>
              <div>
                <h3>{key.name}</h3>
                <code>{key.key_prefix}...</code>
              </div>
              <button
                className="danger-button icon-only-button"
                onClick={() => handleRevokeKey(key.id)}
                title={`Revoke ${key.name}`}
                type="button"
              >
                <Trash2 aria-hidden="true" size={18} />
                <span className="sr-only">Revoke {key.name}</span>
              </button>
            </article>
          ))
        ) : (
          <p className="empty-state">No active API keys</p>
        )}
      </section>

      {isCreateOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" aria-labelledby="new-key-title" role="dialog" aria-modal="true">
            <h2 id="new-key-title">Generate key</h2>
            <form className="form-stack" onSubmit={handleCreateKey}>
              <label>
                Name
                <input
                  autoFocus
                  maxLength={100}
                  minLength={1}
                  onChange={(event) => setNewKeyName(event.target.value)}
                  required
                  value={newKeyName}
                />
              </label>
              <div className="modal-actions">
                <button className="secondary-button" onClick={() => setIsCreateOpen(false)} type="button">
                  Cancel
                </button>
                <button className="primary-button" disabled={isCreating} type="submit">
                  {isCreating ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {createdKey ? (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" aria-labelledby="created-key-title" role="dialog" aria-modal="true">
            <h2 id="created-key-title">Key generated</h2>
            <p className="warning-text">
              Copy this key now. You will not be able to view it again.
            </p>
            <code className="raw-key">{createdKey.api_key}</code>
            <div className="modal-actions">
              <button
                className="secondary-button"
                onClick={() => navigator.clipboard?.writeText(createdKey.api_key)}
                type="button"
              >
                Copy
              </button>
              <button className="primary-button" onClick={() => setCreatedKey(null)} type="button">
                Done
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  )
}

export default Dashboard
