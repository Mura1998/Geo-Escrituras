import { useState } from 'react';

export default function SubirEscritura() {
  const [escritura, setEscritura] = useState(null);
  const [plano, setPlano] = useState(null);
  const [texto, setTexto] = useState('');
  const [datos, setDatos] = useState([]);
  const [cargando, setCargando] = useState(false);

  const handleArchivoChange = (e, tipo) => {
    if (tipo === 'escritura') {
      setEscritura(e.target.files[0]);
    } else if (tipo === 'plano') {
      setPlano(e.target.files[0]);
    }
  };

  const enviarEscritura = async () => {
    if (!escritura) return alert('Selecciona el archivo de escritura primero');

    const formData = new FormData();
    formData.append('archivo', escritura);

    setCargando(true);
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/extraer-escritura`, {
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
      <h2>Subir Escritura y Plano</h2>

      {/* Entrada escritura */}
      <div style={{ marginBottom: 16 }}>
        <label><strong>Archivo de escritura (PDF o imagen):</strong></label>
        <input type="file" accept=".pdf,image/*" onChange={(e) => handleArchivoChange(e, 'escritura')} />
      </div>

      {/* Entrada plano */}
      <div style={{ marginBottom: 16 }}>
        <label><strong>Archivo del plano (PDF, imagen o DXF):</strong></label>
        <input type="file" accept=".pdf,image/*,.dxf" onChange={(e) => handleArchivoChange(e, 'plano')} />
      </div>

      {/* Botón para analizar solo escritura */}
      <button onClick={enviarEscritura} disabled={cargando}>
        {cargando ? 'Procesando...' : 'Analizar escritura'}
      </button>

      {/* Resultados */}
      {texto && (
        <div style={{ marginTop: 24 }}>
          <h3>Texto extraído:</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{texto}</pre>
        </div>
      )}

      {datos.length > 0 && (
        <div style={{ marginTop: 24 }}>
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
