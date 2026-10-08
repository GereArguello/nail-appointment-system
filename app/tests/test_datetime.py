from datetime import timedelta

from sqlmodel import Session

from app.calendar_blocks.models import CalendarBlock
from app.core.datetime import utc_now


def test_datetime_timezone_behavior(session: Session) -> None:
    """Documenta el comportamiento de datetime de SQLite en los tests.

    Aunque los campos usan DateTime(timezone=True), SQLite devuelve los
    datetime persistidos sin tzinfo. Por este motivo se utiliza as_utc()
    al trabajar con valores recuperados de la base de datos.

    Este comportamiento debe volver a comprobarse contra PostgreSQL,
    utilizado en producción, donde TIMESTAMP WITH TIME ZONE tiene soporte
    nativo.
    """
    value = utc_now()

    block = CalendarBlock(
        starts_at=value,
        ends_at=value + timedelta(hours=1),
    )

    session.add(block)
    session.commit()

    block_id = block.id

    session.expire_all()

    loaded = session.get(CalendarBlock, block_id)

    assert loaded is not None

    print()
    print("Original:", value, value.tzinfo)
    print("Loaded:", loaded.starts_at, loaded.starts_at.tzinfo)


# TODO: Ejecutar un test equivalente contra PostgreSQL para verificar
# el comportamiento de DateTime(timezone=True) en producción.
