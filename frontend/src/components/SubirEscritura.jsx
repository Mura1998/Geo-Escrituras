// (Dejamos tu importación y configuración inicial igual)
import { useState } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
console.log('BACKEND_URL:', BACKEND_URL);

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

  const fetchConError = async (url, opciones = {}) => {
    try {
      const res = await fetch(url, opciones);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Error inesperado");
      return data;
    } catch (err) {
      console.error('❌ Error al hacer fetch:', err.message);
      toast.error(err.message);
      throw err;
    }
  };

  const handleArchivoChange = (e, tipo) => {
    const archivo = e.target.files[0];
    if (tipo === 'escritura') {
      console.log('📄 Escritura seleccionada:', archivo);
      setEscritura(archivo);
      setEscrituraCargada(false);
      setPlanoCargado(false);
    } else if (tipo === 'plano') {
      console.log('📐 Plano seleccionado:', archivo);
      setPlano(archivo);
      setPlanoCargado(false);
    }
  };

  const enviarEscritura = async () => {
    if (!escritura) return toast.warn('Selecciona el archivo de escritura');

    const formData = new FormData();
    formData.append('file', escritura);

    setCargando(true);
    setMensajeReporte('');
    setEscrituraCargada(false);
    setPlanoCargado(false);

    try {
      const data = await fetchConError(`${BACKEND_URL}/extraer-escritura`, {
        method: 'POST',
        body: formData
      });

      console.log('✅ Texto extraído:', data.texto_extraido);
      console.log('📐 Datos técnicos extraídos:', data.datos_tecnicos);

      setTexto(data.texto_extraido || '');
      setDatos(data.datos_tecnicos || []);
      setEscrituraCargada(true);
      toast.success('✅ Escritura cargada con éxito');
    } catch (err) {
      console.error('❌ Falló al procesar escritura:', err);
    }

    setCargando(false);
  };

  const testUpload = async () => {
    if (!escritura) return toast.warn('Selecciona el archivo de escritura');

    const formData = new FormData();
    formData.append('file', escritura);

    try {
      const res = await fetch(`${BACKEND_URL}/test-upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error inesperado');
      toast.success(data.mensaje);
    } catch (error) {
      console.error('❌ Fallo en test-upload:', error.message);
      toast.error(error.message);
    }
  };

  const enviarPlano = async () => {
    if (!plano) return toast.warn('Selecciona el archivo del plano');
    if (!escrituraCargada) return toast.warn('Primero debes cargar la escritura');

    const formData = new FormData();
    formData.append('file', plano);

    setCargando(true);
    setMensajeReporte('');
    setPlanoCargado(false);

    try {
      const data = await fetchConError(`${BACKEND_URL}/extraer-plano`, {
        method: 'POST',
        body: formData
      });

      console.log('📏 Segmentos detectados:', data.segmentos_detectados);

      setSegmentos(data.segmentos_detectados || []);
      setPlanoCargado(true);
      toast.success('✅ Plano cargado con éxito');
    } catch (err) {
      console.error('❌ Falló al procesar plano:', err);
    }

    setCargando(false);
  };

  const descargarReporte = async (comparacionData) => {
    try {
      console.log('📤 Enviando comparación para generar reporte...');
      const res = await fetch(`${BACKEND_URL}/generar-reporte`, {
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

      setMensajeReporte('📄 Reporte PDF descargado exitosamente.');
    } catch (error) {
      console.error('❌ Error al generar o descargar reporte:', error);
      toast.error('❌ Error al descargar el reporte PDF');
    }
  };

  const compararEscrituraPlano = async () => {
    if (!escrituraCargada || !planoCargado || !Array.isArray(datos) || datos.length === 0 || !Array.isArray(segmentos) || segmentos.length === 0) {
      return toast.warn("Debes analizar primero la escritura y el plano.");
    }

    setCargando(true);
    setMensajeReporte('');

    try {
      console.log('📊 Comparando escritura y plano...');
      const data = await fetchConError(`${BACKEND_URL}/comparar-escritura-plano`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          escritura: datos,
          plano: segmentos,
        }),
      });

      console.log('📈 Resultado comparación:', data.comparacion);

      setComparacion(data.comparacion || []);
      if (data.comparacion) await descargarReporte(data.comparacion);
    } catch (err) {
      console.error('❌ Error en la comparación:', err);
    }

    setCargando(false);
  };

  // JSX original sin cambios (se mantiene igual)
  return (
    // ...
    // tu mismo JSX completo como ya lo tienes, no lo cambié
    // ...
  );
}
