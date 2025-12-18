"""
Procesador Documental V32 (document_processor.py) - Pre-Análisis Ligero
-----------------------------------------------------------------------
Mejoras:
1. Función 'extraer_info_ligera': Obtiene TOC, Primeras Páginas y Metadata 
   sin procesar el documento completo.
2. Función 'construir_contexto_paginas': Carga quirúrgica de páginas.
3. Corrige errores de indentación y limpieza de imports.
"""
import os
import shutil
import re
import fitz  # PyMuPDF
try:
    import pymupdf4llm
except ImportError:
    print("Error: Falta pymupdf4llm. Instálalo con pip install pymupdf4llm")

from app.core.config import Configuracion

class ProcesadorDocumental:
    
    def __init__(self):
        self.img_dir = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "images_cache")
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)

    def extraer_info_ligera(self, ruta_pdf):
        """
        Extrae información ESTRUCTURAL rápida para decidir relevancia.
        NO procesa todo el documento. Es barato y rápido.
        Retorna: dict con índice, títulos clave, resumen y metadatos.
        """
        if not os.path.exists(ruta_pdf): return None

        try:
            doc = fitz.open(ruta_pdf)
            
            # 1. ÍNDICE (Table of Contents)
            toc = doc.get_toc()
            indice_texto = ""
            if toc:
                # Tomamos solo los primeros 20 items para no saturar
                for nivel, titulo, pagina in toc[:20]:
                    indent = "  " * (nivel - 1)
                    indice_texto += f"{indent}• {titulo} (pág {pagina})\n"
            else:
                indice_texto = "⚠️ Este documento no tiene índice estructurado."

            # 2. PRIMERAS 3 PÁGINAS (Introducción/Resumen)
            primeras_pags = ""
            num_pags_leer = min(3, len(doc))
            for i in range(num_pags_leer):
                primeras_pags += doc[i].get_text()[:800] + "\n...\n"

            # 3. ESCANEO RÁPIDO DE TÍTULOS (Heurística visual)
            titulos_detectados = []
            num_pags_scan = min(5, len(doc))
            for i in range(num_pags_scan):
                texto = doc[i].get_text()
                for linea in texto.split('\n'):
                    l = linea.strip()
                    # Detectar líneas mayúsculas que parecen títulos
                    if l.isupper() and 4 < len(l) < 70 and any(c.isalpha() for c in l):
                        if l not in titulos_detectados:
                            titulos_detectados.append(l)
            
            # 4. METADATA
            meta = doc.metadata or {}

            info = {
                "num_paginas": len(doc),
                "indice": indice_texto,
                "resumen_inicio": primeras_pags,
                "titulos_clave": titulos_detectados[:8], # Top 8 títulos
                "metadata": {
                    "titulo": meta.get("title", "Sin título"),
                    "autor": meta.get("author", "Desconocido")
                }
            }
            doc.close()
            return info

        except Exception as e:
            print(f"[Error info ligera] {e}")
            return {
                "num_paginas": 0,
                "indice": "Error de lectura",
                "resumen_inicio": "",
                "titulos_clave": [],
                "metadata": {}
            }

    def procesar_pdf(self, ruta_pdf):
        """
        Procesamiento PROFUNDO (Solo cuando ya decidimos leerlo).
        Genera Markdown, imágenes y mapas de navegación.
        """
        if not os.path.exists(ruta_pdf): return None
        
        nombre = os.path.basename(ruta_pdf).replace(".pdf", "")
        output_folder = os.path.join(self.img_dir, nombre)
        if not os.path.exists(output_folder): os.makedirs(output_folder)

        print(f">> [Procesador] Analizando {nombre}...")

        # 1. Markdown + Imágenes
        md_text = pymupdf4llm.to_markdown(
            ruta_pdf, 
            write_images=True, 
            image_path=output_folder, 
            image_format="jpg"
        )
        
        # 2. Catálogo y Mapas
        catalogo = self._crear_catalogo_imagenes(md_text, output_folder)
        texto_plano, mapa_paginas = self._extraer_texto_y_mapa(ruta_pdf)
        estructura = self._extraer_mapa_navegacion(md_text)
        metadata = self._generar_metadata(md_text, ruta_pdf)

        return {
            "contenido_markdown": md_text,
            "texto_plano": texto_plano,
            "mapa_paginas": mapa_paginas,
            "mapa_navegacion": estructura,
            "metadata": metadata,
            "ruta_imagenes": output_folder,
            "catalogo_imagenes": catalogo
        }

    def construir_contexto_paginas(self, mapa_paginas, paginas_interes, ventana=1):
        """
        Construye el contexto de texto SOLO de las páginas relevantes.
        """
        if not mapa_paginas or not paginas_interes: return ""
        
        paginas_finales = set()
        max_pag = max(mapa_paginas.keys()) if mapa_paginas else 0
        
        for p in paginas_interes:
            inicio = max(1, p - ventana)
            fin = min(max_pag, p + ventana)
            for i in range(inicio, fin + 1):
                paginas_finales.add(i)
        
        res = []
        last_p = -1
        for p in sorted(list(paginas_finales)):
            if p in mapa_paginas:
                if last_p != -1 and p > last_p + 1:
                    res.append("\n... [SECCIONES OMITIDAS] ...\n")
                res.append(f"--- PÁGINA {p} ---\n{mapa_paginas[p]}\n")
                last_p = p
                
        return "\n".join(res)

    def extraer_indice_ligero(self, ruta_pdf):
        """Wrapper legacy para compatibilidad."""
        info = self.extraer_info_ligera(ruta_pdf)
        return info["indice"] if info else "Error leyendo índice."

    # --- HELPERS INTERNOS ---

    def _crear_catalogo_imagenes(self, markdown, carpeta_imgs):
        catalogo = []
        if not os.path.exists(carpeta_imgs): return catalogo
        
        archivos = sorted([f for f in os.listdir(carpeta_imgs) if f.endswith('.jpg')])
        for img in archivos:
            if img in markdown:
                # Buscar contexto (150 chars antes)
                idx = markdown.find(img)
                raw_ctx = markdown[max(0, idx-150):idx]
                ctx = re.sub(r'[#*`\n]', ' ', raw_ctx).strip()
                if len(ctx) < 10: ctx = "Imagen técnica."
                
                # Página aproximada
                pag = markdown[:idx].count('\n---\n') + 1
                
                catalogo.append({
                    "archivo": img,
                    "ruta_completa": os.path.join(carpeta_imgs, img),
                    "contexto": ctx,
                    "pagina": pag
                })
        return catalogo

    def _extraer_texto_y_mapa(self, ruta_pdf):
        full_text = []
        page_map = {}
        try:
            doc = fitz.open(ruta_pdf)
            for i, page in enumerate(doc):
                text = page.get_text("text")
                full_text.append(text)
                page_map[i+1] = text
            doc.close()
            return "\n".join(full_text), page_map
        except Exception as e:
            print(f"Error texto plano: {e}")
            return "", {}

    def _generar_metadata(self, texto, ruta):
        return {
            "nombre_archivo": os.path.basename(ruta),
            "peso_kb": os.path.getsize(ruta) // 1024,
            "tiene_codigo": "```" in texto,
            "tiene_tablas": "|" in texto
        }

    def _extraer_mapa_navegacion(self, markdown):
        mapa = []
        titulos = re.findall(r'^(#{1,3})\s+(.+)$', markdown, re.MULTILINE)
        for nivel_hashtags, texto in titulos:
            nivel = len(nivel_hashtags)
            icono = "📄" if nivel > 1 else "📘"
            mapa.append(f"{'  '*(nivel-1)}{icono} {texto.strip()}")
        return "\n".join(mapa)

procesador = ProcesadorDocumental()