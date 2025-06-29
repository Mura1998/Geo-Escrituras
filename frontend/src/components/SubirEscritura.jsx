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
      const res = await fetch('http://localhost:5000/extraer-escritura', {
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
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h2 className="text-2xl font-semibold">Subir Escritura</h2>
      <input type="file" accept=".pdf,image/*" onChange={handleArchivoChange} />
      <button onClick={enviarArchivo} className="bg-blue-600 text-white px-4 py-2 rounded">
        {cargando ? 'Procesando...' : 'Analizar escritura'}
      </button>
      {texto && <div className="mt-6 bg-gray-50 border p-4"><h3>Texto extraído:</h3><pre>{texto}</pre></div>}
      {datos.length > 0 && (
        <div className="mt-6 bg-white border p-4">
          <h3>Datos técnicos detectados:</h3>
          <ul>
            {datos.map((item, i) => (
              <li key={i}>
                <strong>Rumbo:</strong> {item.rumbo} — <strong>Distancia:</strong> {item.distancia} m
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}