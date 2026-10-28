import { formatDateToISO } from "./formatDateToISO.js";
import { parseDateToLocal } from "./parseDateToLocal.js";

/**
 * @param {Date} fromDate
 * @param {Date} toDate
 * @returns {string[]}
 */
function rangeGenerator(fromDate, toDate) {
    const calendar = [];
    const currentDate = new Date(fromDate);

    while (currentDate <= toDate) {
        calendar.push(formatDateToISO(currentDate));
        currentDate.setDate(currentDate.getDate() + 1);
    }

    return calendar;
}


/**
 * @param {string} fromDate
 * @param {string} toDate
 * @param {{date: string, start_time: string, end_time: string}[]} workingHours
 * @param {{starts_at: string, ends_at: string}[]} calendarBlocks
 * @returns {{date: string, workingHour: object|null, blocks: object[]}[]}
 */
function groupCalendar(fromDate, toDate, workingHours, calendarBlocks) {
    const localFrom = parseDateToLocal(fromDate);
    const localTo = parseDateToLocal(toDate);

    const calendar = rangeGenerator(localFrom, localTo);

    const groupedCalendar = calendar.map((date) => {
        const workingHour = workingHours.find(
            (wh) => wh.date === date
        );

        const blocks = calendarBlocks.filter(
            (cb) => cb.starts_at.split("T")[0] === date
        );

        return {
            date: date,
            workingHour: workingHour ?? null,
            blocks: blocks
        };
    });
    return groupedCalendar;
};

export { groupCalendar };
