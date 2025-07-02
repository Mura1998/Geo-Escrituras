import { useState } from 'react';

export default function SubirEscritura() {
  const [escritura, setEscritura] = useState(null);
  const [plano, setPlano] = useState(null);
  const [texto, setTexto] = useState('');
  const [datos, setDatos] = useState([]);
  const [segmentos, setSegmentos] = useState([]);
  const [comparacion, setComparacion] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [mensajeReporte, setMensajeReporte] = useState('');
  const [escrituraCargada, setEscrituraCargada] = useState(false);
  const [planoCargado, setPlanoCargado] = useState(false);

  const handleArchivoChange = (e, tipo) => {
    if (tipo === 'escritura') {
      setEscritura(e.target.files[0]);
      setEscrituraCargada(false);
      setPlanoCargado(false);
    } else if (tipo === 'plano') {
      setPlano(e.target.files[0]);
      setPlanoCargado(false);
    }
  };

  const enviarEscritura = async () => {
    if (!escritura) return alert('Selecciona el archivo de escritura');

    const formData = new FormData();
    formData.append('archivo', escritura);

    setCargando(true);
    setMensajeReporte('');
    setEscrituraCargada(false);
    setPlanoCargado(false);

    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/extraer-escritura`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Error procesando escritura");
        return;
      }

      setTexto(data.texto_extraido);
      setDatos(data.datos_tecnicos);
      setEscrituraCargada(true);
    } catch (error) {
      alert('Error al procesar escritura');
    }

    setCargando(false);
  };

  const enviarPlano = async () => {
    if (!plano) return alert('Selecciona el archivo del plano');
    if (!escrituraCargada) return alert('Primero debes cargar correctamente la escritura');

    const formData = new FormData();
    formData.append('archivo', plano);

    setCargando(true);
    setMensajeReporte('');
    setPlanoCargado(false);

    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/extraer-plano`, {
        method: 'POST',
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Error procesando plano");
        return;
      }

      setSegmentos(data.segmentos_detectados || []);
      setPlanoCargado(true);
    } catch (error) {
      alert('Error al procesar plano');
    }

    setCargando(false);
  };

  const descargarReporte = async (comparacionData) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/generar-reporte`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comparacion: comparacionData }),
      });
      if (!res.ok) throw new Error('Error generando reporte');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'reporte_confrontacion.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();

      setMensajeReporte('Reporte PDF descargado exitosamente.');
    } catch (error) {
      alert('Error al descargar el reporte PDF');
    }
  };

  const compararEscrituraPlano = async () => {
    if (datos.length === 0 || segmentos.length === 0) {
      return alert("Debes analizar primero la escritura y el plano.");
    }

    setCargando(true);
    setMensajeReporte('');
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/comparar-escritura-plano`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          escritura: datos,
          plano: segmentos,
        }),
      });
      const data = await res.json();
      setComparacion(data.comparacion || []);

      if (data.comparacion) {
        await descargarReporte(data.comparacion);
      }
    } catch (error) {
      alert("Error al comparar escritura con plano");
    }
    setCargando(false);
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: 20 }}>
      <h2>Subir Escritura y Plano</h2>

      <div style={{ marginBottom: 16 }}>
        <label><strong>Escritura (PDF o imagen):</strong></label><br />
        <input type="file" accept=".pdf,image/*" onChange={(e) => handleArchivoChange(e, 'escritura')} />
        <button onClick={enviarEscritura} disabled={cargando} style={{ marginTop: 8 }}>
          {cargando ? 'Procesando...' : 'Analizar escritura'}
        </button>
        {escrituraCargada && <p style={{ color: 'green' }}>✅ Escritura cargada con éxito</p>}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label><strong>Plano (PDF escaneado):</strong></label><br />
        <input type="file" accept=".pdf" onChange={(e) => handleArchivoChange(e, 'plano')} />
        <button onClick={enviarPlano} disabled={cargando || !escrituraCargada} style={{ marginTop: 8 }}>
          {cargando ? 'Procesando...' : 'Analizar plano'}
        </button>
        {planoCargado && <p style={{ color: 'green' }}>✅ Plano cargado con éxito</p>}
      </div>

      <div style={{ marginTop: 16 }}>
        <button
          onClick={compararEscrituraPlano}
          disabled={!escrituraCargada || !planoCargado || cargando}
        >
          Comparar escritura con plano
        </button>
      </div>

      {mensajeReporte && (
        <div style={{ marginTop: 16, color: 'green', fontWeight: 'bold' }}>
          {mensajeReporte}
        </div>
      )}

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
