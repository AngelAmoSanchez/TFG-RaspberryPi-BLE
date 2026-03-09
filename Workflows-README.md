### GitHub Actions Workflows (4 workflows)

1. **backend-ci.yml** - CI para Raspberry Pi backend
2. **integration-tests.yml** - Tests de integración completos
3. **security-analysis.yml** - Análisis de seguridad
- **dependabot.yml** - Auto-updates de dependencias

---

## Workflows

### Backend CI (`backend-ci.yml`)

**Trigger**: Push/PR en `raspberry-pi/**`

**¿Qué hace?**:
1. Valida el formato de:
- Black
- isort
- Flake8 linter
- tipo de MyPy
5. Crea una Base de Datos de prueba
6. Ejecuta pytest con covertura
7. Valida el esquema de la base de datos
8. Valida la seguridad (hardcoded secrets)

### Integration Tests (`integration-tests.yml`)

**Trigger**: Push a `main` o manual

**¿Qué hace?**:
1. Instalar dependencias de backend
2. Inicializa la base de datos SQLite (si es valida)
3. Importa los test backend

### Security Security (`security-analysis.yml`)
### Security Scan (`security-scan.yml`)

**Trigger**:
- Push a main/develop
- Pull Requests a main
- Cada push (automáticamente)

**¿Qué hace?**:
Ejecuta análisis de seguridad en tres niveles:

1. **Bandit (Python Security)**
   - Escanea código Python en `raspberry-pi/src/`
   - Detecta vulnerabilidades comunes (SQL injection, hardcoded secrets, etc.)

2. **Dependency Vulnerabilities**
   - **Python**: `safety check` en `requirements.txt`
   - Identifica dependencias con CVEs conocidos

### Dependabot (`dependabot.yml`)

**¿Qué hace?** Automáticamente:
- Revisa dependencias cada semana (lunes 9:00)
- Crea PRs para nuevas actualizaciones
- Añade labels apropiadas

**Configurado para**:
- Backend Python (`raspberry-pi/`)
- GitHub Actions (cada mes)
