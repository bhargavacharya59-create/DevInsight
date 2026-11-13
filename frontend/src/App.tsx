import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import TopNav from './components/layout/TopNav';
import DemoBanner from './components/ui/DemoBanner';
import Overview from './pages/Overview';
import LiveMonitoring from './pages/LiveMonitoring';
import Incidents from './pages/Incidents';
import IncidentDetail from './pages/IncidentDetail';
import RCAPage from './pages/RCAPage';
import MetricsExplorer from './pages/MetricsExplorer';
import LogsExplorer from './pages/LogsExplorer';
import ServiceMap from './pages/ServiceMap';
import AIAssistant from './pages/AIAssistant';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen overflow-hidden">
        <DemoBanner />
        <div className="flex flex-1 min-h-0">
          <Sidebar />
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <TopNav monitoringMode="demo" isDemo={true} />
            <main className="flex-1 overflow-y-auto">
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/monitoring" element={<LiveMonitoring />} />
                <Route path="/incidents" element={<Incidents />} />
                <Route path="/incidents/:id" element={<IncidentDetail />} />
                <Route path="/rca" element={<RCAPage />} />
                <Route path="/metrics" element={<MetricsExplorer />} />
                <Route path="/logs" element={<LogsExplorer />} />
                <Route path="/service-map" element={<ServiceMap />} />
                <Route path="/ai-assistant" element={<AIAssistant />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </main>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}
