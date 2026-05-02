import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './components/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import './App.css'

function App() {
  return (
    <Routes>
      <Route element={<Navigate to="/dashboard" replace />} path="/" />
      <Route element={<Login />} path="/login" />
      <Route element={<Register />} path="/register" />
      <Route element={<ProtectedRoute />}>
        <Route element={<Dashboard />} path="/dashboard" />
      </Route>
      <Route element={<Navigate to="/dashboard" replace />} path="*" />
    </Routes>
  )
}

export default App
