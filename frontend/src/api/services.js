const getServices = async () => {
    const response = await fetch("http://localhost:8000/services/");

    if (!response.ok) {
        throw new Error("Error al obtener los servicios")
    }

    return response.json();
}

export {getServices}
