import { useState } from 'react';

export default function SubirEscritura() {
  const [escritura, setEscritura] = useState(null);
  const [plano, setPlano] = useState(null);
  const [texto, setTexto] = useState('');
  const [datos, setDatos] = useState([]);
  const [segmentos, setSegmentos] = useState([]);
  const [comparacion, setComparacion] = useState([]);
  const [cargando, setCargando] = useState(false);

  const handleArchivoChange = (e, tipo) => {
    if (tipo === 'escritura') {
      setEscritura(e.target.files[0]);
    } else if (tipo === 'plano') {
      setPlano(e.target.files[0]);
    }
  };

  const enviarEscritura = async () => {
    if (!escritura) return alert('Selecciona el archivo de escritura');

    const formData = new FormData();
    formData.append('archivo', escritura);

    setCargando(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/extraer-escritura`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setTexto(data.texto_extraido);
      setDatos(data.datos_tecnicos);
    } catch (error) {
      alert('Error al procesar escritura');
    }
    setCargando(false);
  };

  const enviarPlano = async () => {
    if (!plano) return alert('Selecciona el archivo del plano');

    const formData = new FormData();
    formData.append('archivo', plano);

    setCargando(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/extraer-plano`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setSegmentos(data.segmentos_detectados || []);
    } catch (error) {
      alert('Error al procesar plano');
    }
    setCargando(false);
  };

  const compararEscrituraPlano = async () => {
    if (datos.length === 0 || segmentos.length === 0) {
      return alert("Debes analizar primero la escritura y el plano.");
    }

    setCargando(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/comparar-escritura-plano`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          escritura: datos,
          plano: segmentos
        })
      });
      const data = await res.json();
      setComparacion(data.comparacion || []);
    } catch (error) {
      alert("Error al comparar escritura con plano");
    }
    setCargando(false);
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: 20 }}>
      <h2>Subir Escritura y Plano</h2>

      <div style={{ marginBottom: 16 }}>
        <label><strong>Escritura (PDF o imagen):</strong></label>
        <input type="file" accept=".pdf,image/*" onChange={(e) => handleArchivoChange(e, 'escritura')} />
        <button onClick={enviarEscritura} disabled={cargando} style={{ marginTop: 8 }}>
          {cargando ? 'Procesando...' : 'Analizar escritura'}
        </button>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label><strong>Plano (PDF escaneado):</strong></label>
        <input type="file" accept=".pdf" onChange={(e) => handleArchivoChange(e, 'plano')} />
        <button onClick={enviarPlano} disabled={cargando} style={{ marginTop: 8 }}>
          {cargando ? 'Procesando...' : 'Analizar plano'}
        </button>
      </div>

      <div style={{ marginTop: 16 }}>
        <button onClick={compararEscrituraPlano} disabled={cargando || datos.length === 0 || segmentos.length === 0}>
          Comparar escritura con plano
        </button>
      </div>

      {texto && (
        <div style={{ marginTop: 24 }}>
          <h3>Texto extraído de escritura:</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{texto}</pre>
        </div>
      )}

      {datos.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Rumbos y distancias detectados:</h3>
          <ul>
            {datos.map((item, i) => (
              <li key={i}>
                <strong>Rumbo:</strong> {item.rumbo} — <strong>Distancia:</strong> {item.distancia} m
              </li>
            ))}
          </ul>
        </div>
      )}

      {segmentos.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Segmentos detectados en el plano:</h3>
          <ul>
            {segmentos.map((s, i) => (
              <li key={i}>
                ({s.x1}, {s.y1}) → ({s.x2}, {s.y2}) — <strong>Longitud:</strong> {s.longitud_px} px
              </li>
            ))}
          </ul>
        </div>
      )}

      {comparacion.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h3>Resultado de la comparación:</h3>
          <ul>
            {comparacion.map((item, i) => (
              <li key={i} style={{ color: item.coincide ? 'green' : 'red' }}>
                <strong>Escritura:</strong> {item.escritura} <br />
                <strong>Plano:</strong> {item.plano} <br />
                <strong>¿Coincide?</strong> {item.coincide ? '✅ Sí' : '❌ No'}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
