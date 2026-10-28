import { parseDateToLocal } from "./parseDateToLocal";

function formatCalendarDate(dateString) {
    const date = parseDateToLocal(dateString);

    const weekday = new Intl.DateTimeFormat("es-AR", {
        weekday: "short"
    }).format(date);

    const month = new Intl.DateTimeFormat("es-AR", {
        month: "short"
    }).format(date);

    const day = date.getDate();

    return {
        weekday,
        day,
        month
    };
}

export { formatCalendarDate };
