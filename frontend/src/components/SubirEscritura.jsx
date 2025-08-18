import React, { useState } from "react";
import axios from "axios";

const SubirEscritura = () => {
  const [escritura, setEscritura] = useState(null);
  const [plano, setPlano] = useState(null);
  const [datosEscritura, setDatosEscritura] = useState(null);
  const [datosPlano, setDatosPlano] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [mensaje, setMensaje] = useState("");

  const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

  const handleFileChange = (e, tipo) => {
    if (tipo === "escritura") {
      setEscritura(e.target.files[0]);
    } else {
      setPlano(e.target.files[0]);
    }
  };

  const subirEscritura = async () => {
    if (!escritura) return setMensaje("⚠️ Selecciona un archivo de escritura");
    setMensaje("⏳ Subiendo escritura...");

    const formData = new FormData();
    formData.append("file", escritura);

    try {
      const res = await axios.post(`${backendUrl}/extraer-escritura`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDatosEscritura(res.data);
      setMensaje("✅ Escritura procesada con éxito");
    } catch (err) {
      console.error(err);
      setMensaje("❌ Error al procesar escritura");
    }
  };

  const subirPlano = async () => {
    if (!plano) return setMensaje("⚠️ Selecciona un archivo de plano");
    setMensaje("⏳ Subiendo plano...");

    const formData = new FormData();
    formData.append("file", plano);

    try {
      const res = await axios.post(`${backendUrl}/extraer-plano`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDatosPlano(res.data);
      setMensaje("✅ Plano procesado con éxito");
    } catch (err) {
      console.error(err);
      setMensaje("❌ Error al procesar plano");
    }
  };

  const comparar = async () => {
    if (!datosEscritura || !datosPlano) {
      return setMensaje("⚠️ Debes subir primero escritura y plano");
    }
    setMensaje("⏳ Comparando escritura con plano...");

    try {
      const res = await axios.post(`${backendUrl}/comparar-escritura-plano`, {
        escritura: datosEscritura.datos_tecnicos || [],
        plano: datosPlano.segmentos_detectados || [],
      });
      setResultado(res.data);
      setMensaje("✅ Comparación realizada");
    } catch (err) {
      console.error(err);
      setMensaje("❌ Error al comparar escritura y plano");
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <h1 className="text-xl font-bold">📄 Subir Escritura y Plano</h1>

      {/* Subida escritura */}
      <div className="space-y-2">
        <input type="file" onChange={(e) => handleFileChange(e, "escritura")} />
        <button
          onClick={subirEscritura}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg shadow"
        >
          Subir Escritura
        </button>
      </div>

      {/* Subida plano */}
      <div className="space-y-2">
        <input type="file" onChange={(e) => handleFileChange(e, "plano")} />
        <button
          onClick={subirPlano}
          className="px-4 py-2 bg-green-500 text-white rounded-lg shadow"
        >
          Subir Plano
        </button>
      </div>

      {/* Comparar */}
      <div>
        <button
          onClick={comparar}
          className="px-4 py-2 bg-purple-500 text-white rounded-lg shadow"
        >
          Comparar
        </button>
      </div>

      {/* Mensaje de estado */}
      {mensaje && <p className="text-gray-700">{mensaje}</p>}

      {/* Resultados */}
      {resultado && (
        <div className="mt-6 p-4 border rounded-lg bg-gray-50">
          <h2 className="font-semibold">🔎 Resultado de comparación:</h2>
          {resultado.comparacion && resultado.comparacion.length > 0 ? (
            <ul className="list-disc ml-6">
              {resultado.comparacion.map((c, i) => (
                <li key={i}>
                  Escritura: {c.escritura?.rumbo || "—"} -{" "}
                  {c.escritura?.distancia || "?"} m |
                  Plano: {c.plano?.longitud_px || "?"} px →{" "}
                  {c.coincide ? "✅ Coincide" : "❌ No coincide"}
                </li>
              ))}
            </ul>
          ) : (
            <p>No hubo coincidencias</p>
          )}
        </div>
      )}
    </div>
  );
};

export default SubirEscritura;
