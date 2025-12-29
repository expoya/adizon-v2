import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Users from './pages/Users';
import Approvals from './pages/Approvals';
import Dashboard from './pages/Dashboard';
import './index.css';

function Navigation() {
  const location = useLocation();
  
  const getLinkClasses = (path: string) => {
    const isActive = location.pathname === path;
    return isActive
      ? "border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium";
  };

  return (
    <nav className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-2xl font-bold text-indigo-600">Adizon Admin</h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link to="/" className={getLinkClasses('/')}>
                Dashboard
              </Link>
              <Link to="/users" className={getLinkClasses('/users')}>
                Users
              </Link>
              <Link to="/approvals" className={getLinkClasses('/approvals')}>
                Approvals
              </Link>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        {/* Navigation */}
        <Navigation />

        {/* Main Content */}
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/approvals" element={<Approvals />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
