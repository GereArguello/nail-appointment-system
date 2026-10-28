
const getWorkingHours = async (fromDate, toDate) => {
    const response = await fetch(
        `http://localhost:8000/working-hours/?from_date=${fromDate}&to_date=${toDate}`
    )

    if (!response.ok) {
        throw new Error("Error al obtener los servicios")
    }

    return response.json();
}

const getCalendarBlocks = async (fromDate, toDate) => {
    const response = await fetch(
        `http://localhost:8000/calendar-blocks/?from_date=${fromDate}&to_date=${toDate}`
    )

    if (!response.ok) {
        throw new Error("Error al obtener los servicios")
    }

    return response.json();
}

const getWorkingCalendar = (fromDate, toDate) => {
    return Promise.all([
        getWorkingHours(fromDate, toDate),
        getCalendarBlocks(fromDate, toDate)
    ]);
}


export { getWorkingCalendar };
