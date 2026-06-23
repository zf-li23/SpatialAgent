import { Routes, Route } from 'react-router-dom'
import MainLayout from './pages/MainLayout'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />} />
    </Routes>
  )
}
