// src/components/Sidebar.jsx
import { Link } from 'react-router-dom';

export default function Sidebar() {
  return (
    <aside className="w-64 fixed h-screen bg-[#0a1628] border-r border-[#1a2d4a] p-6">
      <h1 className="text-2xl font-bold text-blue-500 mb-8">Zunto</h1>

      <nav className="space-y-2">
        <Link to="/dashboard" className="block px-4 py-3 rounded-lg bg-blue-600">
          Admin Dashboard
        </Link>
        <Link to="/shop" className="block px-4 py-3 rounded-lg hover:bg-[#1a2d4a]">
          Shop
        </Link>
      </nav>
    </aside>
  );
}
