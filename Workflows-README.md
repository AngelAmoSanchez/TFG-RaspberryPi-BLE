### GitHub Actions Workflows (4 workflows)

1. **backend-ci.yml** - CI para Raspberry Pi backend
2. **frontend-ci.yml** - CI para web interface
3. **integration-tests.yml** - Tests de integración completos
4. **security-analysis.yml** - Análisis de seguridad
- **dependabot.yml** - Auto-updates de dependencias

---

## Workflows

### Backend CI (`backend-ci.yml`)

**Trigger**: Push en `raspberry-pi/**`

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

### Frontend CI (`frontend-ci.yml`)

**Trigger**: Push en `web-interface/**`

**¿Qué hace?**:
1. Valida el ESLint
2. Revisa si hay console.logs
3. Build con Vite
4. Verifica si build artifacts
5. Formatea el código
7. Auditorea dependencias

### Integration Tests (`integration-tests.yml`)

**Trigger**: Push a `main` o manual

**¿Qué hace?**:
1. Instalar dependencias de backend y frontend
2. Inicializa la base de datos SQLite (si es valida)
3. Importa los test backend
4. Build frontend

### Security Security (`security-analysis.yml`)

**Trigger**:
- Push a main/develop
- Pull Requests a main
- Cada push (automáticamente)

**¿Qué hace?**:
Ejecuta análisis de seguridad en tres niveles:

1. **Bandit (Python Security)**
   - Escanea código Python en `raspberry-pi/src/`
   - Detecta vulnerabilidades comunes (SQL injection, hardcoded secrets, etc.)

2. **ESLint Security (JavaScript)**
   - Analiza código React en `web-interface/src/`
   - Plugin `eslint-plugin-security` para detección de vulnerabilidades
   - Detecta XSS, eval() inseguro, RegEx DoS, etc.

3. **Dependency Vulnerabilities**
   - **Python**: `safety check` en `requirements.txt`
   - **JavaScript**: `npm audit` en `package.json`
   - Identifica dependencias con CVEs conocidos

### Dependabot (`dependabot.yml`)

**¿Qué hace?** Automáticamente:
- Revisa dependencias cada semana (lunes 9:00)
- Crea PRs para nuevas actualizaciones
- Añade labels apropiadas

**Configurado para**:
- Backend Python (`raspberry-pi/`)
- Frontend npm (`web-interface/`)
- GitHub Actions (cada mes)
