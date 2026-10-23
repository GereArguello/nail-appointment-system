import { useEffect, useState } from 'react'
import './App.css'


function Servicios() {

  const [services, setServices] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/services")
    .then((response => {
      if (!response.ok) {
        throw new Error("Endpoint fallidoo");
      }
      return response.json()
    }))
    .then((data) => setServices(data))
    .catch(console.error)
  }, []);

  return (
    <>
      <p>Acá se verían los servicios</p>

      {services.map((service) => (
        <div key={service.id}>
          <h2>{service.name}</h2>
          <p>{service.description}</p>
          <span>${service.price}</span>
          <p>depósito: {service.deposit_amount}</p>
        </div>
      ))}
    </>
  );
}



function App() {

  return (
    <>
      <h1>HOLA A MI PÁGINA DE MANICURA</h1>
      <Servicios/>
    </>
  )
}

export default App
