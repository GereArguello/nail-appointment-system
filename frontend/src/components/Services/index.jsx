import { useState, useEffect } from "react";
import { getServices } from "../../api/services";
import './Services.css'

function Services() {
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getServices()
      .then(setServices)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [])

  if (loading) return <p>Cargando servicios...</p>
  if (error) return <p>No se pudieron cargar los servicios.</p>

  return (
    <section id="services" className="services">
      <h2>Lista de servicios</h2>

      <div className="services-grid">
        {services.map((service) => (
          <article className="service-card" key={service.id}>
            <div className="service-card-header">
              <h3>{service.name}</h3>
            </div>

            <div className="service-card-body">
              <p>{service.description}</p>
              <p>Duración: {service.duration_minutes} minutos</p>
              <p>Precio: ${service.price}</p>

              {service.deposit_amount > 0 && (
                <p>Seña: ${service.deposit_amount}</p>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export { Services };
