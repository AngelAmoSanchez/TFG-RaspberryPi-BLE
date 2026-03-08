# Git Hooks

Hook para validar commits y sus mensajes.

## Instalación

```bash
chmod +x setup-hooks.sh
./setup-hooks.sh
```

Esto:
1. Instala pre-commit (si no está)
2. Instala el hook (commit-msg)
3. Prueba la configuración

---

## 🪝 Hook Incluido: conventional-pre-commit
Valida formato de mensajes de commit.

**Formato requerido**:
```
<type>: <description>
```

**Tipos válidos**:
- `feat` - Nueva funcionalidad
- `fix` - Corrección de bug
- `docs` - Documentación
- `style` - Formato (sin cambio de código)
- `refactor` - Refactorización
- `test` - Tests
- `chore` - Mantenimiento
- `perf` - Mejora de performance
- `ci` - CI/CD
- `build` - Build system
- `revert` - Revert commit

> [!NOTE]
> **El hook puede fallar en el primer commit.** Ya que los hooks se validan en su primera ejecución. Si esto ocurre o falla por formato ejecútalo de nuevo.

---

## Comandos Útiles
A continuación se comentan comandos interesantes a tener en cuenta. De igual forma se mostrarán tras la ejecución del `setup-hooks.sh`.

### Ejecutar hooks manualmente

```bash
# Run todos los hooks
pre-commit run --all-files

# Run hook específico
pre-commit run conventional-pre-commit --all-files
```

### Actualizar hooks

```bash
pre-commit autoupdate
```

### Deshabilitar temporalmente

```bash
# Saltar el hook una sola vez
git commit --no-verify

# Desinstalar hooks
pre-commit uninstall
```

### Reinstalar hooks

```bash
pre-commit install
```
