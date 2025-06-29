import { useState } from 'react';

export default function SubirEscritura() {
  const [archivo, setArchivo] = useState(null);
  const [texto, setTexto] = useState('');
  const [datos, setDatos] = useState([]);
  const [cargando, setCargando] = useState(false);

  const handleArchivoChange = (e) => {
    setArchivo(e.target.files[0]);
  };

  const enviarArchivo = async () => {
    if (!archivo) return alert('Selecciona un archivo primero');
    const formData = new FormData();
    formData.append('archivo', archivo);
    setCargando(true);
    try {
      const res = await fetch(process.env.REACT_APP_BACKEND_URL + '/extraer-escritura', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setTexto(data.texto_extraido);
      setDatos(data.datos_tecnicos);
    } catch (error) {
      alert('Error al procesar archivo');
    }
    setCargando(false);
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: 20 }}>
      <h2>Subir Escritura</h2>
      <input type="file" accept=".pdf,image/*" onChange={handleArchivoChange} />
      <button onClick={enviarArchivo} disabled={cargando}>
        {cargando ? 'Procesando...' : 'Analizar escritura'}
      </button>
      {texto && <pre style={{ whiteSpace: 'pre-wrap' }}>{texto}</pre>}
      {datos.length > 0 && (
        <ul>
          {datos.map((item, i) => (
            <li key={i}>
              <strong>Rumbo:</strong> {item.rumbo} — <strong>Distancia:</strong> {item.distancia} m
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}