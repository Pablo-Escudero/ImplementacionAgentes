import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import api from '../api';

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');

  useEffect(() => {
    api.get('/auth/me').then(res => setEmail(res.data.email)).catch(() => {});
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <header className="border-b-2 border-cyber-yellow bg-cyber-panel px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <h1 className="text-cyber-yellow font-bold text-xl tracking-widest">CYBERPUNK RAG</h1>
        <nav className="flex gap-4">
          <Link to="/" className={`tag-label text-sm ${location.pathname === '/' ? 'text-cyber-yellow' : 'text-gray-400'}`}>CHAT</Link>
          <Link to="/documents" className={`tag-label text-sm ${location.pathname === '/documents' ? 'text-cyber-yellow' : 'text-gray-400'}`}>DOCUMENTOS</Link>
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-gray-400 text-sm hidden md:block">{email}</span>
        <button onClick={handleLogout} className="text-cyber-red text-sm font-bold uppercase hover:text-white transition-colors">CERRAR SESIÓN</button>
      </div>
    </header>
  );
}
