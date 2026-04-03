import { Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import DashboardPage from './pages/DashboardPage'
import EffectsPage from './pages/EffectsPage'
import LibraryPage from './pages/LibraryPage'
import PreviewPage from './pages/PreviewPage'
import ProjectsPage from './pages/ProjectsPage'
import RenderPage from './pages/RenderPage'
import TimelinePage from './pages/TimelinePage'

function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<DashboardPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="effects" element={<EffectsPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="preview" element={<PreviewPage />} />
        <Route path="render" element={<RenderPage />} />
      </Route>
    </Routes>
  )
}

export default App
