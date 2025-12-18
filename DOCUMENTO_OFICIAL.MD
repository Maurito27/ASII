📘 DOCUMENTACIÓN TÉCNICA: PROYECTO ASII
Versión del Sistema: V24 (Stable - Indagación Progresiva) Fecha de Documentación: 12 de Diciembre, 2025 Desarrollado para: Industrias De Pascale - Depto. de Sistemas
====================================================================================================================================================================================
1. RESUMEN EJECUTIVO DEL PROYECTO
1.1. Definición
ASII (Asistente de Soporte IT Inteligente) es un sistema de inteligencia artificial generativa diseñado para actuar como un Consultor Técnico Senior automatizado. Su función principal es asistir al equipo de soporte y operativos en la resolución de problemas técnicos, configuración de software (Softland, SQL, etc.) y procedimientos internos, utilizando la base de conocimiento de la empresa (Manuales PDF, Docs, TXT).

A diferencia de los sistemas RAG (Retrieval-Augmented Generation) tradicionales que simplemente buscan palabras clave, ASII V24 implementa una Arquitectura Cognitiva de 4 Fases: Detección, Indagación, Lectura Selectiva e Instrucción.

1.2. Capacidades Diferenciales (Core Features)
El sistema ha evolucionado para resolver problemas específicos de la operación diaria:

Indagación Progresiva: El bot no lee documentos enteros ciegamente. Primero extrae el índice (TOC), lo presenta al usuario y pregunta: "¿Qué necesitas específicamente?". Esto reduce alucinaciones y mejora la precisión.

Memoria Visual (Visión): El sistema es capaz de "ver" los manuales. Extrae imágenes, diagramas y capturas de pantalla de los PDFs, crea un catálogo inteligente y las envía al chat cuando la explicación lo requiere.

Modo Instructor (Sherpa): Detecta si el usuario es novato (ej: dice "no sé", "guíame"). En ese caso, abandona el tecnicismo y asume un rol pedagógico, guiando paso a paso desde la introducción.

Auditoría Financiera en Tiempo Real: Cuenta con un monitor de costos que calcula cada token consumido (Entrada/Salida) basado en tarifas de Gemini 2.0 Flash, con un Kill Switch automático si se supera el presupuesto.

Eficiencia de Caché Híbrido: Utiliza un sistema de doble caché (Embeddings vectoriales para búsqueda + JSON estructurado para lectura profunda) que reduce los tiempos de respuesta y costos operativos a casi cero en consultas recurrentes.

1.3. Tecnologías Base

Motor Cognitivo: Google Gemini 2.0 Flash (vía API).

Procesamiento Documental: PyMuPDF4LLM (Extracción de Markdown + Imágenes).

Base de Datos Vectorial: ChromaDB (Búsqueda semántica local).

Interfaz: Telegram Bot API (Async).

Lenguaje: Python 3.10+.



=============================================================================================================================================================================================

2. ÍNDICE GENERAL DE LA DOCUMENTACIÓN

CAPÍTULO 1: Visión General (Actual)
1.1. Resumen del Proyecto.

1.2. Capacidades Diferenciales.

1.3. Tecnologías Base.

CAPÍTULO 2: Arquitectura Lógica
2.1. El Flujo de los 4 Estados (Explorando -> Indagando -> Leyendo -> Instructor).

2.2. Diagrama de Flujo de Datos (Input -> Procesador -> Cerebro -> Output).

2.3. Sistema de Caché Híbrido (Vectores vs. JSON).

CAPÍTULO 3: Análisis Detallado de Código (Core)
Análisis línea a línea de los componentes vitales:

3.1. brain.py: El orquestador de inteligencia y prompts dinámicos.

3.2. session_manager.py: La gestión de la memoria de corto plazo y estados.

3.3. document_processor.py: El motor de extracción de texto, índices e imágenes.

CAPÍTULO 4: Subsistema de Visión y Recursos
4.1. Estrategia de Catálogo de Imágenes (Cómo el bot "sabe" qué fotos tiene).

4.2. Detección de Referencias (Algoritmo de coincidencia difusa/fuzzy).

4.3. cache_manager.py: Estructura de guardado en disco.

CAPÍTULO 5: Motor de Búsqueda y RAG
5.1. rag_engine.py: Lógica de "Francotirador" (Búsqueda exacta) vs. "Explorador" (Semántica).

5.2. Ingesta de datos (ingest_script.py).

CAPÍTULO 6: Interfaz y Control
6.1. telegram_bot.py: Manejo de mensajes largos (paginación anti-crash) y UX.

6.2. Comandos Tácticos (/manual, /limpiar, /costos).

CAPÍTULO 7: Finanzas y Operaciones
7.1. monitor_dashboard.py: El panel de control de costos.

7.2. Sistema de Logs y Kill Switch (API_LOCKED).

7.3. Despliegue y Mantenimiento (run_bot.bat).








📘 CAPÍTULO 2: ARQUITECTURA LÓGICA
El núcleo de ASII V24 no es un simple modelo de "Pregunta-Respuesta", sino un Sistema de Estados Cognitivos. El bot cambia su comportamiento y sus herramientas según la etapa de la conversación en la que se encuentre con el usuario.

2.1. EL FLUJO DE LOS 4 ESTADOS
El archivo session_manager.py gobierna la "memoria de corto plazo" del bot, definiendo en qué estado mental se encuentra para cada usuario (identificado por chat_id).

1️⃣ Estado: EXPLORANDO (Default)
Es el estado inicial y de "reposo". El bot actúa como un bibliotecario generalista.

Objetivo: Encontrar dónde está la información.

Herramientas Activas:

Motor RAG (Vectorial): Busca fragmentos sueltos en toda la base de conocimientos.

Francotirador (Regex): Busca coincidencias exactas en nombres de archivos (ej: "manual sql").

Búsqueda Web: Si no hay data interna, consulta DuckDuckGo.

Transición: Si detecta un archivo específico con alta probabilidad, pasa a INDAGANDO.

2️⃣ Estado: INDAGANDO (Diagnóstico)
Es el estado de "Triaje". El bot ha encontrado un manual candidato pero NO lo lee completo todavía para ahorrar recursos y evitar alucinaciones.

Acción Técnica: Llama a procesador.extraer_indice_ligero(ruta_pdf).

Interacción:

Presenta el Índice (Tabla de Contenidos) al usuario.

Pregunta: "¿Qué tema específico necesitas de este manual?".

Por qué existe: Evita que el bot responda con información de la página 50 cuando el usuario necesitaba la página 2.

Transición: Cuando el usuario responde (con un tema o pidiendo guía), pasa a LEYENDO.

3️⃣ Estado: LEYENDO (Lectura Profunda)
El bot "abre el libro". Carga el contenido completo en su memoria de contexto.

Acción Técnica: Llama a procesador.procesar_pdf(ruta_pdf) (o recupera del Caché JSON).

Capacidades Activas:

Visión: Accede al Catálogo de Imágenes.

Citas: Puede referenciar páginas exactas.

Comportamiento: Responde preguntas específicas sobre el documento activo.

Transición: Se mantiene aquí hasta que el usuario diga "salir", "cancelar" o "basta".

4️⃣ Modo: INSTRUCTOR (Comportamiento Lógico)
Nota: No es un estado duro en el código, sino una adaptación del Prompt en el estado LEYENDO.

Trigger: Detectado por el LLM cuando el usuario dice "no sé", "guíame", "soy nuevo".

Cambio de Estrategia:

Ignora la búsqueda de soluciones rápidas.

Adopta una estructura pedagógica: Concepto -> Prerrequisito -> Paso 1.

Sugiere el orden de lectura (ej: "Empecemos por la Introducción").

2.2. DIAGRAMA DE FLUJO DE DATOS (Pipeline)
El dato viaja a través de una tubería de procesamiento diseñada para maximizar la velocidad y minimizar el costo.

Fragmento de código

graph TD
    A[Usuario (Telegram)] -->|Mensaje/Foto| B(telegram_bot.py)
    B -->|Consulta + SessionID| C{session_manager.py}
    
    C -- Estado: EXPLORANDO --> D[brain.py (RAG Engine)]
    D -->|Búsqueda Vectorial| E[(ChromaDB)]
    D -->|Búsqueda Web| F[DuckDuckGo]
    
    C -- Estado: INDAGANDO --> G[document_processor.py]
    G -->|Extraer Solo Índice| H(Lectura Ligera PyMuPDF)
    
    C -- Estado: LEYENDO --> I[brain.py (Modo Experto)]
    I -->|Verificar Caché| J{cache_manager.py}
    
    J -- No Existe --> K[Procesador Full]
    K -->|OCR + Extracción| L[Markdown + Imágenes .jpg]
    K -->|Guardar| M[(Disco JSON + Images)]
    
    J -- Sí Existe --> M
    
    M -->|Contexto + Catálogo Visual| N[Gemini 2.0 Flash API]
    N -->|Respuesta + Referencias IMG| O[Generador de Respuesta]
    
    O -->|Texto Paginado + Fotos| A
Puntos Críticos del Flujo:

Filtro de Seguridad (API_LOCKED): Antes de llamar a Gemini (N), brain.py verifica si existe el archivo de bloqueo por presupuesto.

Inyección Visual: En el paso (N), el catálogo de imágenes se inyecta como texto en el prompt del sistema para que Gemini "sepa" qué fotos existen.

2.3. SISTEMA DE CACHÉ HÍBRIDO
ASII V24 utiliza dos tipos de memoria para equilibrar precisión y profundidad. Este es uno de los diferenciadores técnicos más fuertes del proyecto.

A. Caché Vectorial (Búsqueda Rápida)
Tecnología: ChromaDB.

Ubicación: data/chroma_db.

Contenido: El PDF se rompe en "chunks" (fragmentos) de 1000 caracteres. Se convierten a vectores matemáticos (embeddings).

Uso: Se usa SOLO en el estado EXPLORANDO para encontrar dónde está la información.

Ventaja: Extremadamente rápido para búsquedas semánticas ("cómo facturar" encuentra "emisión de facturas").

Desventaja: Pierde el contexto global del documento (no sabe qué capítulo va antes de cuál).

B. Caché Estructurado (Lectura Profunda)
Tecnología: Archivos JSON + Carpetas de Imágenes.

Ubicación: data/cache_docs y data/images_cache.

Contenido:

Texto completo del PDF convertido a Markdown limpio.

Mapa de navegación (jerarquía de títulos #, ##, ###).

Catálogo Inteligente de Imágenes: Lista de fotos con su descripción contextual y número de página.

Uso: Se usa en los estados INDAGANDO y LEYENDO.

Ventaja: Mantiene la integridad total del manual. Permite al LLM entender "el todo" y ver imágenes.

Costo: $0.00 leerlo del disco (evita re-procesar el PDF con CPU cada vez).






📘 CAPÍTULO 3: ANÁLISIS DETALLADO DE CÓDIGO (CORE)
Este capítulo documenta la lógica interna de los tres archivos Python que constituyen el "Sistema Nervioso Central" de ASII V24.

3.1. app/logic/brain.py (El Orquestador)
Es el archivo principal donde reside la toma de decisiones. Coordina la memoria, la visión, el control de costos y la generación de respuestas.

A. Control Financiero y Seguridad
Antes de procesar cualquier pensamiento, el cerebro verifica si tiene permiso para gastar dinero.

verificar_kill_switch(): Revisa si existe el archivo data/API_LOCKED. Si existe, aborta inmediatamente devolviendo "SISTEMA PAUSADO". Esto actúa como un fusible físico de seguridad.

auditar_costos(respuesta_llm):

Input: Recibe el objeto usage_metadata de la respuesta de Gemini.

Proceso: Multiplica los tokens de entrada por $0.10/1M y salida por $0.40/1M.

Output: Escribe una línea en el CSV usage_log.csv y muestra el costo en consola. Es vital para la auditoría.

B. Sistema de Visión (Lógica Difusa)
detectar_imagenes_mencionadas(texto, catalogo):

Esta función resuelve el problema de "hallar la foto correcta".

No busca solo coincidencias exactas. Utiliza 3 estrategias:

Exacta: Si el LLM dice img-01.jpg.

Parcial: Si el LLM dice img-01 (sin extensión).

Contextual: Si el LLM dice "la imagen de la página 5" (busca en el catálogo qué foto está en esa página).

Retorno: Una lista de rutas de archivos .jpg lista para enviar a Telegram.

C. El Bucle Principal: generar_respuesta_inteligente
Esta función asíncrona es el corazón del sistema. Implementa la máquina de estados:

Bloque de Transición (Fase Indagación -> Lectura):

Si el estado anterior era INDAGANDO, asume que el texto que acaba de entrar es la selección del usuario (ej: "Quiero ver Prerrequisitos").

Fuerza el cambio de estado a LEYENDO inmediatamente para procesar esa solicitud.

Bloque de Lectura Profunda (Fase 4):

Validación: Verifica si el archivo físico aún existe.

Procesamiento: Llama al caché. Si no existe, invoca al procesador pesado.

Inyección de Prompt (V24 - "Sherpa"): Aquí se carga el prompt dinámico que instruye a Gemini a actuar como "Instructor" si el usuario parece perdido ("guíame") o como "Técnico" si es específico.

Inyección Visual: Inserta la lista de imágenes disponibles (catalogo) en el prompt del sistema.

Bloque de Detección (Fase 1):

Usa detectar_archivo_francotirador (Regex).

Diferencial V24: Si encuentra un archivo, NO LO CARGA. Llama a procesador.extraer_indice_ligero para obtener solo el texto del índice y cambia el estado a INDAGANDO.

3.2. app/logic/session_manager.py (Gestor de Estados)
Este módulo maneja la memoria RAM de "quién es quién" y "en qué está" cada usuario.

Estructura de Datos
Utiliza un diccionario en memoria _sesiones:

Python

{
    "chat_id_123": {
        "estado": "INDAGANDO",       # El estado mental actual
        "doc_activo": "Manual.pdf",  # El archivo que está mirando
        "metadata": {...},           # Datos técnicos del archivo
        "consulta_inicial": "error"  # Qué preguntó el usuario al principio
    }
}
Estados Definidos
EXPLORANDO: Estado por defecto. El bot busca en toda la base de datos.

INDAGANDO: Estado de espera. El bot mostró un índice y espera que el usuario elija. (Introducido en V23).

LEYENDO: Estado de foco. El bot tiene cargado el contexto completo de un documento y responde sobre él.

Funciones Clave
cambiar_estado(...): La única forma segura de transicionar. Se encarga de limpiar o persistir datos según la transición.

limpiar_sesion(...): El botón de pánico. Borra todo y devuelve al usuario al estado EXPLORANDO.

3.3. app/logic/document_processor.py (El Ojo del Sistema)
Es el encargado de transformar PDFs binarios en datos que la IA pueda entender.

A. extraer_indice_ligero(ruta_pdf) (La Vía Rápida)
Tecnología: Usa fitz (PyMuPDF) en modo bajo nivel.

Lógica: Solo lee la tabla de metadatos (TOC) del PDF.

Velocidad: < 0.5 segundos.

Uso: Se ejecuta en la Fase 1 para mostrar el menú al usuario sin gastar CPU en procesar todo el texto.

B. procesar_pdf(ruta_pdf) (La Vía Lenta/Completa)
Tecnología: Usa pymupdf4llm.

Lógica:

Convierte cada página a Markdown.

Extracción de Imágenes: Recorta cada gráfico y lo guarda en data/images_cache/Nombre_Manual/.

Inserta referencias ![](...) en el texto Markdown.

Salida: Un diccionario complejo con el texto completo, el mapa de navegación y el catálogo de imágenes.

C. _crear_catalogo_imagenes(...)
Esta función crea la "Inteligencia Visual".

Recorre el Markdown generado.

Cada vez que encuentra una etiqueta de imagen, mira qué texto hay 150 caracteres antes.

Guarda ese texto como "Contexto" en el catálogo.

Resultado: El bot sabe que img-5.jpg aparece justo después del texto "Configuración de Puertos", permitiéndole asociar la imagen al tema.



📘 CAPÍTULO 4: SUBSISTEMA DE VISIÓN Y RECURSOS
ASII V24 no utiliza modelos de visión costosos (como GPT-4 Vision) para analizar imágenes en tiempo real. En su lugar, utiliza una Estrategia de Asociación Contextual que permite al bot "saber" qué contiene una imagen basándose en el texto que la rodea en el manual original.

4.1. ESTRATEGIA DE CATÁLOGO DE IMÁGENES (Visual Indexing)
El problema fundamental de los PDFs técnicos es que las imágenes están incrustadas como objetos binarios sin significado semántico.

El Proceso de Catalogación
Cuando document_processor.py analiza un PDF en la Fase de Lectura Profunda (LEYENDO), realiza los siguientes pasos para construir la "Visión" del bot:

Extracción Física: Usa PyMuPDF para recortar cada objeto de imagen y guardarlo como .jpg en data/images_cache/{Nombre_Manual}/.

Mapeo de Posición: Identifica en qué byte del texto original aparecía la imagen.

Captura de Contexto (La Clave):

El sistema retrocede 150 caracteres desde la posición de la imagen.

Captura ese texto (ej: "Para configurar el puerto, ver la siguiente pantalla:").

Asocia ese texto a la imagen img-3.jpg.

Estructura del Catálogo (JSON)
Esta información se guarda en el archivo de caché del documento:

JSON

"catalogo_imagenes": [
    {
        "archivo": "img-0.jpg",
        "ruta_completa": "data/images_cache/Manual_SQL/img-0.jpg",
        "pagina": 3,
        "contexto": "Figura 1: Pantalla de inicio de sesión del servidor SQL."
    },
    {
        "archivo": "img-1.jpg",
        "ruta_completa": "data/images_cache/Manual_SQL/img-1.jpg",
        "pagina": 5,
        "contexto": "Seleccione la opción 'Mixed Mode' como se muestra abajo:"
    }
]
4.2. DETECCIÓN DE REFERENCIAS (Algoritmo de Coincidencia)
Una vez que el LLM (Gemini) tiene el catálogo inyectado en su prompt, puede mencionar imágenes. Sin embargo, los LLMs son imprecisos (pueden decir "ver imagen 1", "ver img-1.jpg" o "la foto de la página 3").

Para resolver esto, brain.py utiliza la función detectar_imagenes_mencionadas, que aplica una Lógica de Triple Criterio:

Coincidencia Exacta (High Confidence):

Busca si el string img-0.jpg aparece tal cual en la respuesta.

Uso: Cuando el LLM sigue la instrucción al pie de la letra.

Coincidencia Parcial (Medium Confidence):

Busca si el nombre base img-0 aparece, ignorando la extensión.

Uso: Cuando el LLM olvida poner ".jpg".

Coincidencia Contextual (Fuzzy Logic):

Si el texto menciona "página X" y la palabra "imagen/figura/foto".

El algoritmo busca en el catálogo qué imagen corresponde a esa página X.

Uso: Cuando el LLM dice "Como se ve en la imagen de la página 5...".

4.3. app/logic/cache_manager.py (Gestor de Persistencia)
Este componente es el responsable de que el sistema sea económicamente viable. Evita que tengamos que pagar tokens o gastar CPU procesando el mismo manual dos veces.

Funciones Críticas
Python

"""
Gestor de Caché (cache_manager.py)
----------------------------------
Responsabilidad: Guardar y recuperar el análisis procesado (JSON) de los documentos.
"""
import os
import json
from app.core.config import Configuracion

class CacheManager:
    def __init__(self):
        self.cache_dir = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "cache_docs")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _obtener_ruta_hash(self, ruta_fisica_pdf):
        """Genera un ID único basado en el nombre del archivo para el JSON de caché."""
        nombre_base = os.path.basename(ruta_fisica_pdf)
        return os.path.join(self.cache_dir, f"{nombre_base}.json")

    def guardar_en_cache(self, ruta_fisica_pdf, datos_analisis):
        """
        Guarda el diccionario complejo (Texto + Catálogo + Mapa) en disco.
        """
        ruta_json = self._obtener_ruta_hash(ruta_fisica_pdf)
        try:
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos_analisis, f, ensure_ascii=False, indent=2)
            print(f">> [Caché] SAVE: Análisis guardado en {ruta_json}")
        except Exception as e:
            print(f">> [Caché] ERROR guardando: {e}")

    def obtener_analisis_cacheado(self, ruta_fisica_pdf):
        """
        Intenta recuperar el análisis previo. Retorna None si no existe o es viejo.
        """
        ruta_json = self._obtener_ruta_hash(ruta_fisica_pdf)
        
        if not os.path.exists(ruta_json):
            print(f">> [Caché] MISS: El documento no está procesado ({os.path.basename(ruta_fisica_pdf)})")
            return None
            
        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            print(f">> [Caché] HIT: Documento recuperado de disco.")
            return datos
        except Exception:
            return None

gestor_cache = CacheManager()
Flujo de Vida del Dato
Día 1: Usuario pide "Manual SQL". cache_manager retorna None. document_processor trabaja (tarda 5s). cache_manager guarda el JSON.

Día 2: Usuario pide "Manual SQL". cache_manager encuentra el JSON. Carga inmediata (0.1s). Costo de procesamiento CPU = 0.




📘 CAPÍTULO 5: MOTOR DE BÚSQUEDA Y RAGEl subsistema de búsqueda es la puerta de entrada al flujo de trabajo de ASII. Antes de poder leer o indagar, el bot debe localizar el archivo correcto entre cientos de manuales. Para ello, implementa una Estrategia Dual que prioriza la velocidad sobre la complejidad.5.1. app/logic/rag_engine.py (El Localizador)Este archivo contiene la lógica para recuperar información. No "piensa" (eso lo hace el cerebro), solo "busca".A. Estrategia 1: "El Francotirador" (Búsqueda Heurística)Es la primera línea de defensa. Si el usuario sabe lo que quiere, no perdemos tiempo con vectores matemáticos.Función: detectar_archivo_francotirador(mensaje)Lógica:Escanea la carpeta data/raw_docs en busca de nombres de archivos reales.Normaliza el mensaje del usuario (minúsculas, sin tildes).Busca coincidencias directas de palabras clave fuertes.Ejemplo:Usuario: "Necesito el manual de Validaciones".Archivo: SAR_PROD_MAN_Administrador_de_Validaciones.pdf.Resultado: Match positivo.Ventaja: Precisión del 100% y latencia casi nula.Impacto en V24: Si esta función tiene éxito, dispara inmediatamente el estado INDAGANDO (mostrando el índice), saltándose la búsqueda semántica.B. Estrategia 2: "El Explorador" (Búsqueda Semántica/RAG)Si el francotirador falla (ej: el usuario pregunta "cómo arreglo el error 504" sin mencionar ningún manual), se activa el motor RAG (Retrieval-Augmented Generation).Función: buscar_contexto_relevante(query)Tecnología: ChromaDB + HuggingFace Embeddings.Proceso:Convierte la pregunta del usuario en un vector numérico (lista de 384 números flotantes).Compara ese vector con los millones de vectores almacenados en la base de datos chroma_db.Recupera los 4 fragmentos ("chunks") de texto que están más "cerca" matemáticamente.Salida: Retorna párrafos sueltos de texto que contienen la posible respuesta.C. Gestión de MetadatosFunción: obtener_metadata_archivo(nombre_parcial)Responsabilidad: Dado un nombre de archivo (o parte de él), devuelve su "DNI":Ruta física completa (C:\...\data\raw_docs\Sistemas\Manual.pdf).Categoría (carpeta donde está).Tamaño en KB.Cantidad aproximada de páginas.5.2. data/ingest_script.py (La Digestión de Datos)Este script no se ejecuta con el bot. Es un proceso offline (mantenimiento) que el administrador corre cuando agrega nuevos manuales (/recargar o manualmente).Su trabajo es transformar documentos legibles por humanos en una base de datos vectorial legible por máquinas.Flujo de Ingesta (Paso a Paso):Carga (Loaders):Usa PyPDFLoader para leer PDFs página por página.Usa TextLoader para archivos .txt.Fragmentación (Splitting):Los manuales son muy largos para entrar en un solo vector.Herramienta: RecursiveCharacterTextSplitter.Configuración:chunk_size=1000: Corta el texto cada 1000 caracteres.chunk_overlap=200: Deja un solapamiento de 200 caracteres entre cortes para no romper frases a la mitad.Vectorización (Embedding):Convierte cada fragmento de texto en números.Modelo: sentence-transformers/all-MiniLM-L6-v2 (Local y rápido).Nota: Este modelo "entiende" el significado. Sabe que "coche" y "automóvil" son cercanos, aunque se escriban distinto.Almacenamiento (Persistencia):Guarda los vectores en data/chroma_db.Esta carpeta es la "Memoria de Largo Plazo" del bot.Código Crítico de Ingesta:Python# Fragmento de data/ingest_script.py

def ingest_docs():
    # 1. Definir el modelo de Embeddings (Cerebro semántico)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # 2. Cargar documentos
    loader = DirectoryLoader(ruta_docs, glob="**/*.pdf", loader_cls=PyPDFLoader)
    raw_docs = loader.load()
    
    # 3. Cortar en pedacitos (Chunks)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(raw_docs)
    
    # 4. Guardar en ChromaDB
    Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory="./data/chroma_db"
    )
    print("✅ Ingesta completada. Cerebro actualizado.")
5.3. Diferencia entre Ingesta y ProcesamientoEs vital distinguir estos dos conceptos en ASII V24:CaracterísticaIngesta (ingest_script.py)Procesamiento (document_processor.py)Cuándo ocurreAntes de encender el bot (Mantenimiento).En tiempo real (cuando el usuario pide un doc).ObjetivoBúsqueda y descubrimiento.Lectura profunda y comprensión.TécnicaVectores (Embeddings).Texto Plano (Markdown) + Imágenes.OutputBase de datos chroma_db.Archivos JSON en cache_docs.Uso en BotEstado EXPLORANDO.Estados INDAGANDO y LEYENDO.




📘 CAPÍTULO 6: INTERFAZ Y CONTROLEl archivo app/interfaces/telegram_bot.py es la única capa del sistema que tiene contacto con el mundo exterior. Su responsabilidad es traducir las intenciones del usuario en órdenes para el cerebro (brain.py) y renderizar las respuestas complejas (texto, botones, imágenes, archivos) de una manera limpia y estable.6.1. telegram_bot.py (El Front-End)A diferencia de un script de bot básico, la interfaz de ASII V24 implementa lógica defensiva avanzada para evitar bloqueos y mejorar la experiencia de usuario (UX).A. Sistema Anti-Crash (Paginación Automática)Telegram impone un límite estricto de 4096 caracteres por mensaje. En el "Modo Experto" o "Instructor", las respuestas de Gemini suelen superar este límite (ej: un procedimiento de 50 pasos). Si intentamos enviar el texto de una sola vez, la API devuelve un error Bad Request: message is too long y el bot muere.Para solucionar esto, implementamos la función enviar_mensaje_seguro(...):Lógica de Fragmentación:Verifica la longitud del texto.Si len(texto) > 4000:Busca el último salto de línea (\n) antes del carácter 4000 para no cortar una palabra a la mitad.Corta el mensaje en ese punto.Envía el fragmento.Repite el proceso con el resto del texto.Añade encabezados visuales como *(...Parte 2)* para mantener el hilo.Manejo de Botones: Solo adjunta los botones interactivos (InlineKeyboard) al último fragmento del mensaje para no confundir al usuario.B. Renderizado de Elementos MultimediaASII V24 es multimodal. La interfaz maneja tres tipos de objetos que el cerebro puede devolver en su diccionario de respuesta:Texto (paquete["texto"]): Se envía usando Markdown (negritas, listas, código).Defensa: Si el Markdown está mal formado (ej: un asterisco sin cerrar), captura la excepción y envía el texto plano para evitar el crash.Imágenes (paquete["imagenes"]):El cerebro devuelve una lista de rutas locales (data/images_cache/.../img1.jpg).El bot itera sobre esta lista y usa context.bot.send_photo con la acción visual upload_photo (para que aparezca "subiendo foto..." en el chat).Archivos (paquete["archivos"]):Genera un ID Único Temporal (dl_a1b2c3d4) para cada archivo y lo guarda en DOWNLOAD_CACHE en memoria RAM.Crea un botón "📥 Bajar Archivo" asociado a ese ID.Esto evita enviar la ruta del archivo en el callback de Telegram (que tiene límite de 64 bytes).C. Gestión de Callbacks (Botones)La función manejar_callback es el controlador de eventos de la interfaz táctil.confirmar_experto: Trigger que cambia el estado de INDAGANDO a LEYENDO en el session_manager.cancelar_experto: Trigger que limpia la sesión.dl_{uuid}: Trigger de descarga. Busca la ruta real en el diccionario DOWNLOAD_CACHE y envía el documento físico.6.2. COMANDOS TÁCTICOSPara la administración y uso avanzado, ASII V24 dispone de un set de comandos directos que ejecutan lógica pura (Python) sin pasar por el LLM (ahorrando costos y tiempo).👤 Comandos de Usuario (Operativos)ComandoFunciónDescripción Técnica/startBienvenidaVerifica permisos de usuario (config.py) e inicia el saludo./limpiarResetLlama a gestor_sesiones.limpiar_sesion(chat_id). Borra el contexto de la conversación actual. Útil si el bot se queda "enganchado" con un tema anterior./manual [tema]Búsqueda RápidaBypass del chat. Ejecuta directamente detectar_archivo_francotirador. Si encuentra algo, muestra el índice inmediatamente (Estado INDAGANDO)./ayudaGuíaMuestra la lista de comandos disponibles.🛠️ Comandos de Administrador (Mantenimiento)ComandoFunciónDescripción Técnica/statusMonitorMuestra el estado actual del session_manager (¿En qué fase está? ¿Qué archivo lee?) y el Uptime del servidor./costosAuditoríaLee el archivo data/usage_log.csv, filtra las líneas con la fecha de hoy, suma la columna "CostoUSD" y reporta el gasto diario acumulado en tiempo real./inventarioExploraciónEscanea recursivamente la carpeta data/raw_docs y devuelve un conteo de archivos por categoría (subcarpetas)./recargarIngestaEjecuta el subproceso ingest_script.py para re-indexar la base vectorial (ChromaDB). Útil cuando se agregan PDFs nuevos a la carpeta./flushLimpieza ProfundaComando Peligroso. Borra el contenido de data/cache_docs. Obliga al bot a re-procesar (y re-extraer imágenes) de cualquier documento en la siguiente consulta.6.3. SEGURIDAD DE ACCESOEl bot implementa una capa de seguridad básica en la función verificar_acceso(update).Lista Blanca: Verifica si el user_id de Telegram está en la lista USUARIOS_PERMITIDOS definida en .env o config.py.Grupos: Si el bot se añade a un grupo, solo responderá si es mencionado explícitamente (@AsiiBot ayuda) o si se responde a un mensaje suyo.Bloqueo: Si un usuario no autorizado intenta hablarle, el bot responde "⛔ Acceso Denegado" y no procesa la solicitud (ahorrando costos de IA).


📘 CAPÍTULO 7: FINANZAS Y OPERACIONESASII V24 integra un módulo financiero nativo ("FinOps") que audita cada token consumido. Esto permite descentralizar el uso de la IA sin riesgo de sorpresas en la facturación de Google Cloud.7.1. SISTEMA DE AUDITORÍA EN TIEMPO REALLa arquitectura no espera a fin de mes para saber cuánto gastó. Cada interacción se calcula y registra al instante.A. Precios Base (Gemini 2.0 Flash)El sistema está calibrado con las tarifas oficiales de la API (Confirmed Pricing):Input (Lectura): $0.10 USD por 1 millón de tokens.Output (Escritura): $0.40 USD por 1 millón de tokens.B. El Registro Maestro (usage_log.csv)Ubicación: data/usage_log.csv.Cada vez que brain.py completa una generación, la función auditar_costos escribe una línea en este archivo con la siguiente estructura:TimestampFechaInput (Tokens)Output (Tokens)CostoUSD2025-12-12 10:00:012025-12-12154203500.001682Este archivo es la "Fuente de la Verdad" para todos los reportes y controles.7.2. DASHBOARD DE CONTROL (monitor_dashboard.py)ASII V24 incluye una aplicación de consola independiente para el administrador del sistema. No es necesario entrar a la plataforma de Google para ver el consumo.Funcionalidades del MonitorVisualización en Vivo: Lee el CSV cada segundo y muestra el acumulado del mes.Proyección de Presupuesto: Compara el gasto actual contra el LIMITE_PRESUPUESTO (ej: $50.00 USD).Control Manual: Permite detener el bot remotamente presionando la tecla 1.Mecanismo de "Kill Switch" (Corte de Emergencia)El sistema implementa un mecanismo de seguridad física basado en archivos para detener el consumo de API inmediatamente.Activación Automática: Si monitor_dashboard.py detecta que Gasto > Presupuesto, crea un archivo vacío llamado API_LOCKED en la carpeta data/.Activación Manual: Si el admin presiona 1 en el dashboard, se crea el mismo archivo.Efecto en el Cerebro:Antes de procesar cualquier mensaje, brain.py verifica: if os.path.exists(FILE_LOCK).Si el archivo existe, el bot responde al usuario: "⛔ SISTEMA PAUSADO".Costo: $0.00 (ni siquiera llama a la API).7.3. DESPLIEGUE Y MANTENIMIENTO OPERATIVOA. Estructura de Carpetas en ProducciónPara que el sistema funcione, la estructura de directorios debe mantenerse así:PlaintextASII_V24/
├── app/
│   ├── core/ (config.py)
│   ├── logic/ (brain, processor, session, etc.)
│   └── interfaces/ (telegram_bot)
├── data/
│   ├── raw_docs/       <-- Aquí se tiran los PDF nuevos
│   ├── chroma_db/      <-- Memoria Vectorial (Búsqueda)
│   ├── cache_docs/     <-- Memoria JSON (Lectura Profunda)
│   ├── images_cache/   <-- Catálogo de Fotos Extraídas
│   └── usage_log.csv   <-- Auditoría
├── .env                <-- API Keys y Tokens
├── run_bot.bat         <-- Inicia el Servidor (Bot)
├── monitor.bat         <-- Inicia el Panel de Control
└── requirements.txt
B. Procedimiento de Actualización de Manuales (Ingesta)Cuando el departamento de IT genera un nuevo procedimiento (ej: "Nuevo Servidor VPN.pdf"):Carga: Copiar el archivo PDF en la carpeta data/raw_docs (o cualquiera de sus subcarpetas).Indexación:Opción A (Admin): Ejecutar el comando /recargar en el chat de Telegram.Opción B (Consola): Ejecutar python data/ingest_script.py.Resultado: El archivo se agrega a la base vectorial (chroma_db).Lectura: La primera vez que alguien lo pida, el bot tardará unos segundos en generar el caché JSON y extraer las imágenes. Las siguientes veces será instantáneo.C. Mantenimiento de CachéSi un manual existente se actualiza (mismo nombre, contenido nuevo):Reemplazar el archivo en raw_docs.Ejecutar comando /flush en Telegram (o borrar data/cache_docs manualmente).Esto obliga al bot a re-procesar el archivo y actualizar su "visión" del contenido.