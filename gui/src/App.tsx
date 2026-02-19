import { Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import DashboardPage from './pages/DashboardPage'
import EffectsPage from './pages/EffectsPage'
import LibraryPage from './pages/LibraryPage'
import ProjectsPage from './pages/ProjectsPage'

function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<DashboardPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="effects" element={<EffectsPage />} />
      </Route>
    </Routes>
  )
}

export default App
