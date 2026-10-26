import "./Gallery.css";

function Gallery({ coverImages }) {
  return (
    <section id="gallery" className="gallery-section">
      <div className="section-heading">
        <span className="section-eyebrow">INSPIRACIÓN</span>
        <h2>Nuestros trabajos</h2>
        <p>Explorá algunos de nuestros diseños.</p>
      </div>

      <div className="gallery-grid">
        {coverImages.map((image) => (
          <button
            className="gallery-item"
            key={image.id}
            type="button"
            onClick={() => console.log(image.serviceId)}
            aria-label={`Ver trabajos del servicio ${image.serviceId}`}
          >
            <img
              src={image.url}
              alt={`Trabajo del servicio ${image.serviceId}`}
            />
          </button>
        ))}
      </div>
    </section>
  );
}

export { Gallery };
