CLAUDE.md | CONTRATO ARQUITECTÓNICO DE VIDEOJUEGOS V1.0
1. CONTEXTO TÉCNICO Y VISIÓN
Proyecto:

Entorno:

Arquitectura: Patrón Servicio-Sistema con desacoplamiento total de datos y UI.

Meta de Rendimiento: 60 FPS estables. Presupuesto máximo por frame: 16.67ms.

2. REGLAS DE ORO DE INGENIERÍA (NUNCA VIOLAR)
Gestión de Memoria: PROHIBIDAS las asignaciones en el montón (heap allocations) en Update loops. Usar Object Pooling y pre-asignación de buffers.

Determinismo: Todo cálculo de gameplay debe ser determinista. Usar semillas (seeds) para RNG y Fixed Timestep para físicas.

Arquitectura de Datos: Los datos deben vivir en. Los sistemas no deben guardar estado interno persistente fuera de estos.

Separación de Capas: Los sistemas de gameplay NUNCA deben referenciar directamente a la interfaz de usuario (UI) o componentes visuales. Usar Eventos/Signals.

3. ESTÁNDARES DE CODIFICACIÓN (CONVENCIONES)
Nomenclatura: [Unity: PascalCase para clases/métodos, _camelCase para privados] / [Godot: snake_case para métodos/archivos, PascalCase para clases].

Comentarios: Comentar el "POR QUÉ", nunca el "QUÉ". Documentar decisiones de optimización no obvias.

Módulos: Máximo 500 líneas por archivo. Si crece más, dividir responsabilidades.

4. FLUJO DE TRABAJO AGENTICO (PROCESO OBLIGATORIO)
MODO EXPLORAR: Leer archivos relevantes. No escribir código. Identificar sistemas existentes para REUTILIZAR.

MODO PLAN: Proponer cambios en lenguaje natural. Detallar impacto en rendimiento. ESPERAR APROBACIÓN HUMANA.

MODO IMPLEMENTAR: Seguir enfoque TDD. Escribir la prueba antes que la lógica.

MODO VERIFICAR: Ejecutar comandos de test/lint. Reportar resultados.

5. COMANDOS DE PROYECTO
Build: ``

Test: ``

Lint: ``

Verificación de Performance: /perf-profile (Comando personalizado para medir frame budget).

6. GESTIÓN DE MEMORIA Y ESTADO (PERSISTENCIA)
Mantener SUMMARY.md actualizado con cada cambio arquitectónico.

Si una instrucción es corregida más de dos veces, DEBE ser añadida a esta sección de "Gotchas".

Gotcha 1: [Ejemplo: No usar 'new' en el bucle principal de colisiones].

7. JERARQUÍA DE SUB-AGENTES (DIRECTRICES)
Actuar como Technical Director para decisiones de estructura.

Delegar tareas de UI a sub-agentes especialistas para mantener el contexto del Core limpio.

Respetar las reglas de alcance de ruta (Path-scoped rules) definidas en .claude/rules/.