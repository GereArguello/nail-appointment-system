import { useState, useEffect } from "react";
import './WorkingCalendar.css'
import { getWorkingCalendar } from "../../api/workingcalendar";
import { formatDateToISO } from "../../utils/formatDateToISO";
import { groupCalendar } from "../../utils/groupCalendar";
import { formatCalendarDate } from "../../utils/formatCalendarDate";


function WorkingCalendar() {
    const [calendar, setCalendar] = useState([]);
    const [selectedDate, setSelectedDate] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [fromDate, setFromDate] = useState(() => {
        return formatDateToISO(new Date());
    });

    const [toDate, setToDate] = useState(() => {
        const date = new Date();
        date.setDate(date.getDate() + 14);

        return formatDateToISO(date);
    });


    useEffect(() => {
        let active = true;

        setLoading(true);
        setError(null);

        getWorkingCalendar(fromDate, toDate)
            .then(([hours, blocks]) => {
                if (!active) return;

                const grouped = groupCalendar(
                    fromDate,
                    toDate,
                    hours,
                    blocks
                );

                setCalendar(grouped);
                setSelectedDate(grouped[0] ?? null)
            })
            .catch((err) => {
                if (active) setError(err);
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, [fromDate, toDate]);

    if (loading) return <p>Cargando calendario...</p>;
    if (error) return <p>No se pudo cargar el calendario.</p>;


    return (
        <section className="working-calendar">
            <h2>Calendario de atención</h2>

            <div className="calendar-grid">
                {calendar.map((day) => {
                    const formattedDate = formatCalendarDate(day.date);

                    return (
                        <button
                            type="button"
                            key={day.date}
                            className={`calendar-day ${
                                selectedDate?.date === day.date
                                    ? "selected"
                                    : ""
                            }`}
                            onClick={() => setSelectedDate(day)}
                            aria-pressed={selectedDate?.date === day.date}
                        >
                            <span>{formattedDate.weekday}</span>
                            <strong>{formattedDate.day}</strong>
                            <span>{formattedDate.month}</span>
                        </button>
                    );
                })}
            </div>

            {selectedDate && (
                <div className="calendar-details">
                    <h3>{selectedDate.date}</h3>

                    {selectedDate.workingHour
                        ? <p>
                            Horario laboral: {selectedDate.workingHour.start_time}
                            {" - "}
                            {selectedDate.workingHour.end_time}
                        </p>
                        : <p>Sin horario laboral</p>
                    }

                    {selectedDate.blocks.length > 0
                        ? selectedDate.blocks.map((block) => (
                            <p key={block.id}>
                                Bloqueo: {block.starts_at.slice(11, 16)}
                                {" - "}
                                {block.ends_at.slice(11, 16)}
                            </p>
                        ))
                        : <p>No hay bloqueos</p>
                    }
                </div>
            )}
        </section>
    );
}

export { WorkingCalendar };
