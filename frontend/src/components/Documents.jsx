import { useState, useEffect, useRef } from 'react';
import api from '../api';

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    try {
      const res = await api.get('/documents');
      setDocs(res.data);
    } catch (e) { console.error(e); }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
  };

  const uploadFile = async (file) => {
    if (file.size > 15 * 1024 * 1024) return setError('EL ARCHIVO SUPERA LOS 15 MB');
    const validExts = ['.pdf', '.txt', '.md', '.csv', '.docx'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExts.includes(ext)) return setError('FORMATO NO SOPORTADO (PDF, TXT, MD, CSV, DOCX)');

    setError('');
    setSuccess('');
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSuccess(`DOCUMENTO PROCESADO: ${res.data.chunk_count} FRAGMENTOS EXTRAÍDOS.`);
      fetchDocs();
    } catch (err) {
      const status = err.response?.status;
      if (status === 413) setError('ARCHIVO DEMASIADO GRANDE (413)');
      else if (status === 415) setError('FORMATO NO SOPORTADO (415)');
      else if (status === 422) setError('ARCHIVO SIN TEXTO O INVÁLIDO (422)');
      else setError(err.response?.data?.detail || 'ERROR AL SUBIR EL ARCHIVO');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleDelete = async (id, filename) => {
    if (!window.confirm(`¿ELIMINAR "${filename}" DE LA BASE DE CONOCIMIENTO?`)) return;
    try {
      await api.delete(`/documents/${id}`);
      setDocs(prev => prev.filter(d => d.id !== id));
    } catch (err) {
      alert('ERROR AL ELIMINAR EL DOCUMENTO');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h2 className="text-2xl text-cyber-yellow font-bold border-b-2 border-cyber-yellow pb-2">GESTIÓN DE DOCUMENTOS</h2>

      {/* Upload Zone */}
      <div 
        onDragOver={(e) => e.preventDefault()} 
        onDrop={handleDrop}
        className="cyber-panel border-2 border-dashed border-gray-600 hover:border-cyber-yellow transition-colors p-8 text-center flex flex-col items-center justify-center gap-4 cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
      >
        <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".pdf,.txt,.md,.csv,.docx" />
        <svg className="w-12 h-12 text-cyber-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
        <div>
          <p className="font-bold text-lg">ARRASTRA UN ARCHIVO AQUÍ O HAZ CLIC PARA SELECCIONAR</p>
          <p className="text-gray-400 text-sm">Formatos: PDF, TXT, MD, CSV, DOCX (Máx. 15 MB)</p>
        </div>
        {uploading && <p className="text-cyber-yellow font-bold animate-pulse">PROCESANDO DOCUMENTO...</p>}
      </div>

      {error && <div className="bg-red-900/30 border border-cyber-red text-white p-3 font-bold">{error}</div>}
      {success && <div className="bg-green-900/30 border border-green-500 text-white p-3 font-bold">{success}</div>}

      {/* Table */}
      <div className="cyber-panel overflow-x-auto p-0">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-black/60 text-cyber-yellow tag-label border-b border-gray-700">
              <th className="p-3">NOMBRE</th>
              <th className="p-3">FRAGMENTOS</th>
              <th className="p-3">TAMAÑO</th>
              <th className="p-3">FECHA</th>
              <th className="p-3 text-right">ACCIÓN</th>
            </tr>
          </thead>
          <tbody>
            {docs.map(d => (
              <tr key={d.id} className="border-b border-gray-800 hover:bg-white/5 transition-colors">
                <td className="p-3 font-bold">{d.filename}</td>
                <td className="p-3">{d.chunk_count}</td>
                <td className="p-3">{(d.size_bytes / 1024).toFixed(1)} KB</td>
                <td className="p-3 text-sm text-gray-400">{new Date(d.created_at).toLocaleString()}</td>
                <td className="p-3 text-right">
                  {d.is_owner ? (
                    <button onClick={() => handleDelete(d.id, d.filename)} className="text-cyber-red hover:text-white font-bold text-sm uppercase px-2 py-1 border border-cyber-red hover:bg-cyber-red transition-all">ELIMINAR</button>
                  ) : (
                    <span className="text-gray-600 text-xs">NO AUTORIZADO</span>
                  )}
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr><td colSpan="5" className="p-6 text-center text-gray-500">NO HAY DOCUMENTOS CARGADOS</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
