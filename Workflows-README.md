### GitHub Actions Workflows (4 workflows)

1. **backend-ci.yml** - CI para Raspberry Pi backend
2. **integration-tests.yml** - Tests de integración completos
3. **codeql-analysis.yml** - Análisis de seguridad
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

### CodeQL Security (`codeql-analysis.yml`)

**Trigger**:
- Push a main/develop
- Pull Requests
- Lunes 6:00 (automáticamente)

**¿Qué hace?**:
Analiza:
- Python (raspberry-pi)
- Vulnerabilidades de seguridad

### Dependabot (`dependabot.yml`)

**¿Qué hace?** Automáticamente:
- Revisa dependencias cada semana (lunes 9:00)
- Crea PRs para nuevas actualizaciones
- Añade labels apropiadas

**Configurado para**:
- Backend Python (`raspberry-pi/`)
- GitHub Actions (cada mes)
