import "./Hero.css";

function Hero({ businessName, description }) {
  return (
    <section className="hero">
      <div className="hero-content">
        <span className="hero-eyebrow">
          TU ESPACIO DE BELLEZA
        </span>

        <h1>Bienvenida a {businessName}</h1>

        <p>{description}</p>

        <button className="booking-button" type="button">
          Agendar cita
        </button>
      </div>
    </section>
  );
}

export { Hero };
