import Header from './Header'
import NavSidebar from './NavSidebar'
import MapPage from '../Map/MapPage'
import NodeDetailsPage from '../NodeDetails/NodeDetailsPage'
import { GraphsPage } from '../Graphs'
import { AnalysisPage } from '../Analysis'
import { SettingsPage } from '../Settings'
import { useDataContext } from '../../contexts/DataContext'

export default function Layout() {
  const { currentPage, navigateToPage } = useDataContext()

  const renderPage = () => {
    switch (currentPage) {
      case 'map':
        return <MapPage />
      case 'nodes':
        return <NodeDetailsPage />
      case 'graphs':
        return <GraphsPage />
      case 'analysis':
        return <AnalysisPage />
      case 'settings':
        return <SettingsPage />
      default:
        return <MapPage />
    }
  }

  return (
    <div className="app-layout">
      <NavSidebar currentPage={currentPage} onPageChange={navigateToPage} />
      <main className="main-content">
        <Header />
        <div className="page-content">
          {renderPage()}
        </div>
      </main>
    </div>
  )
}
