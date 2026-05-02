import { useEffect, useMemo, useState } from 'react'
import {
  Check,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Users,
  X,
} from 'lucide-react'

import api from '../api/axios'
import { useAuth } from '../context/auth'

const tabs = [
  { id: 'my-keys', label: 'My keys', icon: KeyRound },
  { id: 'users', label: 'Users', icon: Users, adminOnly: true },
  { id: 'all-keys', label: 'All keys', icon: ShieldCheck, adminOnly: true },
]

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function Dashboard() {
  const [currentUser, setCurrentUser] = useState(null)
  const [keys, setKeys] = useState([])
  const [allKeys, setAllKeys] = useState([])
  const [users, setUsers] = useState([])
  const [activeTab, setActiveTab] = useState('my-keys')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState(null)
  const [editingKey, setEditingKey] = useState(null)
  const [editingName, setEditingName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const { logout } = useAuth()

  const isAdmin = currentUser?.role === 'admin'
  const visibleTabs = tabs.filter((tab) => !tab.adminOnly || isAdmin)

  const usersById = useMemo(
    () => new Map(users.map((user) => [user.id, user])),
    [users],
  )

  const stats = useMemo(() => {
    const activeAllKeys = allKeys.filter((key) => !key.is_revoked)

    return {
      myKeys: keys.length,
      users: users.length,
      allActiveKeys: isAdmin ? activeAllKeys.length : keys.length,
      revokedKeys: isAdmin ? allKeys.filter((key) => key.is_revoked).length : 0,
    }
  }, [allKeys, isAdmin, keys.length, users.length])

  const loadDashboard = async () => {
    setError('')
    setIsLoading(true)

    try {
      const profileResponse = await api.get('/auth/me')
      const profile = profileResponse.data
      setCurrentUser(profile)

      const keyResponse = await api.get('/keys/')
      setKeys(keyResponse.data)

      if (profile.role === 'admin') {
        const [usersResponse, allKeysResponse] = await Promise.all([
          api.get('/admin/users'),
          api.get('/keys/admin/all'),
        ])
        setUsers(usersResponse.data)
        setAllKeys(allKeysResponse.data)
      } else {
        setUsers([])
        setAllKeys([])
        setActiveTab('my-keys')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load dashboard')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isActive = true

    async function loadInitialDashboard() {
      setIsLoading(true)
      try {
        const profileResponse = await api.get('/auth/me')
        const profile = profileResponse.data
        const keyResponse = await api.get('/keys/')

        if (!isActive) {
          return
        }

        setCurrentUser(profile)
        setKeys(keyResponse.data)

        if (profile.role === 'admin') {
          const [usersResponse, allKeysResponse] = await Promise.all([
            api.get('/admin/users'),
            api.get('/keys/admin/all'),
          ])

          if (isActive) {
            setUsers(usersResponse.data)
            setAllKeys(allKeysResponse.data)
          }
        }
      } catch (err) {
        if (isActive) {
          setError(err.response?.data?.detail || 'Unable to load dashboard')
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    loadInitialDashboard()

    return () => {
      isActive = false
    }
  }, [])

  const handleCreateKey = async (event) => {
    event.preventDefault()
    setError('')
    setIsSaving(true)

    try {
      const response = await api.post('/keys/', { name: newKeyName })
      setCreatedKey(response.data)
      setNewKeyName('')
      setIsCreateOpen(false)
      await loadDashboard()
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to generate API key')
    } finally {
      setIsSaving(false)
    }
  }

  const openRenameModal = (key) => {
    setEditingKey(key)
    setEditingName(key.name)
  }

  const handleRenameKey = async (event) => {
    event.preventDefault()
    setError('')
    setIsSaving(true)

    try {
      await api.patch(`/keys/${editingKey.id}`, { name: editingName })
      setEditingKey(null)
      setEditingName('')
      await loadDashboard()
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to rename API key')
    } finally {
      setIsSaving(false)
    }
  }

  const handleRevokeKey = async (keyId) => {
    setError('')

    try {
      await api.delete(`/keys/${keyId}`)
      await loadDashboard()
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to revoke API key')
    }
  }

  const handleRoleChange = async (userId, role) => {
    setError('')

    try {
      await api.patch(`/admin/users/${userId}/role`, { role })
      await loadDashboard()
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update user role')
    }
  }

  const renderKeyRows = (items, showOwner = false, includeRevoked = false) => {
    const visibleKeys = includeRevoked ? items : items.filter((key) => !key.is_revoked)

    if (isLoading) {
      return <p className="empty-state">Loading keys...</p>
    }

    if (visibleKeys.length === 0) {
      return <p className="empty-state">No API keys found</p>
    }

    return visibleKeys.map((key) => {
      const owner = usersById.get(key.user_id)

      return (
        <article className="data-row key-row" key={key.id}>
          <div className="row-main">
            <div className="row-title-line">
              <h3>{key.name}</h3>
              <span className={key.is_revoked ? 'status-pill revoked' : 'status-pill active'}>
                {key.is_revoked ? 'Revoked' : 'Active'}
              </span>
            </div>
            <div className="row-meta">
              <code>{key.key_prefix}...</code>
              {showOwner ? <span>{owner?.email || key.user_id}</span> : null}
              <span>{formatDate(key.created_at)}</span>
            </div>
          </div>
          {!key.is_revoked ? (
            <div className="row-actions">
              <button
                className="secondary-button icon-only-button"
                onClick={() => openRenameModal(key)}
                title={`Rename ${key.name}`}
                type="button"
              >
                <Pencil aria-hidden="true" size={18} />
                <span className="sr-only">Rename {key.name}</span>
              </button>
              <button
                className="danger-button icon-only-button"
                onClick={() => handleRevokeKey(key.id)}
                title={`Revoke ${key.name}`}
                type="button"
              >
                <Trash2 aria-hidden="true" size={18} />
                <span className="sr-only">Revoke {key.name}</span>
              </button>
            </div>
          ) : null}
        </article>
      )
    })
  }

  return (
    <main className="dashboard-page">
      <header className="topbar">
        <div>
          <p className="eyebrow">API Key Manager</p>
          <h1>Dashboard</h1>
          {currentUser ? (
            <p className="user-line">
              {currentUser.email}
              <span>{currentUser.role}</span>
            </p>
          ) : null}
        </div>
        <div className="topbar-actions">
          <button className="secondary-button icon-button" onClick={loadDashboard} type="button">
            <RefreshCw aria-hidden="true" size={18} />
            Refresh
          </button>
          <button className="secondary-button" onClick={logout} type="button">
            Sign out
          </button>
        </div>
      </header>

      <section className="stats-grid" aria-label="Dashboard summary">
        <div className="stat-panel">
          <span>My active keys</span>
          <strong>{stats.myKeys}</strong>
        </div>
        <div className="stat-panel">
          <span>{isAdmin ? 'All active keys' : 'Role'}</span>
          <strong>{isAdmin ? stats.allActiveKeys : currentUser?.role || '-'}</strong>
        </div>
        {isAdmin ? (
          <>
            <div className="stat-panel">
              <span>Users</span>
              <strong>{stats.users}</strong>
            </div>
            <div className="stat-panel">
              <span>Revoked keys</span>
              <strong>{stats.revokedKeys}</strong>
            </div>
          </>
        ) : null}
      </section>

      <nav className="tab-list" aria-label="Dashboard views">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              className={activeTab === tab.id ? 'tab-button active' : 'tab-button'}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              <Icon aria-hidden="true" size={18} />
              {tab.label}
            </button>
          )
        })}
      </nav>

      {error ? <p className="error-message">{error}</p> : null}

      {activeTab === 'my-keys' ? (
        <>
          <section className="toolbar" aria-label="API key actions">
            <div>
              <h2>My API keys</h2>
              <p>{keys.length} active {keys.length === 1 ? 'key' : 'keys'}</p>
            </div>
            <button className="primary-button icon-button" onClick={() => setIsCreateOpen(true)} type="button">
              <Plus aria-hidden="true" size={18} />
              Generate key
            </button>
          </section>
          <section className="data-list" aria-label="My active API keys">
            {renderKeyRows(keys)}
          </section>
        </>
      ) : null}

      {activeTab === 'users' && isAdmin ? (
        <>
          <section className="toolbar" aria-label="User management">
            <div>
              <h2>Users</h2>
              <p>{users.length} registered {users.length === 1 ? 'user' : 'users'}</p>
            </div>
          </section>
          <section className="data-list" aria-label="Users">
            {isLoading ? (
              <p className="empty-state">Loading users...</p>
            ) : users.length > 0 ? (
              users.map((user) => (
                <article className="data-row" key={user.id}>
                  <div className="row-main">
                    <div className="row-title-line">
                      <h3>{user.email}</h3>
                      <span className={user.role === 'admin' ? 'status-pill admin' : 'status-pill'}>
                        {user.role}
                      </span>
                    </div>
                    <div className="row-meta">
                      <span>Joined {formatDate(user.created_at)}</span>
                    </div>
                  </div>
                  <select
                    aria-label={`Role for ${user.email}`}
                    disabled={user.id === currentUser?.id}
                    onChange={(event) => handleRoleChange(user.id, event.target.value)}
                    value={user.role}
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </article>
              ))
            ) : (
              <p className="empty-state">No users found</p>
            )}
          </section>
        </>
      ) : null}

      {activeTab === 'all-keys' && isAdmin ? (
        <>
          <section className="toolbar" aria-label="All API keys">
            <div>
              <h2>All API keys</h2>
              <p>{allKeys.length} total {allKeys.length === 1 ? 'key' : 'keys'}</p>
            </div>
          </section>
          <section className="data-list" aria-label="All API keys">
            {renderKeyRows(allKeys, true, true)}
          </section>
        </>
      ) : null}

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
                  <X aria-hidden="true" size={18} />
                  Cancel
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  <Plus aria-hidden="true" size={18} />
                  {isSaving ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {editingKey ? (
        <div className="modal-backdrop" role="presentation">
          <section className="modal" aria-labelledby="rename-key-title" role="dialog" aria-modal="true">
            <h2 id="rename-key-title">Rename key</h2>
            <form className="form-stack" onSubmit={handleRenameKey}>
              <label>
                Name
                <input
                  autoFocus
                  maxLength={100}
                  minLength={1}
                  onChange={(event) => setEditingName(event.target.value)}
                  required
                  value={editingName}
                />
              </label>
              <div className="modal-actions">
                <button className="secondary-button" onClick={() => setEditingKey(null)} type="button">
                  <X aria-hidden="true" size={18} />
                  Cancel
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  <Check aria-hidden="true" size={18} />
                  {isSaving ? 'Saving...' : 'Save'}
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
