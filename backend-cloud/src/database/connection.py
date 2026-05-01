import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings
from .models import Base

logger = logging.getLogger(__name__)


class Database:
    """Administra la conexión a la base de datos"""

    def __init__(self):
        """Inicializa la base de datos sin conexión"""
        self.engine = None
        self.async_session_maker = None
        self._initialized = False

    async def connect(self):
        """Conecta a la base de datos"""
        if self._initialized:
            return

        try:
            # Configuración del engine
            engine_kwargs = {
                "echo": settings.debug,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }

            # Supabase pgbouncer para evitar problemas con la cache
            if "pooler.supabase.com" in settings.database_url or ":6543" in settings.database_url:
                engine_kwargs["connect_args"] = {
                    "prepared_statement_cache_size": 0,
                    "statement_cache_size": 0,
                    "server_settings": {
                        "jit": "off",
                        "wait_timeout": "30"
                    }
                }

            # Crear motor de base de datos asíncrono
            self.engine = create_async_engine(
                settings.database_url,
                **engine_kwargs
            )

            # Crear generador de sesiones
            self.async_session_maker = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            self._initialized = True
            logger.info("OK - Base de datos conectada")

        except Exception as e:
            logger.error(f"ERROR - Error de conexión a la base de datos: {e}")
            raise

    async def disconnect(self):
        """Desconecta de la base de datos"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("OK - Base de datos desconectada")

    async def create_tables(self):
        """Crea todas las tablas (solo para desarrollo)"""
        if not self._initialized:
            await self.connect()

        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("OK - Tablas de base de datos creadas")
        except Exception as e:
            logger.error(f"ERROR - Error creando tablas: {e}")
            raise

    async def drop_tables(self):
        """Elimina todas las tablas (WARN)"""
        if not self._initialized:
            await self.connect()

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("WARN - Tablas de base de datos eliminadas")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Devuelve una sesión de base de datos asíncrona"""
        if not self._initialized:
            await self.connect()

        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Instancia global de la base de datos
database = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia para obtener una sesión de base de datos"""
    async with database.get_session() as session:
        yield session


async def init_db():
    """Inicializa la base de datos al iniciar la aplicación"""
    await database.connect()

    # Crea tablas en desarrollo
    if settings.environment == "development":
        await database.create_tables()


async def close_db():
    """Cierra la conexión a la base de datos al apagar la aplicación"""
    await database.disconnect()
