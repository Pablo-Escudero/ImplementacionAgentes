import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const expired = searchParams.get('expired');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.includes('@')) return setError('CORREO INVÁLIDO');
    if (password.length < 8) return setError('LA CONTRASEÑA DEBE TENER MÍNIMO 8 CARACTERES');

    try {
      if (isLogin) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        const res = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        localStorage.setItem('token', res.data.access_token);
        navigate('/');
      } else {
        await api.post('/auth/register', { email, password });
        setIsLogin(true);
        setError('REGISTRO EXITOSO. INICIA SESIÓN.');
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) setError(detail.map(d => d.msg).join(', ').toUpperCase());
      else setError((detail || 'ERROR DE CONEXIÓN').toUpperCase());
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-4xl flex flex-col md:flex-row shadow-2xl">
        {/* Banda amarilla izquierda */}
        <div className="bg-cyber-yellow w-full md:w-1/3 p-8 flex flex-col justify-between relative overflow-hidden" style={{ clipPath: 'polygon(0 0, 100% 0, 90% 100%, 0 100%)' }}>
          <div className="text-black font-bold text-3xl md:text-5xl leading-none tracking-tighter" style={{ fontFamily: 'Orbitron' }}>
            CYBER<br/>PUNK<br/>2077
          </div>
          <div className="text-black/50 text-sm mt-4 font-bold uppercase tracking-widest">KNOWLEDGE BASE ACCESS</div>
        </div>

        {/* Formulario */}
        <div className="bg-cyber-panel p-8 w-full md:w-2/3 cyber-panel">
          <div className="flex gap-4 mb-8 border-b border-gray-700 pb-2">
            <button onClick={() => { setIsLogin(true); setError(''); }} className={`tag-label pb-2 ${isLogin ? 'text-cyber-yellow border-b-2 border-cyber-yellow' : 'text-gray-400'}`}>LOGIN</button>
            <button onClick={() => { setIsLogin(false); setError(''); }} className={`tag-label pb-2 ${!isLogin ? 'text-cyber-yellow border-b-2 border-cyber-yellow' : 'text-gray-400'}`}>REGISTRO</button>
          </div>

          {expired && <div className="bg-red-900/30 border border-cyber-red text-white p-2 mb-4 text-sm font-bold">SESIÓN EXPIRADA</div>}
          {error && <div className="bg-red-900/30 border border-cyber-red text-white p-2 mb-4 text-sm font-bold">{error}</div>}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <label className="tag-label bg-cyber-yellow text-black px-2 py-1 text-sm w-32 text-center">CORREO</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="cyber-input flex-1" placeholder="agent@cyberpunk.net" required />
            </div>
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <label className="tag-label bg-cyber-yellow text-black px-2 py-1 text-sm w-32 text-center">CONTRASEÑA</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="cyber-input flex-1" placeholder="********" required />
            </div>
            <button type="submit" className="cyber-button py-3 mt-4 text-lg w-full">{isLogin ? 'ACCEDER' : 'REGISTRARSE'}</button>
          </form>
        </div>
      </div>
    </div>
  );
}
