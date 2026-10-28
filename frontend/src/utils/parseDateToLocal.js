function parseDateToLocal(fecha) {
    const partes = fecha.split("-");
    const año = parseInt(partes[0]);
    const mes = parseInt(partes[1], 10) - 1;
    const dia = parseInt(partes[2]);

    return new Date(año, mes, dia, 0, 0, 0);
}

export { parseDateToLocal };
