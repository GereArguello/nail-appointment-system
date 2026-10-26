import "./Header.css";

function Header({ businessName }) {
  return (
    <header className="site-header">
      <div className="header-container">
        <a className="brand-name" href="#">
          {businessName}
        </a>

        <nav className="header-nav" aria-label="Navegación principal">
          <ul>
            <li>
              <a href="#gallery">Galería</a>
            </li>
            <li>
              <a href="#services">Servicios</a>
            </li>
            <li>
              <a href="#working-calendar">Horarios</a>
            </li>
          </ul>
        </nav>

        <div className="header-auth">
          <button className="login-button" type="button">
            Iniciar sesión
          </button>
          <button className="register-button" type="button">
            Registrarse
          </button>
        </div>
      </div>
    </header>
  );
}

export { Header };
