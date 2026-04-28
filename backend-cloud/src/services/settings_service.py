import logging
from typing import Dict

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database.models import Detection, SystemSettings, ZoneEnum

logger = logging.getLogger(__name__)


class SettingsService:
    """Servicio para gestionar configuración del sistema"""

    async def get_thresholds(self, db: AsyncSession) -> Dict[str, int]:
        """Obtiene los umbrales actuales (de BD o config)

        Returns:
            dict: near_threshold y medium_threshold
        """
        # Intentar obtener de la BD
        near_query = select(SystemSettings).where(SystemSettings.key == "near_threshold")
        medium_query = select(SystemSettings).where(SystemSettings.key == "medium_threshold")

        near_result = await db.execute(near_query)
        medium_result = await db.execute(medium_query)

        near_setting = near_result.scalar_one_or_none()
        medium_setting = medium_result.scalar_one_or_none()

        # Si no existen en BD, usar valores de config y guardarlos
        if not near_setting:
            near_threshold = settings.near_threshold
            near_setting = SystemSettings(
                key="near_threshold",
                value=str(near_threshold),
                description="Umbral RSSI para zona NEAR (dBm)",
            )
            db.add(near_setting)
            await db.commit()
        else:
            near_threshold = int(near_setting.value)

        if not medium_setting:
            medium_threshold = settings.medium_threshold
            medium_setting = SystemSettings(
                key="medium_threshold",
                value=str(medium_threshold),
                description="Umbral RSSI para zona MEDIUM (dBm)",
            )
            db.add(medium_setting)
            await db.commit()
        else:
            medium_threshold = int(medium_setting.value)

        return {"near_threshold": near_threshold, "medium_threshold": medium_threshold}

    async def update_thresholds(
        self, db: AsyncSession, near_threshold: int, medium_threshold: int
    ) -> Dict:
        """Actualiza umbrales y recalcula todas las zonas

        Args:
            db: Sesión de base de datos
            near_threshold: Nuevo umbral NEAR
            medium_threshold: Nuevo umbral MEDIUM

        Returns:
            dict: Estadísticas de actualización
        """
        logger.info(f"Updating thresholds: NEAR={near_threshold}, MEDIUM={medium_threshold}")

        # Actualiza settings en BD
        await db.execute(
            update(SystemSettings)
            .where(SystemSettings.key == "near_threshold")
            .values(value=str(near_threshold))
        )

        await db.execute(
            update(SystemSettings)
            .where(SystemSettings.key == "medium_threshold")
            .values(value=str(medium_threshold))
        )

        await db.commit()

        # Recalcula zonas de TODAS las detecciones y se obtiene conteo de cada zona
        count_query = select(
            func.count(case((Detection.rssi >= near_threshold, 1))).label("near_count"),
            func.count(
                case(
                    (
                        (Detection.rssi >= medium_threshold) & (Detection.rssi < near_threshold),
                        1,
                    )
                )
            ).label("medium_count"),
            func.count(case((Detection.rssi < medium_threshold, 1))).label("far_count"),
            func.count().label("total"),
        )

        result = await db.execute(count_query)
        counts = result.first()

        # Actualiza zonas
        await db.execute(
            update(Detection).where(Detection.rssi >= near_threshold).values(zone=ZoneEnum.NEAR)
        )

        # MEDIUM
        await db.execute(
            update(Detection)
            .where((Detection.rssi >= medium_threshold) & (Detection.rssi < near_threshold))
            .values(zone=ZoneEnum.MEDIUM)
        )

        # FAR
        await db.execute(
            update(Detection).where(Detection.rssi < medium_threshold).values(zone=ZoneEnum.FAR)
        )

        await db.commit()

        logger.info(
            f"Zonas recalculadas: {counts.near_count} NEAR, "
            f"{counts.medium_count} MEDIUM, {counts.far_count} FAR "
            f"(total: {counts.total})"
        )

        return {
            "recalculated_count": counts.total,
            "updated_to_near": counts.near_count,
            "updated_to_medium": counts.medium_count,
            "updated_to_far": counts.far_count,
        }
