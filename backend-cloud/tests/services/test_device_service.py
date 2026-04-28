from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.models import Device
from src.services.device_service import DeviceService

pytestmark = pytest.mark.unit


class TestDeviceService:
    @pytest.fixture
    def service(self):
        return DeviceService()

    @pytest.mark.asyncio
    async def test_update_last_seen_device_exists(self, service, db_session):
        """Caso IF: El dispositivo existe, solo actualiza timestamp."""
        mock_device = MagicMock(spec=Device)
        with patch.object(service, "get_device", return_value=mock_device):
            await service.update_last_seen(db_session, "iot_01")

            assert mock_device.is_active == 1
            assert db_session.flush.called

    @pytest.mark.asyncio
    async def test_update_last_seen_device_not_exists(self, service, db_session):
        """Caso ELSE: El dispositivo no existe, llama a register_device."""
        with patch.object(service, "get_device", return_value=None):
            with patch.object(service, "register_device", new_callable=AsyncMock) as mock_reg:
                await service.update_last_seen(db_session, "iot_new")
                mock_reg.assert_called_once_with(db_session, "iot_new")

    @pytest.mark.asyncio
    async def test_update_device_info_partial_params(self, service, db_session):
        """Valida los IFs donde name o location pueden ser None."""
        mock_device = MagicMock(name="Original", location="Sede A")
        with patch.object(service, "get_device", return_value=mock_device):
            # Solo actualizamos el nombre, location debería quedarse igual
            await service.update_device_info(db_session, "iot_01", name="Nuevo Nombre")

            assert mock_device.name == "Nuevo Nombre"
            assert mock_device.location == "Sede A"

    @pytest.mark.asyncio
    async def test_get_device_stats_no_detections(self, service, db_session):
        """Caso límite: Dispositivo existe pero tiene 0 detecciones."""
        mock_device = MagicMock(device_id="iot_1", created_at=datetime.now(), last_seen=None)
        with patch.object(service, "get_device", return_value=mock_device):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            db_session.execute = AsyncMock(return_value=mock_result)

            stats = await service.get_device_stats(db_session, "iot_1")

            assert stats["total_detections"] == 0
            assert stats["first_detection"] is None


@pytest.mark.asyncio
class TestDeviceServiceMissingCoverage:
    async def test_get_device_success(self, db_session):
        """Valida que se devuelva el objeto Device si existe."""
        service = DeviceService()
        mock_device = Device(device_id="iot_01")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_device(db_session, "iot_01")
        assert result == mock_device

    async def test_update_last_seen_auto_register(self, db_session):
        """Valida que si el dispositivo no existe, debe llamar a register_device."""
        service = DeviceService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(service, "register_device", new_callable=AsyncMock) as mock_register:
            await service.update_last_seen(db_session, "new_iot_device")
            mock_register.assert_called_once_with(db_session, "new_iot_device")

    async def test_get_active_devices_logic(self, db_session):
        """Valida la construcción de la query de dispositivos activos."""
        service = DeviceService()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)

        await service.get_active_devices(db_session, threshold_minutes=30)

        assert db_session.execute.called

    async def test_deactivate_device_none(self, db_session):
        """Valida el caso donde se intenta desactivar un ID que no existe."""
        service = DeviceService()
        with patch.object(service, "get_device", return_value=None):
            result = await service.deactivate_device(db_session, "non_existent")
            assert result is None

    async def test_activate_device_none(self, db_session):
        """Valida el caso donde se intenta activar un ID que no existe."""
        service = DeviceService()
        with patch.object(service, "get_device", return_value=None):
            result = await service.activate_device(db_session, "non_existent")
            assert result is None

    async def test_update_device_info_none(self, db_session):
        """Valida el caso donde se intenta actualizar info de un ID que no existe."""
        service = DeviceService()
        with patch.object(service, "get_device", return_value=None):
            result = await service.update_device_info(db_session, "non_existent", name="Test")
            assert result is None

    async def test_get_device_stats_none(self, db_session):
        """Valida que devuelve None si el dispositivo no existe para las estadísticas."""
        service = DeviceService()
        with patch.object(service, "get_device", return_value=None):
            result = await service.get_device_stats(db_session, "non_existent")
            assert result is None

    async def test_get_device_stats_last_seen_none(self, db_session):
        """Valida la rama del if ternario cuando last_seen es None."""
        service = DeviceService()

        mock_device = MagicMock(spec=Device)
        mock_device.device_id = "iot_01"
        mock_device.is_active = 1
        mock_device.created_at = datetime.now()
        mock_device.last_seen = None

        mock_val = MagicMock()
        mock_val.scalar.return_value = 0
        db_session.execute = AsyncMock(return_value=mock_val)

        with patch.object(service, "get_device", return_value=mock_device):
            stats = await service.get_device_stats(db_session, "iot_01")
            assert stats["last_seen"] is None

    @pytest.mark.asyncio
    async def test_register_device_new(self, db_session):
        """Valida el registro de un nuevo dispositivo y que se guarde en la BD."""
        service = DeviceService()
        device_id = "new_sensor_01"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.register_device(
            db_session, device_id, name="Test Name", location="Test Loc"
        )

        assert result.device_id == device_id
        assert result.name == "Test Name"
        assert result.location == "Test Loc"
        assert result.is_active == 1
        db_session.add.assert_called_once()
        db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_device_already_exists(self, db_session):
        """Valida que si el dispositivo ya existe, no se intente crear uno nuevo."""
        service = DeviceService()
        device_id = "existing_sensor"
        existing_device = Device(device_id=device_id, name="Original")

        with patch.object(service, "get_device", return_value=existing_device):
            result = await service.register_device(db_session, device_id)
            assert result == existing_device
            db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_device_found(self, db_session):
        """Valida que se devuelva el dispositivo correcto si existe."""
        service = DeviceService()
        device_id = "found_id"
        mock_device = Device(device_id=device_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_device(db_session, device_id)
        assert result == mock_device

    @pytest.mark.asyncio
    async def test_get_active_devices_list(self, db_session):
        """Valida que se devuelva una lista de dispositivos activos."""
        service = DeviceService()
        mock_devices = [Device(device_id="d1"), Device(device_id="d2")]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_devices
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_active_devices(db_session, threshold_minutes=30)

        assert len(result) == 2
        assert result == mock_devices

    @pytest.mark.asyncio
    async def test_activate_device_success(self, db_session):
        """Valida que se active un dispositivo inactivo correctamente."""
        service = DeviceService()
        device_id = "inactive_id"
        mock_device = Device(device_id=device_id, is_active=0)

        with patch.object(service, "get_device", return_value=mock_device):
            result = await service.activate_device(db_session, device_id)
            assert result.is_active == 1
            db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_device_info_with_params(self, db_session):
        """Valida la actualización de nombre y ubicación de un dispositivo."""
        service = DeviceService()
        device_id = "update_id"
        mock_device = Device(device_id=device_id, name="Old", location="Old")

        with patch.object(service, "get_device", return_value=mock_device):
            result = await service.update_device_info(
                db_session, device_id, name="New", location="New"
            )
            assert result.name == "New"
            assert result.location == "New"
            db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_stats_not_found(self, db_session):
        """Valida que se devuelva None si el dispositivo no existe para las estadísticas."""
        service = DeviceService()
        device_id = "missing_stats_id"

        with patch.object(service, "get_device", return_value=None):
            result = await service.get_device_stats(db_session, device_id)
            assert result is None
